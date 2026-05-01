from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from board_access import BoardAccessConfig


def _discover_repo_root() -> Path:
    script_path = Path(__file__).resolve()
    candidates = [
        script_path.parents[4],
        Path.cwd(),
    ]
    candidates.extend(script_path.parents)

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "USRP292x").is_dir():
            return resolved

    return script_path.parents[4]


REPO_ROOT = _discover_repo_root()
DEFAULT_RUNNER = REPO_ROOT / "USRP292x" / "RunQpskFileBatchSpoolArq.py"
DEFAULT_INPUT_DIR = REPO_ROOT / "USRP292x" / "payloads" / "finalwork_webp5"
DEFAULT_INPUT_FILE = REPO_ROOT / "USRP292x" / "payloads" / "source_latent_wire_blob.bin"
DEFAULT_RUN_ROOT = REPO_ROOT / "USRP292x" / "qpsk_batch_spool_arq_runs"

RUNNER_SCRIPT_KEYS = ("MLKEM_USRP_RUNNER_SCRIPT", "USRP_RUNNER_SCRIPT")
INPUT_DIR_KEYS = ("MLKEM_USRP_INPUT_DIR", "USRP_INPUT_DIR")
INPUT_FILE_KEYS = ("MLKEM_USRP_INPUT_FILE", "USRP_INPUT_FILE")
RUN_ROOT_KEYS = ("MLKEM_USRP_RUN_ROOT", "USRP_RUN_ROOT")
MAX_ARQ_ROUNDS_KEYS = ("MLKEM_USRP_MAX_ARQ_ROUNDS", "USRP_MAX_ARQ_ROUNDS")
DECODE_BACKEND_KEYS = ("QPSK_DECODE_BACKEND",)
CPP_SYNC_MODE_KEYS = ("QPSK_CPP_SYNC_MODE",)
ARTIFACT_MODE_KEYS = ("USRP_ARTIFACT_MODE",)
BATCH_SIZE_KEYS = ("BATCH_SIZE",)
DECODE_WORKERS_KEYS = ("BATCH_DECODE_WORKERS",)
CHUNK_BYTES_KEYS = ("CHUNK_BYTES",)
FAST_ARQ_PROFILE_KEYS = ("USRP_FAST_ARQ_PROFILE",)
STOP_ON_FAIL_KEYS = ("USRP_STOP_ON_FAIL",)
TIMEOUT_SEC_KEYS = ("USRP_JOB_TIMEOUT_SEC", "MLKEM_USRP_JOB_TIMEOUT_SEC")


def _first_value(env_values: dict[str, str], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = str(env_values.get(key, "") or "").strip()
        if value:
            return value
    return default


def _resolve_existing_path(raw_value: str) -> Path | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    try:
        if path.exists():
            return path
    except OSError:
        return None
    return None


def _parse_int(raw_value: str, default: int) -> int:
    text = str(raw_value or "").strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def _parse_float(raw_value: str, default: float) -> float:
    text = str(raw_value or "").strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _parse_bool(raw_value: str, default: bool = False) -> bool:
    text = str(raw_value or "").strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _count_processed_from_results(results: list[dict[str, Any]]) -> int:
    processed = 0
    for item in results:
        rounds = int(item.get("rounds", 0) or 0)
        merge_summary = str(item.get("merge_summary") or "").strip()
        if rounds > 0 or merge_summary:
            processed += 1
    return processed


def _parse_progress_from_log(log_path: Path, *, fallback_target: int) -> dict[str, int]:
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "processed": 0,
            "pass_count": 0,
            "pending": fallback_target,
            "target": fallback_target,
        }

    progress_match = None
    for match in re.finditer(
        r"batch_progress\s+round=\d+\s+batch=\d+/\d+\s+processed=(\d+)/(\d+)\s+pass=(\d+)\s+pending=(\d+)",
        text,
    ):
        progress_match = match

    if progress_match is None:
        return {
            "processed": 0,
            "pass_count": 0,
            "pending": fallback_target,
            "target": fallback_target,
        }

    return {
        "processed": int(progress_match.group(1)),
        "target": int(progress_match.group(2)),
        "pass_count": int(progress_match.group(3)),
        "pending": int(progress_match.group(4)),
    }


