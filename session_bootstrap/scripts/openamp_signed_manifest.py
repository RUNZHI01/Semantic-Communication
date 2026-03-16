#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEX_DIGITS = frozenset("0123456789abcdef")
MANIFEST_SCHEMA = "openamp_artifact_manifest/v1"
SIGNED_BUNDLE_SCHEMA = "openamp_signed_manifest_bundle/v1"
BUNDLE_VERSION = 1
SIGNATURE_ALGORITHM = "ecdsa-p256-sha256"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def resolve_path(raw: str | Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(resolve_path(path).read_text(encoding="utf-8"))


def normalize_sha256(raw: Any, *, field_name: str) -> str:
    text = str(raw or "").strip().lower()
    if len(text) != 64 or any(char not in HEX_DIGITS for char in text):
        raise ValueError(f"{field_name} must be a 64-character SHA-256 hex string.")
    return text


def require_dict(raw: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{field_name} must be an object.")
    return raw


def require_text(raw: Any, *, field_name: str) -> str:
    value = str(raw or "").strip()
    if not value:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def require_u32(raw: Any, *, field_name: str, allow_zero: bool = False) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{field_name} must be an integer.") from err
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    if not allow_zero and value == 0:
        raise ValueError(f"{field_name} must be > 0.")
    if value > 0xFFFFFFFF:
        raise ValueError(f"{field_name} must fit in u32.")
    return value


def compute_file_sha256(path: str | Path) -> str:
    resolved = resolve_path(path)
    digest = hashlib.sha256()
    with resolved.open("rb") as infile:
        while True:
            chunk = infile.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def canonicalize_manifest(manifest: Mapping[str, Any]) -> bytes:
    validate_manifest(manifest)
    return json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def manifest_sha256_hex(manifest: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonicalize_manifest(manifest)).hexdigest()


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    schema = require_text(manifest.get("schema"), field_name="manifest.schema")
    if schema != MANIFEST_SCHEMA:
        raise ValueError(f"manifest.schema must equal {MANIFEST_SCHEMA!r}.")

    version = require_u32(manifest.get("manifest_version"), field_name="manifest.manifest_version")
    if version != 1:
        raise ValueError("manifest.manifest_version must equal 1.")

    artifact = require_dict(manifest.get("artifact"), field_name="manifest.artifact")
    normalize_sha256(artifact.get("sha256"), field_name="manifest.artifact.sha256")
    require_u32(artifact.get("size_bytes"), field_name="manifest.artifact.size_bytes", allow_zero=True)
    require_text(artifact.get("path"), field_name="manifest.artifact.path")
    require_text(artifact.get("format"), field_name="manifest.artifact.format")
    require_text(artifact.get("variant"), field_name="manifest.artifact.variant")

    job = require_dict(manifest.get("job"), field_name="manifest.job")
    require_u32(job.get("deadline_ms"), field_name="manifest.job.deadline_ms")
    require_u32(job.get("expected_outputs"), field_name="manifest.job.expected_outputs")
    require_text(job.get("job_flags"), field_name="manifest.job.job_flags")

    input_contract = require_dict(manifest.get("input_contract"), field_name="manifest.input_contract")
    shape = input_contract.get("shape")
    if not isinstance(shape, list) or len(shape) != 4:
        raise ValueError("manifest.input_contract.shape must be a 4-element list.")
    for index, raw_dim in enumerate(shape):
        require_u32(raw_dim, field_name=f"manifest.input_contract.shape[{index}]")
    require_text(input_contract.get("dtype"), field_name="manifest.input_contract.dtype")

    publisher = require_dict(manifest.get("publisher"), field_name="manifest.publisher")
    require_text(publisher.get("key_id"), field_name="manifest.publisher.key_id")
    require_text(publisher.get("channel"), field_name="manifest.publisher.channel")

    provenance = require_dict(manifest.get("provenance"), field_name="manifest.provenance")
    require_text(provenance.get("created_at"), field_name="manifest.provenance.created_at")
    require_text(provenance.get("builder"), field_name="manifest.provenance.builder")
    require_text(provenance.get("source_repo"), field_name="manifest.provenance.source_repo")


def build_manifest(
    *,
    artifact_path: str | Path,
    variant: str,
    key_id: str,
    publisher_channel: str,
    deadline_ms: int,
    expected_outputs: int,
    job_flags: str,
    artifact_format: str = "tvm-module-shared-object",
    input_shape: tuple[int, int, int, int] = (1, 32, 32, 32),
    input_dtype: str = "float32",
    source_git_commit: str = "",
    note: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    resolved_artifact = resolve_path(artifact_path)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "manifest_version": 1,
        "artifact": {
            "path": str(artifact_path),
            "sha256": compute_file_sha256(resolved_artifact),
            "size_bytes": resolved_artifact.stat().st_size,
            "format": artifact_format,
            "variant": require_text(variant, field_name="variant"),
        },
        "job": {
            "deadline_ms": require_u32(deadline_ms, field_name="deadline_ms"),
            "expected_outputs": require_u32(expected_outputs, field_name="expected_outputs"),
            "job_flags": require_text(job_flags, field_name="job_flags"),
        },
        "input_contract": {
            "shape": [
                require_u32(input_shape[0], field_name="input_shape[0]"),
                require_u32(input_shape[1], field_name="input_shape[1]"),
                require_u32(input_shape[2], field_name="input_shape[2]"),
                require_u32(input_shape[3], field_name="input_shape[3]"),
            ],
            "dtype": require_text(input_dtype, field_name="input_dtype"),
        },
        "publisher": {
            "key_id": require_text(key_id, field_name="key_id"),
            "channel": require_text(publisher_channel, field_name="publisher_channel"),
        },
        "provenance": {
            "created_at": created_at or now_iso(),
            "builder": "session_bootstrap/scripts/openamp_signed_manifest.py",
            "source_repo": "tvm_metaschedule_execution_project",
        },
    }
    if source_git_commit:
        manifest["provenance"]["source_git_commit"] = str(source_git_commit).strip()
    if note:
        manifest["provenance"]["note"] = str(note).strip()
    validate_manifest(manifest)
    return manifest


def _run_openssl(command: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        check=False,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        detail = stderr or stdout or f"openssl exited with {result.returncode}"
        raise ValueError(detail)
    return result


def _sign_bytes_with_openssl(payload: bytes, *, private_key: str | Path, openssl_bin: str) -> bytes:
    private_key_path = resolve_path(private_key)
    with tempfile.TemporaryDirectory(prefix="openamp_sign_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        payload_path = temp_dir / "manifest.bin"
        signature_path = temp_dir / "manifest.sig"
        payload_path.write_bytes(payload)
        _run_openssl(
            [
                openssl_bin,
                "dgst",
                "-sha256",
                "-sign",
                str(private_key_path),
                "-out",
                str(signature_path),
                str(payload_path),
            ]
        )
        return signature_path.read_bytes()


def _verify_bytes_with_openssl(
    payload: bytes,
    *,
    signature: bytes,
    public_key: str | Path,
    openssl_bin: str,
) -> None:
    public_key_path = resolve_path(public_key)
    with tempfile.TemporaryDirectory(prefix="openamp_verify_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        payload_path = temp_dir / "manifest.bin"
        signature_path = temp_dir / "manifest.sig"
        payload_path.write_bytes(payload)
        signature_path.write_bytes(signature)
        _run_openssl(
            [
                openssl_bin,
                "dgst",
                "-sha256",
                "-verify",
                str(public_key_path),
                "-signature",
                str(signature_path),
                str(payload_path),
            ]
        )


def sign_manifest(
    manifest: Mapping[str, Any],
    *,
    private_key: str | Path,
    key_id: str | None = None,
    openssl_bin: str = "openssl",
) -> dict[str, Any]:
    validate_manifest(manifest)
    canonical = canonicalize_manifest(manifest)
    manifest_sha256 = hashlib.sha256(canonical).hexdigest()
    selected_key_id = require_text(
        key_id if key_id is not None else manifest["publisher"]["key_id"],
        field_name="key_id",
    )
    if selected_key_id != str(manifest["publisher"]["key_id"]).strip():
        raise ValueError("key_id must match manifest.publisher.key_id.")
    signature_bytes = _sign_bytes_with_openssl(canonical, private_key=private_key, openssl_bin=openssl_bin)
    return {
        "schema": SIGNED_BUNDLE_SCHEMA,
        "bundle_version": BUNDLE_VERSION,
        "manifest_sha256": manifest_sha256,
        "manifest": dict(manifest),
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": selected_key_id,
            "encoding": "base64",
            "value": base64.b64encode(signature_bytes).decode("ascii"),
        },
    }


def validate_signed_manifest_bundle(bundle: Mapping[str, Any]) -> None:
    schema = require_text(bundle.get("schema"), field_name="bundle.schema")
    if schema != SIGNED_BUNDLE_SCHEMA:
        raise ValueError(f"bundle.schema must equal {SIGNED_BUNDLE_SCHEMA!r}.")

    version = require_u32(bundle.get("bundle_version"), field_name="bundle.bundle_version")
    if version != BUNDLE_VERSION:
        raise ValueError(f"bundle.bundle_version must equal {BUNDLE_VERSION}.")

    manifest = require_dict(bundle.get("manifest"), field_name="bundle.manifest")
    validate_manifest(manifest)

    declared_manifest_sha = normalize_sha256(bundle.get("manifest_sha256"), field_name="bundle.manifest_sha256")
    actual_manifest_sha = manifest_sha256_hex(manifest)
    if declared_manifest_sha != actual_manifest_sha:
        raise ValueError("bundle.manifest_sha256 does not match the canonical manifest digest.")

    signature = require_dict(bundle.get("signature"), field_name="bundle.signature")
    algorithm = require_text(signature.get("algorithm"), field_name="bundle.signature.algorithm").lower()
    if algorithm != SIGNATURE_ALGORITHM:
        raise ValueError(f"bundle.signature.algorithm must equal {SIGNATURE_ALGORITHM!r}.")
    require_text(signature.get("key_id"), field_name="bundle.signature.key_id")
    encoding = require_text(signature.get("encoding"), field_name="bundle.signature.encoding").lower()
    if encoding != "base64":
        raise ValueError("bundle.signature.encoding must equal 'base64'.")
    require_text(signature.get("value"), field_name="bundle.signature.value")


def load_signed_manifest_bundle(path: str | Path) -> dict[str, Any]:
    bundle = load_json(path)
    validate_signed_manifest_bundle(bundle)
    return bundle


def signed_manifest_summary(
    bundle: Mapping[str, Any],
    *,
    bundle_path: str | Path | None = None,
    verified: bool,
    artifact_match: bool | None,
    verification_public_key: str | None = None,
) -> dict[str, Any]:
    manifest = require_dict(bundle.get("manifest"), field_name="bundle.manifest")
    signature = require_dict(bundle.get("signature"), field_name="bundle.signature")
    artifact = require_dict(manifest.get("artifact"), field_name="manifest.artifact")
    job = require_dict(manifest.get("job"), field_name="manifest.job")
    return {
        "admission_mode": "signed_manifest_v1",
        "bundle_schema": str(bundle["schema"]),
        "bundle_version": int(bundle["bundle_version"]),
        "manifest_schema": str(manifest["schema"]),
        "manifest_version": int(manifest["manifest_version"]),
        "manifest_sha256": str(bundle["manifest_sha256"]),
        "artifact_sha256": str(artifact["sha256"]),
        "artifact_path": str(artifact["path"]),
        "artifact_size_bytes": int(artifact["size_bytes"]),
        "variant": str(artifact["variant"]),
        "deadline_ms": int(job["deadline_ms"]),
        "expected_outputs": int(job["expected_outputs"]),
        "job_flags": str(job["job_flags"]),
        "signature_algorithm": str(signature["algorithm"]),
        "key_id": str(signature["key_id"]),
        "verified_locally": bool(verified),
        "artifact_match": artifact_match,
        "bundle_path": str(bundle_path) if bundle_path is not None else None,
        "verification_public_key": verification_public_key,
        "protocol_status": "draft_only",
    }


def verify_signed_manifest_bundle(
    bundle: Mapping[str, Any],
    *,
    public_key: str | Path,
    artifact_path: str | Path | None = None,
    openssl_bin: str = "openssl",
) -> dict[str, Any]:
    validate_signed_manifest_bundle(bundle)
    manifest = require_dict(bundle.get("manifest"), field_name="bundle.manifest")
    signature = require_dict(bundle.get("signature"), field_name="bundle.signature")
    signature_bytes = base64.b64decode(str(signature["value"]).encode("ascii"), validate=True)
    canonical = canonicalize_manifest(manifest)
    _verify_bytes_with_openssl(
        canonical,
        signature=signature_bytes,
        public_key=public_key,
        openssl_bin=openssl_bin,
    )
    artifact_match: bool | None = None
    if artifact_path is not None:
        artifact_sha = compute_file_sha256(artifact_path)
        artifact_match = artifact_sha == str(manifest["artifact"]["sha256"])
        if not artifact_match:
            raise ValueError("artifact_path sha256 does not match manifest.artifact.sha256.")
    return signed_manifest_summary(
        bundle,
        bundle_path=None,
        verified=True,
        artifact_match=artifact_match,
        verification_public_key=str(resolve_path(public_key)),
    )


def build_signed_manifest_bundle(
    *,
    artifact_path: str | Path,
    variant: str,
    key_id: str,
    publisher_channel: str,
    deadline_ms: int,
    expected_outputs: int,
    job_flags: str,
    private_key: str | Path,
    artifact_format: str = "tvm-module-shared-object",
    input_shape: tuple[int, int, int, int] = (1, 32, 32, 32),
    input_dtype: str = "float32",
    source_git_commit: str = "",
    note: str = "",
    created_at: str | None = None,
    openssl_bin: str = "openssl",
) -> dict[str, Any]:
    manifest = build_manifest(
        artifact_path=artifact_path,
        variant=variant,
        key_id=key_id,
        publisher_channel=publisher_channel,
        deadline_ms=deadline_ms,
        expected_outputs=expected_outputs,
        job_flags=job_flags,
        artifact_format=artifact_format,
        input_shape=input_shape,
        input_dtype=input_dtype,
        source_git_commit=source_git_commit,
        note=note,
        created_at=created_at,
    )
    return sign_manifest(
        manifest,
        private_key=private_key,
        key_id=key_id,
        openssl_bin=openssl_bin,
    )


def parse_shape(raw: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in str(raw).split(",")]
    if len(parts) != 4:
        raise ValueError("--input-shape must have exactly four comma-separated dimensions.")
    return tuple(require_u32(part, field_name=f"input_shape[{index}]") for index, part in enumerate(parts))  # type: ignore[return-value]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create, sign, and verify signed OpenAMP artifact manifests. "
            "The host keeps the private key; firmware stores only public keys."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build an unsigned artifact manifest JSON file.")
    build_parser.add_argument("--artifact", required=True, help="Artifact path used for sha256 and size metadata.")
    build_parser.add_argument("--output", required=True, help="Manifest JSON output path.")
    build_parser.add_argument("--variant", required=True, help="Variant label such as current or baseline.")
    build_parser.add_argument("--key-id", required=True, help="Publisher key identifier stored in the manifest.")
    build_parser.add_argument("--publisher-channel", required=True, help="Publishing channel or environment label.")
    build_parser.add_argument("--deadline-ms", type=int, default=300000)
    build_parser.add_argument("--expected-outputs", type=int, default=300)
    build_parser.add_argument("--job-flags", default="reconstruction")
    build_parser.add_argument("--artifact-format", default="tvm-module-shared-object")
    build_parser.add_argument("--input-shape", default="1,32,32,32")
    build_parser.add_argument("--input-dtype", default="float32")
    build_parser.add_argument("--source-git-commit", default="")
    build_parser.add_argument("--note", default="")

    sign_parser = subparsers.add_parser("sign", help="Sign an existing manifest JSON file and emit a bundle.")
    sign_parser.add_argument("--manifest", required=True, help="Input unsigned manifest JSON.")
    sign_parser.add_argument("--private-key", required=True, help="PEM private key used for signing.")
    sign_parser.add_argument("--output", required=True, help="Signed bundle JSON output path.")
    sign_parser.add_argument("--key-id", default="", help="Optional explicit key_id. Defaults to manifest.publisher.key_id.")
    sign_parser.add_argument("--openssl-bin", default="openssl")

    verify_parser = subparsers.add_parser("verify", help="Verify a signed bundle with a public key.")
    verify_parser.add_argument("--signed-manifest", required=True, help="Signed bundle JSON path.")
    verify_parser.add_argument("--public-key", required=True, help="PEM public key used for verification.")
    verify_parser.add_argument("--artifact", default="", help="Optional artifact path to match against the manifest sha256.")
    verify_parser.add_argument("--openssl-bin", default="openssl")

    return parser.parse_args()


def command_build(args: argparse.Namespace) -> dict[str, Any]:
    manifest = build_manifest(
        artifact_path=args.artifact,
        variant=args.variant,
        key_id=args.key_id,
        publisher_channel=args.publisher_channel,
        deadline_ms=args.deadline_ms,
        expected_outputs=args.expected_outputs,
        job_flags=args.job_flags,
        artifact_format=args.artifact_format,
        input_shape=parse_shape(args.input_shape),
        input_dtype=args.input_dtype,
        source_git_commit=args.source_git_commit,
        note=args.note,
    )
    output_path = resolve_path(args.output)
    write_json(output_path, manifest)
    return {
        "command": "build",
        "output": str(output_path),
        "manifest_sha256": manifest_sha256_hex(manifest),
        "artifact_sha256": manifest["artifact"]["sha256"],
    }


def command_sign(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    bundle = sign_manifest(
        manifest,
        private_key=args.private_key,
        key_id=args.key_id or None,
        openssl_bin=args.openssl_bin,
    )
    output_path = resolve_path(args.output)
    write_json(output_path, bundle)
    return {
        "command": "sign",
        "output": str(output_path),
        "manifest_sha256": bundle["manifest_sha256"],
        "key_id": bundle["signature"]["key_id"],
        "signature_algorithm": bundle["signature"]["algorithm"],
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    bundle_path = resolve_path(args.signed_manifest)
    bundle = load_signed_manifest_bundle(bundle_path)
    summary = verify_signed_manifest_bundle(
        bundle,
        public_key=args.public_key,
        artifact_path=args.artifact or None,
        openssl_bin=args.openssl_bin,
    )
    summary["command"] = "verify"
    summary["bundle_path"] = str(bundle_path)
    return summary


def main() -> int:
    args = parse_args()
    if args.command == "build":
        result = command_build(args)
    elif args.command == "sign":
        result = command_sign(args)
    elif args.command == "verify":
        result = command_verify(args)
    else:
        raise SystemExit(f"unsupported command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
