#!/usr/bin/env python3
"""Prepare the first handwritten scaffold for fused_conv2d_transpose1_add9.

This helper is intentionally narrow. It creates a small bookkeeping pack for the
current wave-1 priority-1 handwritten candidate without launching tuning,
uploading artifacts, or touching trusted current.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_NAME = "fused_conv2d_transpose1_add9"
DEFAULT_CANDIDATE_JSON = (
    PROJECT_ROOT / "session_bootstrap" / "reports" / "handwritten_hotspot_candidates_20260331.json"
)
DEFAULT_REBUILD_BASE_ENV = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "config"
    / "rpc_tune_rebuild_current_safe.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env"
)
DEFAULT_VALIDATE_BASE_ENV = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "config"
    / "inference_tvm310_safe.2026-03-10.phytium_pi.env"
)
DEFAULT_PROFILE_BASE_ENV = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "reports"
    / "profiling_runtime_joint_top6_staging_artifact_reprobe_20260331_0010"
    / "trusted_env_snapshot.env"
)
DEFAULT_BEST_STAGING_DB = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "phytium_runtime_joint_top6_targeted_staging_search_20260330_2315"
    / "tuning_logs"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "handwritten_fused_conv2d_transpose1_add9_scaffold"
)
DEFAULT_REBUILD_OUTPUT_DIR = (
    "./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_candidate"
)
DEFAULT_REMOTE_ARCHIVE_DIR = (
    "/home/user/Downloads/jscc-test/jscc_staging_handwritten_fused_conv2d_transpose1_add9"
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a staging-only bookkeeping pack for the handwritten "
            f"candidate {OPERATOR_NAME}."
        )
    )
    parser.add_argument(
        "--candidate-json",
        type=Path,
        default=DEFAULT_CANDIDATE_JSON,
        help="Candidate pack JSON created by prepare_handwritten_hotspot_candidates.py.",
    )
    parser.add_argument(
        "--rebuild-base-env",
        type=Path,
        default=DEFAULT_REBUILD_BASE_ENV,
        help="Base rebuild-only env used by run_phytium_current_safe_one_shot.sh.",
    )
    parser.add_argument(
        "--validate-inference-base-env",
        type=Path,
        default=DEFAULT_VALIDATE_BASE_ENV,
        help="Base safe-runtime inference env used for staging validation.",
    )
    parser.add_argument(
        "--profile-base-env",
        type=Path,
        default=DEFAULT_PROFILE_BASE_ENV,
        help="Base trusted env snapshot used by run_task_5_1_operator_profile.py.",
    )
    parser.add_argument(
        "--best-staging-db",
        type=Path,
        default=DEFAULT_BEST_STAGING_DB,
        help="Warm-start DB root for the current best staging candidate.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated scaffold files.",
    )
    parser.add_argument(
        "--remote-archive-dir",
        default=DEFAULT_REMOTE_ARCHIVE_DIR,
        help="Staging-only remote archive for this handwritten candidate.",
    )
    parser.add_argument(
        "--manual-artifact-sha256",
        default="",
        help="Optional handwritten artifact SHA256 to prefill into validation/profile envs.",
    )
    parser.add_argument(
        "--rebuild-output-dir",
        default=DEFAULT_REBUILD_OUTPUT_DIR,
        help="Repo-native local output dir for the handwritten rebuild artifact.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwriting an existing scaffold directory.",
    )
    args = parser.parse_args(argv)
    digest = args.manual_artifact_sha256.strip()
    if digest and not SHA256_RE.fullmatch(digest):
        raise SystemExit(
            "ERROR: --manual-artifact-sha256 must be a 64-character hex digest when provided."
        )
    args.manual_artifact_sha256 = digest.lower()
    return args


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def as_abs(path: Path) -> Path:
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def repo_native(path: Path | str) -> str:
    value = Path(path)
    resolved = value if value.is_absolute() else (PROJECT_ROOT / value).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return str(resolved)
    return f"./{relative.as_posix()}"


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def load_candidate(candidate_json: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(candidate_json.read_text(encoding="utf-8"))
    wave1 = payload.get("wave1_candidates") or []
    candidate = next((row for row in wave1 if row.get("name") == OPERATOR_NAME), None)
    if candidate is None:
        raise SystemExit(
            f"ERROR: {OPERATOR_NAME} is not present in wave1_candidates: {candidate_json}"
        )
    if candidate.get("priority") != 1:
        raise SystemExit(
            f"ERROR: expected {OPERATOR_NAME} to remain wave-1 priority 1, "
            f"got priority={candidate.get('priority')!r}"
        )
    return payload, candidate


def ensure_clean_outputs(paths: list[Path], allow_overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not allow_overwrite:
        joined = "\n  ".join(str(path) for path in existing)
        raise SystemExit(
            "ERROR: scaffold output already exists. Re-run with --allow-overwrite or "
            f"choose a new --output-dir.\n  {joined}"
        )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_sha_comment(sha256_value: str) -> str:
    if sha256_value:
        return "# Prefilled from --manual-artifact-sha256."
    return (
        "# Fill INFERENCE_CURRENT_EXPECTED_SHA256 after the handwritten artifact is built "
        "and before remote validation/profile."
    )


def build_rebuild_env(
    *,
    args: argparse.Namespace,
    candidate_payload: dict[str, Any],
    candidate: dict[str, Any],
) -> str:
    best_staging = candidate_payload.get("current_best_staging") or {}
    lines = [
        "# Auto-generated handwritten rebuild overlay for fused_conv2d_transpose1_add9.",
        "# shellcheck source=/dev/null",
        f"source {shell_quote(str(args.rebuild_base_env.resolve()))}",
        "",
        "# Keep this candidate tied to the current best staging lineage.",
        f"TUNE_EXISTING_DB={shell_quote(repo_native(args.best_staging_db))}",
        f"TUNE_OUTPUT_DIR={shell_quote(args.rebuild_output_dir)}",
        "TUNE_TOTAL_TRIALS=0",
        (
            "TUNE_MODE_LABEL="
            "rebuild_current_safe_handwritten_fused_conv2d_transpose1_add9_from_best_staging"
        ),
        "EXECUTION_ID=handwritten_fused_conv2d_transpose1_add9_from_best_staging",
        "FULL_EXECUTION_ID=handwritten_fused_conv2d_transpose1_add9_from_best_staging_full",
        "",
        "# Pin the remote archive to a handwritten staging lane.",
        f"REMOTE_TVM_JSCC_BASE_DIR={shell_quote(args.remote_archive_dir)}",
        "",
        "# Handwritten bookkeeping only; these variables are not consumed by the stock wrappers.",
        f"HANDWRITTEN_TARGET_OP={OPERATOR_NAME}",
        f"HANDWRITTEN_PRIORITY=wave1_p{candidate.get('priority')}",
        f"HANDWRITTEN_REFERENCE_ARTIFACT_SHA256={best_staging.get('artifact_sha256', '')}",
        (
            "HANDWRITTEN_REFERENCE_PROFILE_JSON="
            f"{shell_quote(str(candidate_payload.get('current_profile_json', '')))}"
        ),
        f"HANDWRITTEN_ARGUMENT_SHAPES={shell_quote(str(candidate.get('current_argument_shapes', '')))}",
        "",
        "# TODO: add the env switch or path that enables the handwritten kernel before rebuild.",
        "# Example placeholders:",
        f"# TVM_HANDWRITTEN_OP={OPERATOR_NAME}",
        "# TVM_HANDWRITTEN_IMPL_PATH=./session_bootstrap/tmp/fused_conv2d_transpose1_add9_manual_impl.py",
        "",
    ]
    return "\n".join(lines)


def build_validate_env(*, args: argparse.Namespace) -> str:
    sha256_value = args.manual_artifact_sha256
    lines = [
        "# Auto-generated validation inference env for fused_conv2d_transpose1_add9.",
        "# shellcheck source=/dev/null",
        f"source {shell_quote(str(args.validate_inference_base_env.resolve()))}",
        "",
        "# Keep validation on the dedicated handwritten staging archive.",
        f"INFERENCE_CURRENT_ARCHIVE={shell_quote(args.remote_archive_dir)}",
        f"REMOTE_TVM_JSCC_BASE_DIR={shell_quote(args.remote_archive_dir)}",
        (
            "REMOTE_CURRENT_ARTIFACT="
            f"{shell_quote(args.remote_archive_dir + '/tvm_tune_logs/optimized_model.so')}"
        ),
        render_sha_comment(sha256_value),
        f"INFERENCE_CURRENT_EXPECTED_SHA256={sha256_value}",
        "INFERENCE_EXECUTION_ID=handwritten_fused_conv2d_transpose1_add9_validate",
        "",
    ]
    return "\n".join(lines)


def build_profile_env(*, args: argparse.Namespace) -> str:
    sha256_value = args.manual_artifact_sha256
    lines = [
        "# Auto-generated runtime-profile env for fused_conv2d_transpose1_add9.",
        "# shellcheck source=/dev/null",
        f"source {shell_quote(str(args.profile_base_env.resolve()))}",
        "",
        "# Point the existing operator-profile wrapper at the handwritten staging archive.",
        f"INFERENCE_CURRENT_ARCHIVE={shell_quote(args.remote_archive_dir)}",
        f"REMOTE_TVM_JSCC_BASE_DIR={shell_quote(args.remote_archive_dir)}",
        (
            "REMOTE_CURRENT_ARTIFACT="
            f"{shell_quote(args.remote_archive_dir + '/tvm_tune_logs/optimized_model.so')}"
        ),
        render_sha_comment(sha256_value),
        f"INFERENCE_CURRENT_EXPECTED_SHA256={sha256_value}",
        "INFERENCE_EXECUTION_ID=profiling_handwritten_fused_conv2d_transpose1_add9",
        "",
    ]
    return "\n".join(lines)


def build_commands(
    *,
    rebuild_env: Path,
    validate_env: Path,
    profile_env: Path,
    remote_archive_dir: str,
    rebuild_output_dir: str,
) -> dict[str, str]:
    validate_command = "\n".join(
        [
            "bash ./session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh \\",
            f"  --rebuild-env {shell_quote(str(rebuild_env))} \\",
            f"  --inference-env {shell_quote(str(validate_env))} \\",
            f"  --remote-archive-dir {shell_quote(remote_archive_dir)} \\",
            "  --report-id phytium_handwritten_fused_conv2d_transpose1_add9_$(date +%Y%m%d_%H%M%S)",
        ]
    )
    profile_command = "\n".join(
        [
            "python3 ./session_bootstrap/scripts/run_task_5_1_operator_profile.py \\",
            "  --run-id profiling_handwritten_fused_conv2d_transpose1_add9_$(date +%Y%m%d_%H%M%S) \\",
            "  --hotspot-mode reuse \\",
            "  --runtime-mode attempt \\",
            f"  --trusted-env {shell_quote(str(profile_env))} \\",
            "  --trusted-variant current \\",
            "  --max-inputs 1 \\",
            "  --profile-samples 1",
        ]
    )
    sha_target = f"{repo_native(Path(rebuild_output_dir))}/optimized_model.so"
    sha_command = f"sha256sum {shell_quote(sha_target)}"
    return {
        "compute_sha256": sha_command,
        "validate": validate_command,
        "profile": profile_command,
    }


def build_validation_report_template(
    *,
    candidate_payload: dict[str, Any],
    candidate: dict[str, Any],
    args: argparse.Namespace,
    commands: dict[str, str],
) -> str:
    best_staging = candidate_payload.get("current_best_staging") or {}
    digest = args.manual_artifact_sha256 or "<fill_after_build>"
    return "\n".join(
        [
            f"# Validation record: {OPERATOR_NAME}",
            "",
            "## Candidate identity",
            "",
            f"- operator: `{OPERATOR_NAME}`",
            f"- candidate_sha256: `{digest}`",
            f"- fixed_best_staging_sha256: `{best_staging.get('artifact_sha256', '')}`",
            f"- remote_staging_archive: `{args.remote_archive_dir}`",
            f"- local_rebuild_output: `{repo_native(Path(args.rebuild_output_dir))}`",
            f"- operator_shapes: `{candidate.get('current_argument_shapes', '')}`",
            "",
            "## Payload validation",
            "",
            "- validate_report_id: `<fill>`",
            "- validate_summary_md: `<fill>`",
            "- artifact_sha256_match: `<true|false>`",
            "- payload_result: `<fill>`",
            "- payload_vs_best_staging: `<better|flat|worse>`",
            "",
            "## Runtime reprobe",
            "",
            "- reprobe_run_id: `<fill>`",
            "- reprobe_summary_md: `<fill>`",
            f"- {OPERATOR_NAME}_result: `<fill>`",
            "- hotspot_snapback: `<none|present>`",
            "",
            "## Decision",
            "",
            "- decision: `<keep_staging_only|drop>`",
            "- rationale: `<fill>`",
            "",
            "## Commands used",
            "",
            "```bash",
            commands["compute_sha256"],
            "```",
            "",
            "```bash",
            commands["validate"],
            "```",
            "",
            "```bash",
            commands["profile"],
            "```",
            "",
        ]
    )


def build_readme(
    *,
    candidate_payload: dict[str, Any],
    candidate: dict[str, Any],
    args: argparse.Namespace,
    generated_files: dict[str, str],
    commands: dict[str, str],
) -> str:
    best_staging = candidate_payload.get("current_best_staging") or {}
    sha_note = (
        "The SHA256 fields are prefilled."
        if args.manual_artifact_sha256
        else "Fill the SHA256 fields in the generated envs before remote validation/profile."
    )
    return "\n".join(
        [
            f"# {OPERATOR_NAME} handwritten scaffold",
            "",
            f"- operator: `{OPERATOR_NAME}`",
            f"- family: `{candidate.get('family', '')}`",
            f"- wave-1 priority: `{candidate.get('priority')}`",
            f"- current runtime share: `{candidate.get('current_mean_percent'):.2f}%`",
            f"- current mean duration: `{candidate.get('current_mean_duration_us'):.2f} us`",
            f"- current shapes: `{candidate.get('current_argument_shapes', '')}`",
            (
                "- fixed comparison staging artifact: "
                f"`{best_staging.get('artifact_sha256', '')}`"
            ),
            f"- remote handwritten staging archive: `{args.remote_archive_dir}`",
            "",
            "## Why this path",
            "",
            "- `run_phytium_current_safe_one_shot.sh` is the smallest repo-native validator here because it supports rebuild-only (`TUNE_TOTAL_TRIALS=0`) plus a staging archive override.",
            "- `run_phytium_current_safe_staging_validate.sh` is not the first fit for handwritten work because its parent wrapper enforces a nonzero tuning budget.",
            "- `run_task_5_1_operator_profile.py` already knows how to reuse hotspot evidence; it only needs a patched trusted env that points at the handwritten staging archive.",
            "",
            "## Generated files",
            "",
            f"- `manual_rebuild.env`: `{generated_files['manual_rebuild.env']}`",
            f"- `manual_validate_inference.env`: `{generated_files['manual_validate_inference.env']}`",
            f"- `manual_profile.env`: `{generated_files['manual_profile.env']}`",
            f"- `validation_report_template.md`: `{generated_files['validation_report_template.md']}`",
            f"- `bookkeeping.json`: `{generated_files['bookkeeping.json']}`",
            "",
            "## Before running anything remote",
            "",
            f"1. Patch `manual_rebuild.env` so the handwritten implementation for `{OPERATOR_NAME}` is actually enabled.",
            (
                "2. Build or rebuild the candidate locally so "
                f"`{repo_native(Path(args.rebuild_output_dir))}/optimized_model.so` exists."
            ),
            f"3. {sha_note}",
            "4. Copy or edit `validation_report_template.md` so the keep/drop decision is captured together with the payload and reprobe outputs.",
            "",
            "## SHA capture",
            "",
            "```bash",
            commands["compute_sha256"],
            "```",
            "",
            "## Staging validation",
            "",
            "```bash",
            commands["validate"],
            "```",
            "",
            "## Runtime reprobe",
            "",
            "```bash",
            commands["profile"],
            "```",
            "",
            "## Scope guard",
            "",
            "- Trusted current remains untouched.",
            "- The remote archive stays operator-specific and staging-only.",
            "- This pack records one candidate only; it does not add a generic handwritten subsystem.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.candidate_json = require_file(as_abs(args.candidate_json), "candidate JSON")
    args.rebuild_base_env = require_file(as_abs(args.rebuild_base_env), "rebuild base env")
    args.validate_inference_base_env = require_file(
        as_abs(args.validate_inference_base_env), "validation inference base env"
    )
    args.profile_base_env = require_file(as_abs(args.profile_base_env), "profile base env")
    args.best_staging_db = require_dir(as_abs(args.best_staging_db), "best staging DB")
    args.output_dir = as_abs(args.output_dir)

    payload, candidate = load_candidate(args.candidate_json)

    rebuild_env = args.output_dir / "manual_rebuild.env"
    validate_env = args.output_dir / "manual_validate_inference.env"
    profile_env = args.output_dir / "manual_profile.env"
    validation_template_md = args.output_dir / "validation_report_template.md"
    bookkeeping_json = args.output_dir / "bookkeeping.json"
    readme_md = args.output_dir / "README.md"
    ensure_clean_outputs(
        [
            rebuild_env,
            validate_env,
            profile_env,
            validation_template_md,
            bookkeeping_json,
            readme_md,
        ],
        args.allow_overwrite,
    )

    commands = build_commands(
        rebuild_env=rebuild_env,
        validate_env=validate_env,
        profile_env=profile_env,
        remote_archive_dir=args.remote_archive_dir,
        rebuild_output_dir=args.rebuild_output_dir,
    )
    generated_files = {
        rebuild_env.name: str(rebuild_env),
        validate_env.name: str(validate_env),
        profile_env.name: str(profile_env),
        validation_template_md.name: str(validation_template_md),
        bookkeeping_json.name: str(bookkeeping_json),
        readme_md.name: str(readme_md),
    }
    bookkeeping = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "operator": OPERATOR_NAME,
        "current_candidate_source": str(args.candidate_json),
        "current_best_staging": payload.get("current_best_staging"),
        "current_profile_json": payload.get("current_profile_json"),
        "reference_profile_json": payload.get("reference_profile_json"),
        "operator_context": candidate,
        "best_staging_db": str(args.best_staging_db),
        "remote_archive_dir": args.remote_archive_dir,
        "rebuild_base_env": str(args.rebuild_base_env),
        "validate_inference_base_env": str(args.validate_inference_base_env),
        "profile_base_env": str(args.profile_base_env),
        "manual_artifact_sha256": args.manual_artifact_sha256 or None,
        "why_rebuild_only": (
            "run_phytium_current_safe_one_shot.sh supports rebuild-only staging validation, "
            "while run_phytium_current_safe_staging_validate.sh ultimately expects a positive "
            "tuning budget."
        ),
        "generated_files": generated_files,
        "commands": commands,
    }

    write_text(
        rebuild_env,
        build_rebuild_env(args=args, candidate_payload=payload, candidate=candidate),
    )
    write_text(validate_env, build_validate_env(args=args))
    write_text(profile_env, build_profile_env(args=args))
    write_text(
        validation_template_md,
        build_validation_report_template(
            candidate_payload=payload,
            candidate=candidate,
            args=args,
            commands=commands,
        ),
    )
    write_text(bookkeeping_json, json.dumps(bookkeeping, indent=2, ensure_ascii=False) + "\n")
    write_text(
        readme_md,
        build_readme(
            candidate_payload=payload,
            candidate=candidate,
            args=args,
            generated_files=generated_files,
            commands=commands,
        ),
    )

    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
