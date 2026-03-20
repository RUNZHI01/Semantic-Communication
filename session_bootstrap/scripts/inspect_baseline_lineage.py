#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPARE_ENV_GLOB = "session_bootstrap/tmp/inference_compare_scheme_a_fair_run_fixed_*.env"
DEFAULT_REBUILD_REPORT_GLOB = "session_bootstrap/reports/phytium_baseline_style_current_rebuild_*.json"
PAYLOAD_RUNNER = "./session_bootstrap/scripts/run_remote_tvm_inference_payload.sh"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract baseline/current artifact and runtime lineage from the fair "
            "Scheme A compare evidence plus the latest baseline-style current rebuild."
        )
    )
    parser.add_argument(
        "--compare-env",
        type=Path,
        help=(
            "Path to the fair compare env file. Defaults to the latest "
            f"{DEFAULT_COMPARE_ENV_GLOB}."
        ),
    )
    parser.add_argument(
        "--compare-log",
        type=Path,
        help=(
            "Path to the fair compare benchmark log. Defaults to the log derived from "
            "INFERENCE_EXECUTION_ID inside --compare-env."
        ),
    )
    parser.add_argument(
        "--current-rebuild-report",
        type=Path,
        help=(
            "Path to the baseline-style current rebuild JSON report. Defaults to the "
            f"latest {DEFAULT_REBUILD_REPORT_GLOB}."
        ),
    )
    return parser.parse_args()


def pick_latest(glob_pattern: str, label: str) -> Path:
    matches = sorted(PROJECT_ROOT.glob(glob_pattern))
    if not matches:
        raise SystemExit(f"ERROR: no {label} found for glob: {glob_pattern}")
    return matches[-1]


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def parse_shell_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env[key] = value
    return env


def parse_compare_payloads(path: Path) -> dict[str, dict[str, object]]:
    payloads: dict[str, dict[str, object]] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        variant = payload.get("variant")
        if variant not in {"baseline", "current"}:
            continue
        if "artifact_path" not in payload:
            continue
        payloads[str(variant)] = payload
    missing = {"baseline", "current"} - set(payloads)
    if missing:
        raise SystemExit(
            f"ERROR: missing compare payload JSON for variant(s): {', '.join(sorted(missing))}"
        )
    return payloads


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_remote_tvm_python_override(command: str | None) -> str | None:
    if not command:
        return None
    match = re.search(r"(?:^|\s)REMOTE_TVM_PYTHON=([^ ]+)", command)
    if not match:
        return None
    return match.group(1)


def derive_compare_log_path(compare_env: Path, env_vars: dict[str, str]) -> Path:
    run_id = env_vars.get("INFERENCE_EXECUTION_ID") or env_vars.get("EXECUTION_ID")
    if not run_id:
        raise SystemExit(
            "ERROR: compare env does not define INFERENCE_EXECUTION_ID/EXECUTION_ID; "
            "pass --compare-log explicitly."
        )
    return PROJECT_ROOT / "session_bootstrap" / "logs" / f"{run_id}.log"


def to_abs_project_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except FileNotFoundError:
        return str(path)


def build_variant_summary(
    *,
    variant: str,
    payload: dict[str, object],
    command: str | None,
    env_remote_tvm_python: str | None,
) -> dict[str, object]:
    override_remote_tvm_python = extract_remote_tvm_python_override(command)
    effective_remote_tvm_python = override_remote_tvm_python or env_remote_tvm_python
    return {
        "variant": variant,
        "command": command,
        "archive_dir": payload.get("archive"),
        "artifact_path": payload.get("artifact_path"),
        "artifact_sha256": payload.get("artifact_sha256"),
        "artifact_sha256_expected": payload.get("artifact_sha256_expected"),
        "artifact_sha256_match": payload.get("artifact_sha256_match"),
        "artifact_size_bytes": payload.get("artifact_size_bytes"),
        "output_shape": payload.get("output_shape"),
        "output_dtype": payload.get("output_dtype"),
        "tvm_version": payload.get("tvm_version"),
        "device": payload.get("device"),
        "effective_remote_tvm_python": effective_remote_tvm_python,
        "remote_tvm_python_source": "command_override" if override_remote_tvm_python else "compare_env",
        "remote_tvm_python_override": override_remote_tvm_python,
    }


def build_current_rebuild_summary(report: dict[str, object]) -> dict[str, object]:
    remote_artifact = report.get("remote_artifact") or {}
    safe_runtime_inference = report.get("safe_runtime_inference") or {}
    payload = safe_runtime_inference.get("payload") or {}
    return {
        "report_id": report.get("report_id"),
        "mode": report.get("mode"),
        "archive_dir": payload.get("archive") or remote_artifact.get("archive_dir"),
        "artifact_path": payload.get("artifact_path") or remote_artifact.get("optimized_model_so"),
        "artifact_sha256": payload.get("artifact_sha256") or remote_artifact.get("optimized_model_sha256"),
        "artifact_sha256_expected": payload.get("artifact_sha256_expected"),
        "artifact_sha256_match": payload.get("artifact_sha256_match"),
        "artifact_size_bytes": payload.get("artifact_size_bytes") or remote_artifact.get("optimized_model_size_bytes"),
        "output_shape": payload.get("output_shape"),
        "output_dtype": payload.get("output_dtype"),
        "tvm_version": payload.get("tvm_version") or safe_runtime_inference.get("remote_tvm_version"),
        "device": payload.get("device") or safe_runtime_inference.get("device"),
        "effective_remote_tvm_python": safe_runtime_inference.get("remote_tvm_python"),
        "remote_tvm_python_source": "rebuild_report",
        "remote_tvm_python_override": None,
        "remote_archive_hash_match": remote_artifact.get("hash_match"),
    }