class UsrpBatchSpoolJob:
    def __init__(
        self,
        access: BoardAccessConfig,
        *,
        variant: str,
        max_inputs: int,
        control_transport: str = "mlkem",
        control_preflight: dict[str, Any] | None = None,
    ) -> None:
        self.job_id = f"usrp-{int(time.time())}"
        self.variant = variant
        self._expected_outputs = max(1, int(max_inputs))
        self._control_transport = str(control_transport or "mlkem").strip().lower() or "mlkem"
        self._control_preflight = dict(control_preflight) if isinstance(control_preflight, dict) else None
        self._lock = threading.Lock()
        self._final_snapshot: dict[str, Any] | None = None
        self._process: subprocess.Popen[str] | None = None
        self._timed_out = False

        env_values = access.build_env()
        runner_path = _resolve_existing_path(_first_value(env_values, RUNNER_SCRIPT_KEYS)) or DEFAULT_RUNNER
        input_dir = _resolve_existing_path(_first_value(env_values, INPUT_DIR_KEYS)) or DEFAULT_INPUT_DIR
        input_file = _resolve_existing_path(_first_value(env_values, INPUT_FILE_KEYS)) or DEFAULT_INPUT_FILE
        run_root = _resolve_existing_path(_first_value(env_values, RUN_ROOT_KEYS)) or DEFAULT_RUN_ROOT
        run_id = f"cockpit_usrp_{self.job_id}"
        self._run_dir = Path(run_root) / run_id
        self._summary_path = self._run_dir / "batch_spool_summary.json"
        self._log_path = self._run_dir / "cockpit_usrp.log"
        self._runner_path = Path(runner_path)
        self._input_path = Path(input_dir) if Path(input_dir).exists() else Path(input_file)
        self._timeout_sec = max(120.0, _parse_float(_first_value(env_values, TIMEOUT_SEC_KEYS), 0.0) or 0.0)
        if self._timeout_sec <= 0.0:
            self._timeout_sec = max(300.0, float(self._expected_outputs) * 5.0)

        if not self._runner_path.is_file():
            self._final_snapshot = self._build_terminal_snapshot(
                status="config_error",
                status_category="config_error",
                message=f"USRP runner 不存在: {self._runner_path}",
            )
            return
        if not self._input_path.exists():
            self._final_snapshot = self._build_terminal_snapshot(
                status="config_error",
                status_category="config_error",
                message=f"USRP 输入不存在: {self._input_path}",
            )
            return

        self._run_dir.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(self._runner_path)]
        if self._input_path.is_dir():
            command.extend(["--input-dir", str(self._input_path), "--cycle-inputs"])
        else:
            command.extend(["--input", str(self._input_path)])
        command.extend([
            "--count",
            str(self._expected_outputs),
            "--run-id",
            run_id,
            "--run-root",
            str(run_root),
            "--max-arq-rounds",
            str(max(0, _parse_int(_first_value(env_values, MAX_ARQ_ROUNDS_KEYS), 2))),
            "--decode-backend",
            _first_value(env_values, DECODE_BACKEND_KEYS, "cpp"),
            "--cpp-sync-mode",
            _first_value(env_values, CPP_SYNC_MODE_KEYS, "header"),
            "--artifact-mode",
            _first_value(env_values, ARTIFACT_MODE_KEYS, "minimal"),
        ])

        batch_size = _parse_int(_first_value(env_values, BATCH_SIZE_KEYS), 0)
        if batch_size > 0:
            command.extend(["--batch-size", str(batch_size)])
        decode_workers = _parse_int(_first_value(env_values, DECODE_WORKERS_KEYS), 0)
        if decode_workers > 0:
            command.extend(["--decode-workers", str(decode_workers)])
        chunk_bytes = _parse_int(_first_value(env_values, CHUNK_BYTES_KEYS), 0)
        if chunk_bytes > 0:
            command.extend(["--chunk-bytes", str(chunk_bytes)])
        if _parse_bool(_first_value(env_values, FAST_ARQ_PROFILE_KEYS), False):
            command.append("--fast-arq-profile")
        if _parse_bool(_first_value(env_values, STOP_ON_FAIL_KEYS), False):
            command.append("--stop-on-fail")

        env = access.build_subprocess_env()
        env["PYTHONUNBUFFERED"] = "1"

        self._log_handle = self._log_path.open("w", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                env=env,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            self._log_handle.close()
            self._final_snapshot = self._build_terminal_snapshot(
                status="launch_error",
                status_category="launch_error",
                message=f"USRP runner 启动失败: {exc}",
            )
            return

        watcher = threading.Thread(target=self._wait_for_completion, daemon=True)
        watcher.start()

    def _artifact_paths(self) -> dict[str, str]:
        return {
            "run_dir": str(self._run_dir),
            "summary_path": str(self._summary_path),
            "runner_log_path": str(self._log_path),
        }

    def _build_progress_payload(
        self,
        *,
        state: str,
        label: str,
        percent: int,
        completed_count: int,
        expected_count: int,
        event_log: list[str] | None = None,
    ) -> dict[str, Any]:
        expected = max(1, int(expected_count))
        completed = max(0, min(int(completed_count), expected))
        return {
            "state": state,
            "label": label,
            "tone": "online" if state in {"running", "completed"} else "degraded",
            "percent": percent,
            "phase_percent": percent,
            "completed_count": completed,
            "expected_count": expected,
            "remaining_count": max(0, expected - completed),
            "completion_ratio": round(completed / expected, 4),
            "count_source": "usrp_batch_spool",
            "count_label": f"{completed} / {expected}",
            "current_stage": f"USRP 数据面 {completed}/{expected}",
            "stages": [
                {
                    "key": "usrp_batch_spool",
                    "label": "USRP batch-spool",
                    "status": "current" if state == "running" else ("done" if state == "completed" else "error"),
                    "detail": f"已完成 {completed}/{expected}",
                }
            ],
            "event_log": list(event_log or []),
        }

    def _build_terminal_snapshot(
        self,
        *,
        status: str,
        status_category: str,
        message: str,
        summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        summary = dict(summary or {})
        target_count = max(1, int(summary.get("target_count") or self._expected_outputs))
        pass_count = int(summary.get("pass_count") or 0)
        all_pass = bool(summary.get("all_pass")) if summary else False
        per_image_sec = float(summary.get("per_image_sec") or 0.0)
        payload_airtime_ms_mean = float(summary.get("payload_airtime_ms_mean") or 0.0)
        decode_total_wall_sec_mean = float(summary.get("decode_total_wall_sec_mean") or 0.0)
        merge_wall_sec_mean = float(summary.get("merge_wall_sec_mean") or 0.0)
        diagnostics = {
            "transport_mode": "usrp_batch_spool",
            "summary_path": str(self._summary_path),
            "runner_log_path": str(self._log_path),
        }
        if self._control_preflight:
            diagnostics["control_preflight"] = self._control_preflight
        if summary:
            diagnostics["usrp_summary"] = summary

        runner_summary = {
            "processed_count": pass_count if all_pass else int(summary.get("pass_count") or 0),
            "input_count": target_count,
            "max_inputs": target_count,
            "pipeline": {
                "load_ms": 0.0,
                "vm_init_ms": 0.0,
                "ms_per_image": round(per_image_sec * 1000.0, 3) if per_image_sec > 0 else None,
                "run_mean_ms": round(per_image_sec * 1000.0, 3) if per_image_sec > 0 else None,
                "run_median_ms": round(per_image_sec * 1000.0, 3) if per_image_sec > 0 else None,
            },
        }
        wrapper_summary = {
            "result": "success" if status == "success" else "runner_failed",
            "transport_mode": "usrp_batch_spool",
            "per_image_ms": round(per_image_sec * 1000.0, 3) if per_image_sec > 0 else None,
            "radio_metrics": {
                "payload_airtime_ms_mean": round(payload_airtime_ms_mean, 3),
                "decode_total_wall_sec_mean": round(decode_total_wall_sec_mean * 1000.0, 3),
                "merge_wall_sec_mean": round(merge_wall_sec_mean * 1000.0, 3),
                "estimated_non_airtime_non_decode_non_merge_wall_sec_mean": round(
                    float(summary.get("estimated_non_airtime_non_decode_non_merge_wall_sec_mean") or 0.0) * 1000.0,
                    3,
                ),
                "compared_transmitted_bytes_mean": round(float(summary.get("compared_transmitted_bytes_mean") or 0.0), 3),
            },
            "radio_sample_count": int(summary.get("pass_count") or 0),
        }
        progress = self._build_progress_payload(
            state="completed" if status == "success" else "fallback",
            label="USRP 数据面完成" if status == "success" else "USRP 数据面失败",
            percent=100 if status == "success" else int(round((pass_count / target_count) * 100)),
            completed_count=pass_count,
            expected_count=target_count,
            event_log=[],
        )
        return {
            "status": status,
            "request_state": "completed",
            "status_category": status_category,
            "execution_mode": "live" if status == "success" else "fallback",
            "variant": self.variant,
            "message": message,
            "control_transport": self._control_transport,
            "data_transport": "usrp",
            "control_handshake_complete": self._control_transport != "none",
            "runner_summary": runner_summary,
            "wrapper_summary": wrapper_summary,
            "diagnostics": diagnostics,
            "progress": progress,
            "artifacts": self._artifact_paths(),
        }

    def _wait_for_completion(self) -> None:
        assert self._process is not None
        try:
            rc = self._process.wait(timeout=self._timeout_sec)
        except subprocess.TimeoutExpired:
            self._timed_out = True
            self._process.kill()
            rc = self._process.wait()
        finally:
            self._log_handle.close()

        summary = _safe_read_json(self._summary_path)
        if self._timed_out:
            snapshot = self._build_terminal_snapshot(
                status="fallback",
                status_category="timeout",
                message="USRP 数据面批处理超时，已回退到归档样例。",
                summary=summary,
            )
        elif rc == 0 and bool(summary.get("all_pass")):
            snapshot = self._build_terminal_snapshot(
                status="success",
                status_category="success",
                message="混合链路模式已完成 USRP 数据面传输；图像对比继续使用归档样例，链路指标来自当前 2922 批处理结果。",
                summary=summary,
            )
        else:
            fail_count = int(summary.get("fail_count") or 0)
            detail = f"fail_count={fail_count}" if fail_count > 0 else f"rc={rc}"
            snapshot = self._build_terminal_snapshot(
                status="fallback",
                status_category="error",
                message=f"USRP 数据面批处理未全部成功（{detail}），已回退到归档样例。",
                summary=summary,
            )

        with self._lock:
            self._final_snapshot = snapshot

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._final_snapshot is not None:
                return dict(self._final_snapshot)

        summary = _safe_read_json(self._summary_path)
        target_count = max(1, int(summary.get("target_count") or self._expected_outputs))
        results = summary.get("results") if isinstance(summary.get("results"), list) else []
        processed_count = _count_processed_from_results(results) if results else 0
        pass_count = int(summary.get("pass_count") or 0)

        log_progress = _parse_progress_from_log(self._log_path, fallback_target=target_count)
        processed_count = max(processed_count, int(log_progress.get("processed") or 0))
        pass_count = max(pass_count, int(log_progress.get("pass_count") or 0))
        percent = int(round((processed_count / target_count) * 100)) if target_count > 0 else 0

        diagnostics = {
            "transport_mode": "usrp_batch_spool",
            "summary_path": str(self._summary_path),
            "runner_log_path": str(self._log_path),
        }
        if self._control_preflight:
            diagnostics["control_preflight"] = self._control_preflight

        return {
            "status": "running",
            "request_state": "running",
            "status_category": "running",
            "execution_mode": "live",
            "variant": self.variant,
            "message": "USRP 数据面 batch-spool 正在推进；界面继续使用归档样例图，无线链路指标来自当前 2922 运行时。",
            "control_transport": self._control_transport,
            "data_transport": "usrp",
            "control_handshake_complete": self._control_transport != "none",
            "runner_summary": {},
            "wrapper_summary": {},
            "diagnostics": diagnostics,
            "progress": self._build_progress_payload(
                state="running",
                label="USRP 数据面传输中",
                percent=percent,
                completed_count=processed_count,
                expected_count=target_count,
                event_log=[],
            ),
            "artifacts": self._artifact_paths(),
        }


def launch_local_usrp_reconstruction_job(
    access: BoardAccessConfig,
    *,
    variant: str,
    max_inputs: int,
    control_transport: str = "mlkem",
    control_preflight: dict[str, Any] | None = None,
) -> UsrpBatchSpoolJob:
    return UsrpBatchSpoolJob(
        access,
        variant=variant,
        max_inputs=max_inputs,
        control_transport=control_transport,
        control_preflight=control_preflight,
    )
