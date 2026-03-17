from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

HOST_KEYS = ("REMOTE_HOST", "PHYTIUM_PI_HOST")
USER_KEYS = ("REMOTE_USER", "PHYTIUM_PI_USER")
PASSWORD_KEYS = ("REMOTE_PASS", "PHYTIUM_PI_PASSWORD")
PORT_KEYS = ("REMOTE_SSH_PORT", "PHYTIUM_PI_PORT")

INFERENCE_SHARED_REQUIRED_KEYS = (
    "REMOTE_TVM_PYTHON",
    "REMOTE_INPUT_DIR",
    "REMOTE_OUTPUT_BASE",
)
INFERENCE_VARIANT_REQUIRED_KEYS = {
    "baseline": ("REMOTE_JSCC_DIR", "REMOTE_SNR_BASELINE", "REMOTE_BATCH_BASELINE"),
    "current": ("REMOTE_SNR_CURRENT", "REMOTE_BATCH_CURRENT"),
}

DEFAULT_SSH_ENV_CANDIDATES = (
    "session_bootstrap/config/phytium_pi_login.env",
    "session_bootstrap/config/phytium_pi_login.example.env",
)
DEFAULT_INFERENCE_ENV_CANDIDATES = (
    "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
    "session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env",
)
VALIDATED_INFERENCE_REPORT_CANDIDATES = (
    "session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md",
)
VALIDATED_OPENAMP_RUN_MANIFEST_CANDIDATES = (
    "session_bootstrap/reports/openamp_input_contract_fit_20260315_014542/run_manifest.json",
    "session_bootstrap/reports/openamp_wrong_sha_fit_20260315_012403/run_manifest.json",
    "session_bootstrap/reports/openamp_wrong_sha_fit_20260315_010828/run_manifest.json",
)
TRUSTED_BASELINE_SHA_REPORT_CANDIDATES = (
    "session_bootstrap/reports/inference_compare_scheme_a_fair_fixed_20260311_154243.md",
    "session_bootstrap/reports/inference_local_scheme_a_payload_20260311_133729.md",
    "session_bootstrap/reports/inference_local_legacy_wrapper_20260311_015655.md",
)
TRUSTED_CURRENT_ARTIFACT_REPORT_CANDIDATES = (
    "session_bootstrap/reports/phytium_baseline_seeded_warm_start_current_incremental_chunk4_20260313_131545.json",
    "session_bootstrap/reports/phytium_baseline_seeded_warm_start_current_incremental_chunk3_20260313_131545.json",
)
PYTORCH_REFERENCE_MANIFEST_CANDIDATES = (
    "session_bootstrap/tmp/quality_metrics_inputs_20260312/reference/pytorch_reference_manifest.json",
)
VALIDATED_RUNTIME_FALLBACK_KEYS = (
    "REMOTE_TORCH_PYTHONPATH",
)


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_local_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / raw_path).resolve()
    else:
        path = path.resolve()
    return path


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env_file(raw_path: str | None) -> tuple[Path | None, dict[str, str]]:
    if not raw_path:
        return None, {}
    path = resolve_local_path(raw_path.strip())
    if not path.exists() or not path.is_file():
        raise ValueError(f"env 文件不存在: {repo_relative(path)}")
    return path, parse_env_text(path.read_text(encoding="utf-8"))


def load_env_path(path: Path) -> dict[str, str]:
    return parse_env_text(path.read_text(encoding="utf-8"))


