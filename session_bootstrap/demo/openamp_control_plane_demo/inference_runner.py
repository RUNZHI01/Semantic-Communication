from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from board_access import BoardAccessConfig
from remote_failure import build_diagnostics, build_operator_message, classify_status_category


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REMOTE_RECONSTRUCTION_SCRIPT = (
    PROJECT_ROOT / "session_bootstrap" / "scripts" / "run_remote_current_real_reconstruction.sh"
)
ARTIFACT_SHA_MISMATCH_RE = re.compile(
    r"artifact sha256 mismatch path=(?P<path>\S+) expected=(?P<expected>[0-9A-Fa-f]{64}) actual=(?P<actual>[0-9A-Fa-f]{64})"
)


def parse_json_stdout(raw: str) -> dict[str, Any]:
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    raise ValueError("runner produced no JSON payload")


def extract_artifact_sha_mismatch(*values: str) -> dict[str, str]:
    for raw in values:
        match = ARTIFACT_SHA_MISMATCH_RE.search(raw or "")
        if match:
            return {
                "artifact_path": match.group("path"),
                "expected_sha256": match.group("expected").lower(),
                "actual_sha256": match.group("actual").lower(),
            }
    return {}


def run_remote_reconstruction(
    access: BoardAccessConfig,
    *,
    variant: str,
    max_inputs: int = 1,
    seed: int = 0,
    timeout_sec: float = 900.0,
) -> dict[str, Any]:
    missing = access.missing_inference_fields(variant)
    if missing:
        status_category = classify_status_category(status="config_error", missing_fields=missing)
        return {
            "status": "config_error",
            "status_category": status_category,
            "execution_mode": "fallback",
            "variant": variant,
            "message": build_operator_message("inference", status_category, include_fallback=True),
            "missing_fields": missing,
            "diagnostics": build_diagnostics(missing_fields=missing),
        }

    command = [
        "bash",
        str(REMOTE_RECONSTRUCTION_SCRIPT),
        "--variant",
        variant,
        "--max-inputs",
        str(max_inputs),
        "--seed",
        str(seed),
    ]
    env = access.build_subprocess_env()
    env["REMOTE_MODE"] = "ssh"

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "status_category": "timeout",
            "execution_mode": "fallback",
            "variant": variant,
            "message": build_operator_message("inference", "timeout", include_fallback=True),
            "missing_fields": [],
            "diagnostics": {},
        }
    except OSError as exc:
        status_category = classify_status_category(status="launch_error", error=str(exc))
        return {
            "status": "launch_error",
            "status_category": status_category,
            "execution_mode": "fallback",
            "variant": variant,
            "message": build_operator_message("inference", status_category, include_fallback=True),
            "missing_fields": [],
            "diagnostics": build_diagnostics(error=str(exc)),
        }

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        status_category = classify_status_category(status="error", stderr=stderr, stdout=stdout)
        diagnostics = build_diagnostics(stdout=stdout, stderr=stderr, returncode=result.returncode)
        if status_category == "artifact_mismatch":
            diagnostics.update(extract_artifact_sha_mismatch(stderr, stdout))
        return {
            "status": "error",
            "status_category": status_category,
            "execution_mode": "fallback",
            "variant": variant,
            "message": build_operator_message("inference", status_category, include_fallback=True),
            "missing_fields": [],
            "diagnostics": diagnostics,
        }

    try:
        summary = parse_json_stdout(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        status_category = classify_status_category(
            status="parse_error",
            stderr=stderr,
            stdout=stdout,
            error=str(exc),
        )
        return {
            "status": "parse_error",
            "status_category": status_category,
            "execution_mode": "fallback",
            "variant": variant,
            "message": build_operator_message("inference", status_category, include_fallback=True),
            "missing_fields": [],
            "diagnostics": build_diagnostics(stdout=stdout, stderr=stderr, error=str(exc)),
        }

    return {
        "status": "success",
        "status_category": "success",
        "execution_mode": "live",
        "variant": variant,
        "message": "已使用当前会话凭据触发远端推理。",
        "runner_summary": summary,
        "missing_fields": [],
        "diagnostics": {},
    }