def shape_equals(left: object, right: object) -> bool:
    return left == right and left is not None


def build_board_probe_command(compare_env: Path) -> str:
    env_path = shlex.quote(to_abs_project_path(compare_env))
    project_root = shlex.quote(str(PROJECT_ROOT))
    payload_runner = shlex.quote(PAYLOAD_RUNNER)
    return (
        "bash -lc "
        + shlex.quote(
            f"cd {project_root} && "
            f"set -a; source {env_path}; set +a; "
            "INFERENCE_WARMUP_RUNS=0 INFERENCE_REPEAT=1 "
            f"bash {payload_runner} --variant baseline"
        )
    )


def main() -> int:
    args = parse_args()

    compare_env = require_file(
        args.compare_env or pick_latest(DEFAULT_COMPARE_ENV_GLOB, "fair compare env"),
        "fair compare env",
    )
    env_vars = parse_shell_env(compare_env)

    compare_log = require_file(
        args.compare_log or derive_compare_log_path(compare_env, env_vars),
        "fair compare log",
    )
    compare_payloads = parse_compare_payloads(compare_log)

    rebuild_report_path = require_file(
        args.current_rebuild_report
        or pick_latest(DEFAULT_REBUILD_REPORT_GLOB, "baseline-style current rebuild report"),
        "baseline-style current rebuild report",
    )
    rebuild_report = load_json(rebuild_report_path)

    compare_env_remote_tvm_python = env_vars.get("REMOTE_TVM_PYTHON")
    baseline = build_variant_summary(
        variant="baseline",
        payload=compare_payloads["baseline"],
        command=env_vars.get("INFERENCE_BASELINE_CMD"),
        env_remote_tvm_python=compare_env_remote_tvm_python,
    )
    current_compare = build_variant_summary(
        variant="current",
        payload=compare_payloads["current"],
        command=env_vars.get("INFERENCE_CURRENT_CMD"),
        env_remote_tvm_python=compare_env_remote_tvm_python,
    )
    current_rebuild = build_current_rebuild_summary(rebuild_report)

    baseline_archive = baseline.get("archive_dir")
    current_compare_archive = current_compare.get("archive_dir")
    current_rebuild_archive = current_rebuild.get("archive_dir")

    baseline_shape = baseline.get("output_shape")
    current_compare_shape = current_compare.get("output_shape")
    current_rebuild_shape = current_rebuild.get("output_shape")

    baseline_archive_touched_by_rebuild = baseline_archive == current_rebuild_archive
    current_archive_reused_between_compare_and_rebuild = current_compare_archive == current_rebuild_archive
    current_outputs_match_between_compare_and_rebuild = shape_equals(current_compare_shape, current_rebuild_shape)
    baseline_runtime_differs_from_current_compare = (
        baseline.get("effective_remote_tvm_python") != current_compare.get("effective_remote_tvm_python")
    )

    most_likely_249_source = (
        "baseline artifact/export lineage anchored at "
        f"{baseline.get('artifact_path')} "
        f"(archive {baseline_archive}, sha256 {baseline.get('artifact_sha256')})"
    )

    result = {
        "sources": {
            "compare_env": to_abs_project_path(compare_env),
            "compare_log": to_abs_project_path(compare_log),
            "current_rebuild_report": to_abs_project_path(rebuild_report_path),
        },
        "baseline_compare": baseline,
        "current_compare": current_compare,
        "current_rebuild": current_rebuild,
        "lineage_assessment": {
            "baseline_archive_touched_by_rebuild": baseline_archive_touched_by_rebuild,
            "current_archive_reused_between_compare_and_rebuild": current_archive_reused_between_compare_and_rebuild,
            "current_outputs_match_between_compare_and_rebuild": current_outputs_match_between_compare_and_rebuild,
            "baseline_runtime_differs_from_current_compare": baseline_runtime_differs_from_current_compare,
            "baseline_shape_differs_from_current_compare": baseline_shape != current_compare_shape,
            "baseline_shape_differs_from_current_rebuild": baseline_shape != current_rebuild_shape,
            "most_likely_249_source": most_likely_249_source,
            "most_likely_249_source_confidence": "high",
            "residual_runtime_uncertainty": (
                "baseline fair compare used a compat runtime override, so a pure runtime effect "
                "is not completely eliminated until the same baseline archive is rerun under the "
                "current-safe runtime"
            ),
        },
        "next_board_probe": {
            "purpose": (
                "Rerun the baseline archive through the payload runner without the compat "
                "runtime override to isolate artifact lineage from runtime-version effects."
            ),
            "command": build_board_probe_command(compare_env),
            "expected_interpretation": (
                "If this still reports output_shape [1, 3, 249, 249] while using the "
                "current-safe runtime, the baseline artifact/export lineage is effectively "
                "confirmed as the source of the 249x249 output."
            ),
        },
    }

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