def first_non_empty(mapping: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(mapping.get(key, "")).strip()
        if value:
            return value
    return ""


def normalize_port(raw: str) -> str:
    value = (raw or "22").strip() or "22"
    try:
        port = int(value)
    except ValueError as err:
        raise ValueError("SSH 端口必须是整数。") from err
    if port < 1 or port > 65535:
        raise ValueError("SSH 端口必须在 1 到 65535 之间。")
    return str(port)


def sanitize_env_values(values: dict[str, str]) -> dict[str, str]:
    sanitized = dict(values)
    for key in PASSWORD_KEYS:
        sanitized.pop(key, None)
    return sanitized


def resolve_existing_env(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = resolve_local_path(raw_path.strip())
    if path.exists() and path.is_file():
        return path
    return None


def first_existing_env(candidates: tuple[str, ...]) -> Path | None:
    for raw_path in candidates:
        path = resolve_existing_env(raw_path)
        if path is not None:
            return path
    return None


def load_markdown_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        values[key.strip()] = value.strip()
    return values


def discover_validated_inference_env(
    report_candidates: tuple[str, ...] = VALIDATED_INFERENCE_REPORT_CANDIDATES,
) -> Path | None:
    for raw_report_path in report_candidates:
        report_path = resolve_existing_env(raw_report_path)
        if report_path is None:
            continue
        env_file = load_markdown_key_values(report_path).get("env_file", "")
        env_path = resolve_existing_env(env_file)
        if env_path is not None:
            return env_path
    return None


def discover_validated_openamp_remote_project_root(
    run_manifest_candidates: tuple[str, ...] = VALIDATED_OPENAMP_RUN_MANIFEST_CANDIDATES,
) -> str:
    for raw_manifest_path in run_manifest_candidates:
        manifest_path = resolve_existing_env(raw_manifest_path)
        if manifest_path is None:
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        board_access = payload.get("board_access")
        if not isinstance(board_access, dict):
            continue
        remote_project_root = str(board_access.get("remote_project_root") or "").strip()
        if remote_project_root:
            return remote_project_root
    return ""


def valid_sha256_text(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", value):
        return value
    return ""


def resolve_baseline_artifact_path(values: dict[str, str]) -> str:
    explicit = str(values.get("REMOTE_BASELINE_ARTIFACT") or "").strip()
    if explicit:
        return explicit
    archive = str(values.get("INFERENCE_BASELINE_ARCHIVE") or values.get("REMOTE_TVM_PRIMARY_DIR") or "").strip()
    if archive:
        return f"{archive.rstrip('/')}/tvm_tune_logs/optimized_model.so"
    return ""


def resolve_current_artifact_path(values: dict[str, str]) -> str:
    explicit = str(values.get("REMOTE_CURRENT_ARTIFACT") or "").strip()
    if explicit:
        return explicit
    archive = str(values.get("INFERENCE_CURRENT_ARCHIVE") or values.get("REMOTE_TVM_JSCC_BASE_DIR") or "").strip()
    if archive:
        return f"{archive.rstrip('/')}/tvm_tune_logs/optimized_model.so"
    return ""


def discover_trusted_baseline_expected_sha(
    env_values: dict[str, str],
    report_candidates: tuple[str, ...] = TRUSTED_BASELINE_SHA_REPORT_CANDIDATES,
) -> str:
    baseline_artifact_path = resolve_baseline_artifact_path(env_values)
    if not baseline_artifact_path:
        return ""

    for raw_report_path in report_candidates:
        report_path = resolve_existing_env(raw_report_path)
        if report_path is None:
            continue
        values = load_markdown_key_values(report_path)
        baseline_expected_sha = valid_sha256_text(values.get("baseline_expected_sha256_configured", ""))
        if not baseline_expected_sha:
            continue
        report_artifact_path = str(values.get("baseline_artifact_path") or "").strip()
        if report_artifact_path and report_artifact_path != baseline_artifact_path:
            continue
        return baseline_expected_sha
    return ""


def discover_pytorch_reference_expected_sha(env_values: dict[str, str]) -> str:
    manifest_candidates: list[Path] = []
    explicit_manifest = str(env_values.get("PYTORCH_REFERENCE_MANIFEST") or "").strip()
    if explicit_manifest:
        manifest_candidates.append(resolve_local_path(explicit_manifest))
    manifest_candidates.extend(resolve_local_path(raw_path) for raw_path in PYTORCH_REFERENCE_MANIFEST_CANDIDATES)

    seen_paths: set[Path] = set()
    for manifest_path in manifest_candidates:
        if manifest_path in seen_paths:
            continue
        seen_paths.add(manifest_path)
        if not manifest_path.exists() or not manifest_path.is_file():
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        generator_sha = valid_sha256_text(payload.get("generator_ckpt_sha256", ""))
        if generator_sha:
            return generator_sha
    return ""


def discover_trusted_current_local_artifact_source(
    env_values: dict[str, str],
    report_candidates: tuple[str, ...] = TRUSTED_CURRENT_ARTIFACT_REPORT_CANDIDATES,
) -> str:
    binding = discover_trusted_current_artifact_binding(env_values, report_candidates)
    return str(binding.get("local_current_artifact_source") or "").strip()


def discover_trusted_current_artifact_binding(
    env_values: dict[str, str],
    report_candidates: tuple[str, ...] = TRUSTED_CURRENT_ARTIFACT_REPORT_CANDIDATES,
) -> dict[str, str]:
    expected_sha = valid_sha256_text(
        env_values.get("INFERENCE_CURRENT_EXPECTED_SHA256") or env_values.get("INFERENCE_EXPECTED_SHA256") or ""
    )
    if not expected_sha:
        return {}

    for raw_report_path in report_candidates:
        report_path = resolve_existing_env(raw_report_path)
        if report_path is None:
            continue
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        local_build = payload.get("local_build")
        remote_artifact = payload.get("remote_artifact")
        if not isinstance(local_build, dict) or not isinstance(remote_artifact, dict):
            continue
        local_source = str(local_build.get("optimized_model_so") or "").strip()
        local_sha = valid_sha256_text(local_build.get("optimized_model_sha256", ""))
        if local_sha != expected_sha:
            continue
        remote_sha = valid_sha256_text(remote_artifact.get("optimized_model_sha256", ""))
        if remote_sha and remote_sha != expected_sha:
            continue
        local_path = resolve_existing_env(local_source)
        if local_source and local_path is None:
            continue
        return {
            "expected_sha256": expected_sha,
            "local_current_artifact_source": str(local_path) if local_path is not None else "",
            "remote_current_artifact": str(remote_artifact.get("optimized_model_so") or "").strip(),
            "remote_current_archive_dir": str(remote_artifact.get("archive_dir") or "").strip(),
        }
    return {}


def apply_trusted_current_artifact_binding(
    env_values: dict[str, str],
    report_candidates: tuple[str, ...] = TRUSTED_CURRENT_ARTIFACT_REPORT_CANDIDATES,
) -> dict[str, str]:
    binding = discover_trusted_current_artifact_binding(env_values, report_candidates)
    if not binding:
        return dict(env_values)

    values = dict(env_values)
    remote_artifact = str(binding.get("remote_current_artifact") or "").strip()
    remote_archive_dir = str(binding.get("remote_current_archive_dir") or "").strip()
    local_source = str(binding.get("local_current_artifact_source") or "").strip()

    if remote_artifact:
        values["REMOTE_CURRENT_ARTIFACT"] = remote_artifact
    if remote_archive_dir:
        values["INFERENCE_CURRENT_ARCHIVE"] = remote_archive_dir
        values["REMOTE_TVM_JSCC_BASE_DIR"] = remote_archive_dir
        values["REMOTE_CURRENT_ARTIFACT_STAGE_DIR"] = remote_archive_dir
    if local_source:
        values["LOCAL_CURRENT_ARTIFACT_SOURCE"] = local_source
    return values


def merge_env_values(
    *,
    startup_env_values: dict[str, str],
    env_file_values: dict[str, str],
    host: str,
    user: str,
    password: str,
    port: str,
) -> dict[str, str]:
    values = sanitize_env_values(startup_env_values)
    values.update(sanitize_env_values(env_file_values))
    if host:
        values["REMOTE_HOST"] = host
        values["PHYTIUM_PI_HOST"] = host
    if user:
        values["REMOTE_USER"] = user
        values["PHYTIUM_PI_USER"] = user
    values["REMOTE_SSH_PORT"] = port
    values["PHYTIUM_PI_PORT"] = port
    if password:
        values["REMOTE_PASS"] = password
        values["PHYTIUM_PI_PASSWORD"] = password
    else:
        for key in PASSWORD_KEYS:
            values.pop(key, None)
    return apply_trusted_current_artifact_binding(values)


def preserve_validated_runtime_fallbacks(
    env_file_values: dict[str, str],
    startup_env_values: dict[str, str],
) -> dict[str, str]:
    values = dict(env_file_values)
    # Older inference env snapshots blank this field, which would drop the validated
    # torch sidecar and break `.pt` latent loading in the live demo path.
    for key in VALIDATED_RUNTIME_FALLBACK_KEYS:
        if str(values.get(key) or "").strip():
            continue
        if str(startup_env_values.get(key) or "").strip():
            values.pop(key, None)
    return values


def build_field_sources(
    *,
    host: str,
    user: str,
    password: str,
    port: str,
    env_file: Path | None,
    preloaded_values: dict[str, str],
) -> dict[str, str]:
    field_sources = {
        "host": "missing",
        "user": "missing",
        "password": "session" if password else "missing",
        "port": "missing",
        "env_file": "missing",
    }
    if host:
        field_sources["host"] = "preloaded" if host == preloaded_values.get("host", "") else "session"
    if user:
        field_sources["user"] = "preloaded" if user == preloaded_values.get("user", "") else "session"
    current_env_file = repo_relative(env_file) if env_file else ""
    if current_env_file:
        field_sources["env_file"] = "preloaded" if current_env_file == preloaded_values.get("env_file", "") else "session"
    effective_port = port if (host or user or current_env_file or preloaded_values.get("port")) else ""
    if effective_port:
        field_sources["port"] = "preloaded" if effective_port == preloaded_values.get("port", "") else "session"
    return field_sources


def build_source_summary(
    *,
    field_sources: dict[str, str],
    preloaded_ssh_env_file: Path | None,
    preloaded_inference_env_file: Path | None,
) -> str:
    parts: list[str] = []
    if preloaded_ssh_env_file or preloaded_inference_env_file:
        parts.append("启动预载")
    if any(source == "session" for source in field_sources.values()):
        parts.append("网页表单")
    if not parts:
        parts.append("未配置")
    return " + ".join(parts)


@dataclass(frozen=True)
class BoardAccessConfig:
    host: str
    user: str
    password: str
    port: str
    env_file: Path | None
    env_values: dict[str, str]
    source_summary: str
    field_sources: dict[str, str] = field(default_factory=dict)
    startup_env_values: dict[str, str] = field(default_factory=dict)
    env_file_values: dict[str, str] = field(default_factory=dict)
    preloaded_values: dict[str, str] = field(default_factory=dict)
    preloaded_ssh_env_file: Path | None = None
    preloaded_inference_env_file: Path | None = None

    @property
    def configured(self) -> bool:
        return bool(self.host or self.user or self.password or self.env_file)

    @property
    def connection_ready(self) -> bool:
        return bool(self.host and self.user and self.password)

    @property
    def probe_ready(self) -> bool:
        return self.connection_ready

    @property
    def has_preloaded_defaults(self) -> bool:
        return bool(
            self.preloaded_ssh_env_file
            or self.preloaded_inference_env_file
            or any(str(value).strip() for value in self.preloaded_values.values())
        )

    def missing_connection_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.host:
            missing.append("host")
        if not self.user:
            missing.append("user")
        if not self.password:
            missing.append("password")
        return missing

    def missing_inference_fields(self, variant: str) -> list[str]:
        missing = self.missing_connection_fields()
        for key in INFERENCE_SHARED_REQUIRED_KEYS + INFERENCE_VARIANT_REQUIRED_KEYS.get(variant, ()):
            if not str(self.env_values.get(key, "")).strip():
                missing.append(key)
        return missing

    def build_env(self) -> dict[str, str]:
        startup_env_values = self.startup_env_values
        env_file_values = self.env_file_values
        if not startup_env_values and not env_file_values:
            startup_env_values = sanitize_env_values(self.env_values)
        return merge_env_values(
            startup_env_values=startup_env_values,
            env_file_values=env_file_values,
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
        )

    def build_subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self.build_env())
        return env

    def with_env_overrides(self, overrides: dict[str, str]) -> "BoardAccessConfig":
        clean_overrides = {str(key): str(value).strip() for key, value in overrides.items() if str(value).strip()}
        if not clean_overrides:
            return self

        env_values = dict(self.env_values)
        env_values.update(clean_overrides)

        startup_env_values = dict(self.startup_env_values)
        env_file_values = dict(self.env_file_values)
        if startup_env_values or env_file_values:
            env_file_values.update(clean_overrides)

        return replace(
            self,
            env_values=env_values,
            startup_env_values=startup_env_values,
            env_file_values=env_file_values,
        )

    def to_public_dict(self) -> dict[str, Any]:
        missing_current = self.missing_inference_fields("current")
        missing_baseline = self.missing_inference_fields("baseline")
        return {
            "configured": self.configured,
            "connection_ready": self.connection_ready,
            "probe_ready": self.probe_ready,
            "inference_ready": not missing_current,
            "inference_ready_variants": {
                "current": not missing_current,
                "baseline": not missing_baseline,
            },
            "host": self.host,
            "user": self.user,
            "port": int(self.port),
            "env_file": repo_relative(self.env_file) if self.env_file else "",
            "has_password": bool(self.password),
            "missing_connection_fields": self.missing_connection_fields(),
            "missing_inference_fields": missing_current,
            "missing_inference_fields_by_variant": {
                "current": missing_current,
                "baseline": missing_baseline,
            },
            "source_summary": self.source_summary,
            "field_sources": self.field_sources,
            "preloaded_defaults": {
                "active": self.has_preloaded_defaults,
                "host": self.preloaded_values.get("host", ""),
                "user": self.preloaded_values.get("user", ""),
                "port": self.preloaded_values.get("port", ""),
                "env_file": self.preloaded_values.get("env_file", ""),
                "ssh_env_file": repo_relative(self.preloaded_ssh_env_file) if self.preloaded_ssh_env_file else "",
                "inference_env_file": (
                    repo_relative(self.preloaded_inference_env_file) if self.preloaded_inference_env_file else ""
                ),
            },
        }


def build_board_access_config(
    payload: dict[str, Any],
    *,
    fallback: BoardAccessConfig | None = None,
) -> BoardAccessConfig:
    raw_payload = {str(key): str(value or "").strip() for key, value in payload.items()}
    fallback_startup_env = sanitize_env_values(fallback.startup_env_values) if fallback else {}
    fallback_env_file_values = sanitize_env_values(fallback.env_file_values) if fallback else {}
    raw_env_file = raw_payload.get("env_file")
    if raw_env_file:
        env_file, env_file_values = load_env_file(raw_env_file)
        env_file_values = sanitize_env_values(env_file_values)
    else:
        env_file = fallback.env_file if fallback else None
        env_file_values = fallback_env_file_values
    env_file_values = preserve_validated_runtime_fallbacks(env_file_values, fallback_startup_env)

    host = (
        raw_payload.get("host")
        or first_non_empty(env_file_values, HOST_KEYS)
        or (fallback.host if fallback else "")
        or first_non_empty(fallback_startup_env, HOST_KEYS)
    )
    user = (
        raw_payload.get("user")
        or first_non_empty(env_file_values, USER_KEYS)
        or (fallback.user if fallback else "")
        or first_non_empty(fallback_startup_env, USER_KEYS)
    )
    password = raw_payload.get("password") or (fallback.password if fallback else "")
    port = normalize_port(
        raw_payload.get("port")
        or first_non_empty(env_file_values, PORT_KEYS)
        or (fallback.port if fallback else "")
        or first_non_empty(fallback_startup_env, PORT_KEYS)
        or "22"
    )

    preloaded_values = dict(fallback.preloaded_values) if fallback else {}
    field_sources = build_field_sources(
        host=host,
        user=user,
        password=password,
        port=port,
        env_file=env_file,
        preloaded_values=preloaded_values,
    )
    merged_env = merge_env_values(
        startup_env_values=fallback_startup_env,
        env_file_values=env_file_values,
        host=host,
        user=user,
        password=password,
        port=port,
    )

    return BoardAccessConfig(
        host=host,
        user=user,
        password=password,
        port=port,
        env_file=env_file,
        env_values=merged_env,
        source_summary=build_source_summary(
            field_sources=field_sources,
            preloaded_ssh_env_file=fallback.preloaded_ssh_env_file if fallback else None,
            preloaded_inference_env_file=fallback.preloaded_inference_env_file if fallback else None,
        ),
        field_sources=field_sources,
        startup_env_values=fallback_startup_env,
        env_file_values=env_file_values,
        preloaded_values=preloaded_values,
        preloaded_ssh_env_file=fallback.preloaded_ssh_env_file if fallback else None,
        preloaded_inference_env_file=fallback.preloaded_inference_env_file if fallback else None,
    )


def build_demo_default_board_access(
    probe_env: str | None,
    *,
    startup_env_overrides: dict[str, str] | None = None,
) -> BoardAccessConfig:
    ssh_env_path = resolve_existing_env(probe_env) or first_existing_env(DEFAULT_SSH_ENV_CANDIDATES)
    inference_env_path = discover_validated_inference_env() or first_existing_env(DEFAULT_INFERENCE_ENV_CANDIDATES)

    ssh_env_values = sanitize_env_values(load_env_path(ssh_env_path)) if ssh_env_path else {}
    inference_env_values = sanitize_env_values(load_env_path(inference_env_path)) if inference_env_path else {}
    startup_env_values = dict(ssh_env_values)
    if startup_env_overrides:
        startup_env_values.update({str(key): str(value) for key, value in startup_env_overrides.items() if str(value)})
    for key in VALIDATED_RUNTIME_FALLBACK_KEYS:
        value = str(inference_env_values.get(key) or "").strip()
        if value and not str(startup_env_values.get(key) or "").strip():
            startup_env_values[key] = value
    remote_project_root = discover_validated_openamp_remote_project_root()
    if (
        remote_project_root
        and not str(inference_env_values.get("REMOTE_PROJECT_ROOT") or "").strip()
        and not str(inference_env_values.get("OPENAMP_REMOTE_PROJECT_ROOT") or "").strip()
    ):
        startup_env_values["REMOTE_PROJECT_ROOT"] = remote_project_root
    if not str(inference_env_values.get("INFERENCE_BASELINE_EXPECTED_SHA256") or "").strip():
        baseline_expected_sha = discover_pytorch_reference_expected_sha(
            inference_env_values
        ) or discover_trusted_baseline_expected_sha(inference_env_values)
        if baseline_expected_sha:
            startup_env_values["INFERENCE_BASELINE_EXPECTED_SHA256"] = baseline_expected_sha
    if not str(inference_env_values.get("LOCAL_CURRENT_ARTIFACT_SOURCE") or "").strip():
        trusted_current_local_source = discover_trusted_current_local_artifact_source(inference_env_values)
        if trusted_current_local_source:
            startup_env_values["LOCAL_CURRENT_ARTIFACT_SOURCE"] = trusted_current_local_source

    host = first_non_empty(ssh_env_values, HOST_KEYS) or first_non_empty(inference_env_values, HOST_KEYS)
    user = first_non_empty(ssh_env_values, USER_KEYS) or first_non_empty(inference_env_values, USER_KEYS)
    port = normalize_port(
        first_non_empty(ssh_env_values, PORT_KEYS)
        or first_non_empty(inference_env_values, PORT_KEYS)
        or "22"
    )

    merged_env = merge_env_values(
        startup_env_values=startup_env_values,
        env_file_values=inference_env_values,
        host=host,
        user=user,
        password="",
        port=port,
    )
    preloaded_values = {
        "host": host,
        "user": user,
        "port": port if (host or user or inference_env_path) else "",
        "env_file": repo_relative(inference_env_path) if inference_env_path else "",
    }
    field_sources = build_field_sources(
        host=host,
        user=user,
        password="",
        port=port,
        env_file=inference_env_path,
        preloaded_values=preloaded_values,
    )

    return BoardAccessConfig(
        host=host,
        user=user,
        password="",
        port=port,
        env_file=inference_env_path,
        env_values=merged_env,
        source_summary=build_source_summary(
            field_sources=field_sources,
            preloaded_ssh_env_file=ssh_env_path,
            preloaded_inference_env_file=inference_env_path,
        ),
        field_sources=field_sources,
        startup_env_values=startup_env_values,
        env_file_values=inference_env_values,
        preloaded_values=preloaded_values,
        preloaded_ssh_env_file=ssh_env_path,
        preloaded_inference_env_file=inference_env_path,
    )
