from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from board_access import BoardAccessConfig


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REMOTE_RECONSTRUCTION_SCRIPT = (
    PROJECT_ROOT / "session_bootstrap" / "scripts" / "run_remote_current_real_reconstruction.sh"
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
        return {
            "status": "config_error",
            "execution_mode": "fallback",
            "variant": variant,
            "message": "缺少远端推理所需配置。",
            "missing_fields": missing,
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
            "execution_mode": "fallback",
            "variant": variant,
            "message": "远端推理超时，已保留预录结果作为回退。",
            "missing_fields": [],
        }
    except OSError as exc:
        return {
            "status": "launch_error",
            "execution_mode": "fallback",
            "variant": variant,
            "message": "远端推理命令无法启动。",
            "error": str(exc),
            "missing_fields": [],
        }

    if result.returncode != 0:
        return {
            "status": "error",
            "execution_mode": "fallback",
            "variant": variant,
            "message": "远端推理执行失败，已回退到预录结果。",
            "stderr": (result.stderr or result.stdout).strip(),
            "missing_fields": [],
        }

    try:
        summary = parse_json_stdout(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "parse_error",
            "execution_mode": "fallback",
            "variant": variant,
            "message": "远端推理返回内容无法解析，已回退到预录结果。",
            "error": str(exc),
            "stdout": result.stdout.strip(),
            "missing_fields": [],
        }

    return {
        "status": "success",
        "execution_mode": "live",
        "variant": variant,
        "message": "已使用当前会话凭据触发远端推理。",
        "runner_summary": summary,
        "missing_fields": [],
    }
