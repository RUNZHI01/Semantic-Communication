from __future__ import annotations

import json
from pathlib import Path
import re
import secrets
import shlex
import statistics
import subprocess
import sys
import tempfile
from threading import Lock, Thread
import time
from typing import Any

from board_access import BoardAccessConfig
from remote_failure import build_diagnostics, build_operator_message, classify_status_category


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = PROJECT_ROOT / "session_bootstrap" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from openamp_signed_manifest import load_signed_manifest_bundle, verify_signed_manifest_bundle  # noqa: E402

REMOTE_RECONSTRUCTION_SCRIPT = (
    PROJECT_ROOT / "session_bootstrap" / "scripts" / "run_remote_current_real_reconstruction.sh"
)
REMOTE_LEGACY_COMPAT_SCRIPT = PROJECT_ROOT / "session_bootstrap" / "scripts" / "run_remote_legacy_tvm_compat.sh"
OPENAMP_CONTROL_WRAPPER_SCRIPT = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_control_wrapper.py"
REMOTE_HOOK_PROXY_SCRIPT = Path(__file__).resolve().parent / "openamp_remote_hook_proxy.py"
ARTIFACT_SHA_MISMATCH_RE = re.compile(
    r"artifact sha256 mismatch path=(?P<path>\S+) expected=(?P<expected>[0-9A-Fa-f]{64}) actual=(?P<actual>[0-9A-Fa-f]{64})"
)
RUNNER_SAMPLE_LATENCY_PATTERNS = (
    re.compile(r"批量推理时间.*?:\s*([0-9]+(?:\.[0-9]+)?)\s*秒"),
    re.compile(r"batch\s+infer(?:ence)?\s+time.*?:\s*([0-9]+(?:\.[0-9]+)?)\s*s(?:ec(?:onds?)?)?", re.I),
)
RUNNER_LOG_TAIL_LINES = 40
DEFAULT_HEARTBEAT_INTERVAL_SEC = 0.5
DEFAULT_LIVE_CONTROL_HOOK_TIMEOUT_SEC = 30.0
MIN_LIVE_CONTROL_HOOK_TIMEOUT_SEC = 5.0
# Demo live runs stay on a fixed 300-image budget so baseline/current remain aligned
# without drifting into a full dataset benchmark.
DEFAULT_MAX_INPUTS = 300
DEFAULT_SEED = 0
TRUSTED_CURRENT_E2E_MS = 230.339
CURRENT_SLOWDOWN_MIN_DELTA_MS = 40.0
HEAVY_HEARTBEAT_DURATION_MS = 1500.0
HEAVY_HEARTBEAT_COUNT = 8
UINT32_MAX = (1 << 32) - 1
DEMO_MODE_ENV = "OPENAMP_DEMO_MODE"
DEMO_MAX_INPUTS_ENV = "OPENAMP_DEMO_MAX_INPUTS"
DEMO_ADMISSION_MODE_ENV = "OPENAMP_DEMO_ADMISSION_MODE"
DEMO_SIGNED_MANIFEST_FILE_ENV = "OPENAMP_DEMO_SIGNED_MANIFEST_FILE"
DEMO_SIGNED_MANIFEST_PUBLIC_KEY_ENV = "OPENAMP_DEMO_SIGNED_MANIFEST_PUBLIC_KEY"
DEMO_BASELINE_ADMISSION_MODE_ENV = "OPENAMP_DEMO_BASELINE_ADMISSION_MODE"
DEMO_BASELINE_SIGNED_MANIFEST_FILE_ENV = "OPENAMP_DEMO_BASELINE_SIGNED_MANIFEST_FILE"
DEMO_BASELINE_SIGNED_MANIFEST_PUBLIC_KEY_ENV = "OPENAMP_DEMO_BASELINE_SIGNED_MANIFEST_PUBLIC_KEY"

_LIVE_JOB_ID_LOCK = Lock()
_LAST_LIVE_JOB_ID = 0


def parse_json_stdout(raw: str) -> dict[str, Any]:
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    raise ValueError("runner produced no JSON payload")


def sanitize_wrapper_stdout_for_classification(raw: str) -> str:
    retained: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            retained.append(stripped)
            continue
        if isinstance(payload, dict) and "job_req_response" in payload and "status_response" in payload:
            continue
        retained.append(stripped)
    return "\n".join(retained)


def count_completed_images_from_runner_log(path: Path) -> int:
    if not path.exists():
        return 0
    completed = 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in RUNNER_SAMPLE_LATENCY_PATTERNS):
            completed += 1
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        progress_payload = payload.get("openamp_demo_progress")
        if not isinstance(progress_payload, dict):
            continue
        try:
            completed = max(completed, int(progress_payload.get("completed_count") or 0))
        except (TypeError, ValueError):
            continue
    return completed


def read_runner_log_tail(path: Path, *, max_lines: int = RUNNER_LOG_TAIL_LINES) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if max_lines > 0:
        lines = lines[-max_lines:]
    return "\n".join(line.rstrip() for line in lines if line.strip())


def generate_live_job_id() -> str:
    global _LAST_LIVE_JOB_ID

    # The board-side OpenAMP frame header packs job_id as an unsigned 32-bit integer.
    with _LIVE_JOB_ID_LOCK:
        candidate = 0
        for _ in range(8):
            candidate = secrets.randbelow(UINT32_MAX) + 1
            if candidate != _LAST_LIVE_JOB_ID:
                break
        if candidate == 0 or candidate == _LAST_LIVE_JOB_ID:
            candidate = (_LAST_LIVE_JOB_ID % UINT32_MAX) + 1
        _LAST_LIVE_JOB_ID = candidate
    return str(candidate)


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


def read_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_trace_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def short_time_label(value: str) -> str:
    if len(value) >= 19 and value[10] == "T":
        return value[11:19]
    return value


def safe_nested(mapping: dict[str, Any] | None, *keys: str) -> Any:
    current: Any = mapping or {}
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def last_event_by_phase(events: list[dict[str, Any]], phase: str) -> dict[str, Any] | None:
    for event in reversed(events):
        if str(event.get("phase") or "").upper() == phase:
            return event
    return None


def hook_response_for_event(event: dict[str, Any] | None) -> dict[str, Any]:
    response = safe_nested(event, "hook_result", "response")
    return response if isinstance(response, dict) else {}


def hook_response_for_phase(events: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    return hook_response_for_event(last_event_by_phase(events, phase))


def latest_hook_response(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        response = hook_response_for_event(event)
        if response:
            return response
    return {}


def hook_transport_status(response: dict[str, Any]) -> str:
    return str(response.get("transport_status") or "").strip().lower()


def hook_transport_failed(response: dict[str, Any]) -> bool:
    transport_status = hook_transport_status(response)
    if not transport_status:
        return False
    return transport_status not in {
        "status_resp_received",
        "job_ack_received",
        "heartbeat_ack_received",
        "job_done_status_received",
    }


def control_handshake_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    status_response = hook_response_for_phase(events, "STATUS_REQ")
    job_req_response = hook_response_for_phase(events, "JOB_REQ")
    status_req_transport = hook_transport_status(status_response)
    job_req_transport = hook_transport_status(job_req_response)
    status_req_confirmed = status_req_transport == "status_resp_received"
    job_req_confirmed = job_req_transport == "job_ack_received"
    return {
        "complete": status_req_confirmed and job_req_confirmed,
        "status_req_transport": status_req_transport,
        "job_req_transport": job_req_transport,
        "status_req_confirmed": status_req_confirmed,
        "job_req_confirmed": job_req_confirmed,
    }


def build_transport_timeout_handshake_message(handshake: dict[str, Any]) -> str:
    if not handshake:
        return ""

    notes: list[str] = []
    if handshake.get("status_req_transport") == "tx_ok_rx_timeout":
        notes.append("STATUS_REQ 已写入 RPMsg，但超时前未收到 STATUS_RESP")
    if handshake.get("job_req_transport") == "tx_ok_rx_timeout":
        notes.append("JOB_REQ 已写入 RPMsg，但超时前未收到 JOB_ACK")
    if not notes:
        return ""
    return "；".join(notes) + "。本次板端握手未完成，界面已回退到预录结果。"


def hook_fault_name(response: dict[str, Any]) -> str:
    candidates = (
        response.get("fault_name"),
        safe_nested(response, "rx_frame", "job_ack", "fault_name"),
        response.get("last_fault_name"),
        safe_nested(response, "rx_frame", "status_resp", "last_fault_name"),
    )
    for raw in candidates:
        value = str(raw or "").strip().upper()
        if value:
            return value
    return ""


def hook_guard_state_name(response: dict[str, Any]) -> str:
    candidates = (
        response.get("guard_state_name"),
        safe_nested(response, "rx_frame", "job_ack", "guard_state_name"),
        safe_nested(response, "rx_frame", "status_resp", "guard_state_name"),
        response.get("guard_state"),
        safe_nested(response, "rx_frame", "job_ack", "guard_state"),
        safe_nested(response, "rx_frame", "status_resp", "guard_state"),
    )
    for raw in candidates:
        value = str(raw or "").strip().upper()
        if value:
            return value
    return ""


def hook_active_job_id(response: dict[str, Any]) -> int:
    candidates = (
        response.get("active_job_id"),
        safe_nested(response, "rx_frame", "status_resp", "active_job_id"),
        safe_nested(response, "rx_frame", "job_ack", "active_job_id"),
    )
    for raw in candidates:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0


def hook_denied_by_active_job(response: dict[str, Any]) -> bool:
    return hook_fault_name(response) == "DUPLICATE_JOB_ID" and hook_guard_state_name(response) == "JOB_ACTIVE"


def hook_status_category(response: dict[str, Any]) -> str | None:
    if hook_denied_by_active_job(response):
        return "board_busy"
    if hook_fault_name(response) == "ARTIFACT_SHA_MISMATCH":
        return "artifact_mismatch"
    return None


def hook_uses_permission_gate(response: dict[str, Any]) -> bool:
    transport_status = str(response.get("transport_status") or "").strip().lower()
    if transport_status == "permission_gate":
        return True
    note = str(response.get("note") or "").strip().lower()
    return any(
        marker in note
        for marker in (
            "passwordless sudo",
            "permission denied",
            "/dev/rpmsg",
        )
    )


def control_hook_error_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "phase",
        "decision",
        "fault_name",
        "fault_code",
        "last_fault_name",
        "guard_state_name",
        "guard_state",
        "active_job_id",
        "source",
        "transport_status",
        "protocol_semantics",
        "note",
    ):
        value = response.get(key)
        if value:
            parts.append(str(value))
    if hook_uses_permission_gate(response):
        for key in ("rpmsg_ctrl", "rpmsg_dev"):
            value = response.get(key)
            if value:
                parts.append(str(value))
    return "\n".join(parts)


def control_hook_diagnostics(response: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for key in (
        "phase",
        "decision",
        "fault_name",
        "fault_code",
        "last_fault_name",
        "guard_state_name",
        "guard_state",
        "active_job_id",
        "source",
        "transport_status",
        "protocol_semantics",
        "note",
        "rpmsg_ctrl",
        "rpmsg_dev",
    ):
        value = response.get(key)
        if value not in (None, ""):
            details[key] = value
    device_status = response.get("device_status")
    if isinstance(device_status, dict) and device_status:
        details["device_status"] = device_status
    return details


def format_trace_event(event: dict[str, Any]) -> str:
    phase = str(event.get("phase") or "UNKNOWN").upper()
    at = short_time_label(str(event.get("at") or ""))
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    response = hook_response_for_event(event)

    if phase == "STATUS_REQ":
        transport = hook_transport_status(response)
        semantics = str(response.get("protocol_semantics") or "").strip()
        if transport and transport != "status_resp_received":
            detail = f"transport={transport}"
            if semantics:
                detail = f"{detail} / semantics={semantics}"
            return f"[{at}] STATUS_REQ -> {detail}"
        guard = (
            safe_nested(response, "rx_frame", "status_resp", "guard_state_name")
            or response.get("guard_state_name")
            or "PENDING"
        )
        fault = (
            safe_nested(response, "rx_frame", "status_resp", "last_fault_name")
            or response.get("fault_name")
            or "UNKNOWN"
        )
        return f"[{at}] STATUS_REQ -> guard={guard} / fault={fault}"
    if phase == "JOB_REQ":
        sha = str(payload.get("expected_sha256") or "")[:12]
        transport = hook_transport_status(response)
        if transport and transport != "job_ack_received":
            detail_parts = [f"trusted_sha={sha or 'NA'}", f"transport={transport}"]
            decision = str(response.get("decision") or "").strip().upper()
            if decision:
                detail_parts.append(f"decision={decision}")
            return f"[{at}] JOB_REQ -> {' / '.join(detail_parts)}"
        return f"[{at}] JOB_REQ -> trusted_sha={sha or 'NA'}"
    if phase == "JOB_ACK":
        decision = payload.get("decision") or "UNKNOWN"
        guard = payload.get("guard_state_name") or payload.get("guard_state") or "UNKNOWN"
        fault = payload.get("fault_name") or payload.get("fault_code") or "NONE"
        transport = payload.get("transport_status")
        if transport:
            return f"[{at}] JOB_ACK({decision}) -> guard={guard} / fault={fault} / transport={transport}"
        return f"[{at}] JOB_ACK({decision}) -> guard={guard} / fault={fault}"
    if phase == "HEARTBEAT":
        runtime_state = payload.get("runtime_state") or "RUNNING"
        elapsed_ms = payload.get("elapsed_ms")
        if elapsed_ms is None:
            return f"[{at}] HEARTBEAT -> runtime={runtime_state}"
        return f"[{at}] HEARTBEAT -> runtime={runtime_state} / elapsed={elapsed_ms} ms"
    if phase == "JOB_DONE":
        result_code = payload.get("result_code")
        runner_exit_code = payload.get("runner_exit_code")
        return f"[{at}] JOB_DONE -> result={result_code} / runner_exit={runner_exit_code}"
    return f"[{at}] {phase}"


def normalize_positive_int(value: Any) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    if normalized < 0:
        return None
    return normalized


def normalize_nonnegative_float(value: Any) -> float | None:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None
    if normalized < 0:
        return None
    return normalized


def hook_result_for_trace_event(event: dict[str, Any]) -> dict[str, Any]:
    hook_result = event.get("hook_result")
    return hook_result if isinstance(hook_result, dict) else {}


def build_control_hook_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    hook_events = [event for event in events if hook_result_for_trace_event(event)]
    if not hook_events:
        return {}

    timeout_events = [event for event in hook_events if hook_result_for_trace_event(event).get("timed_out")]
    nonzero_events = []
    duration_values: list[float] = []
    heartbeat_duration_values: list[float] = []

    for event in hook_events:
        hook_result = hook_result_for_trace_event(event)
        returncode = hook_result.get("returncode")
        if returncode not in (None, 0):
            nonzero_events.append(event)
        duration_ms = hook_result.get("duration_ms")
        try:
            numeric_duration = float(duration_ms)
        except (TypeError, ValueError):
            numeric_duration = None
        if numeric_duration is not None and numeric_duration >= 0:
            duration_values.append(numeric_duration)
            if str(event.get("phase") or "").upper() == "HEARTBEAT":
                heartbeat_duration_values.append(numeric_duration)

    timeout_phases = [str(event.get("phase") or "UNKNOWN").upper() for event in timeout_events]
    stats: dict[str, Any] = {
        "event_count": len(hook_events),
        "timeout_count": len(timeout_events),
        "timeout_phases": timeout_phases,
        "nonzero_return_count": len(nonzero_events),
    }
    if duration_values:
        stats["duration_total_ms"] = round(sum(duration_values), 3)
        stats["duration_median_ms"] = round(statistics.median(duration_values), 3)
        stats["duration_max_ms"] = round(max(duration_values), 3)
    if heartbeat_duration_values:
        stats["heartbeat_event_count"] = len(heartbeat_duration_values)
        stats["heartbeat_duration_total_ms"] = round(sum(heartbeat_duration_values), 3)
        stats["heartbeat_duration_median_ms"] = round(statistics.median(heartbeat_duration_values), 3)
        stats["heartbeat_duration_max_ms"] = round(max(heartbeat_duration_values), 3)
    return stats


def detect_current_live_slowdown(
    *,
    variant: str,
    runner_summary: dict[str, Any],
    control_hook_stats: dict[str, Any],
) -> dict[str, Any]:
    if variant != "current":
        return {}

    observed_run_median_ms = normalize_nonnegative_float(
        runner_summary.get("run_median_ms") or runner_summary.get("run_mean_ms")
    )
    if observed_run_median_ms is None:
        return {}

    delta_ms = observed_run_median_ms - TRUSTED_CURRENT_E2E_MS
    if delta_ms < CURRENT_SLOWDOWN_MIN_DELTA_MS:
        return {}

    heartbeat_event_count = normalize_positive_int(control_hook_stats.get("heartbeat_event_count")) or 0
    heartbeat_duration_median_ms = normalize_nonnegative_float(control_hook_stats.get("heartbeat_duration_median_ms"))
    heartbeat_duration_max_ms = normalize_nonnegative_float(control_hook_stats.get("heartbeat_duration_max_ms"))
    heartbeat_duration_total_ms = normalize_nonnegative_float(control_hook_stats.get("heartbeat_duration_total_ms"))

    diagnostics: dict[str, Any] = {
        "trusted_run_median_ms": round(TRUSTED_CURRENT_E2E_MS, 3),
        "observed_run_median_ms": round(observed_run_median_ms, 3),
        "delta_ms": round(delta_ms, 3),
        "heartbeat_event_count": heartbeat_event_count,
    }
    if heartbeat_duration_median_ms is not None:
        diagnostics["heartbeat_duration_median_ms"] = round(heartbeat_duration_median_ms, 3)
    if heartbeat_duration_max_ms is not None:
        diagnostics["heartbeat_duration_max_ms"] = round(heartbeat_duration_max_ms, 3)
    if heartbeat_duration_total_ms is not None:
        diagnostics["heartbeat_duration_total_ms"] = round(heartbeat_duration_total_ms, 3)

    likely_causes: list[str] = []
    if (
        heartbeat_event_count >= HEAVY_HEARTBEAT_COUNT
        and heartbeat_duration_median_ms is not None
        and heartbeat_duration_median_ms >= HEAVY_HEARTBEAT_DURATION_MS
    ):
        diagnostics["control_plane_interference_suspected"] = True
        likely_causes.append(
            "OpenAMP live heartbeat hook round-trips are expensive enough to perturb the same-board inference run."
        )
    if likely_causes:
        diagnostics["likely_causes"] = likely_causes
    return diagnostics


def build_current_live_slowdown_message(performance_diag: dict[str, Any]) -> str:
    observed = float(performance_diag["observed_run_median_ms"])
    trusted = float(performance_diag["trusted_run_median_ms"])
    heartbeat_event_count = int(performance_diag.get("heartbeat_event_count") or 0)
    heartbeat_duration_median_ms = normalize_nonnegative_float(performance_diag.get("heartbeat_duration_median_ms"))
    if performance_diag.get("control_plane_interference_suspected") and heartbeat_duration_median_ms is not None:
        return (
            f"板端作业已完成，但 live current 中位数 {observed:.3f} ms 高于 trusted {trusted:.3f} ms；"
            f"本次 {heartbeat_event_count} 次 HEARTBEAT hook 的中位往返约 {heartbeat_duration_median_ms:.0f} ms，"
            "最可能是 OpenAMP live 控制面心跳对同板推理造成了额外干扰。"
        )
    return (
        f"板端作业已完成，但 live current 中位数 {observed:.3f} ms 仍高于 trusted {trusted:.3f} ms；"
        "当前已保留真实在线结果，请继续复核板端负载与现场环境。"
    )


def build_completion_counts(
    *,
    runner_log_path: Path,
    runner_summary: dict[str, Any] | None = None,
    expected_outputs: int | None = None,
) -> dict[str, Any]:
    summary = runner_summary or {}

    summary_processed = normalize_positive_int(summary.get("processed_count"))
    if summary_processed is not None:
        completed_count = summary_processed
        count_source = "runner_summary.processed_count"
    elif runner_log_path.exists():
        completed_count = count_completed_images_from_runner_log(runner_log_path)
        count_source = "runner_log.sample_latency_lines"
    else:
        completed_count = 0
        count_source = "runner_log.missing"

    expected_count = (
        normalize_positive_int(summary.get("input_count"))
        or normalize_positive_int(summary.get("max_inputs"))
        or normalize_positive_int(expected_outputs)
        or 0
    )
    if expected_count > 0:
        completed_count = min(completed_count, expected_count)
    remaining_count = max(expected_count - completed_count, 0) if expected_count > 0 else 0
    completion_ratio = (completed_count / expected_count) if expected_count > 0 else 0.0
    percent = int(round(completion_ratio * 100.0))
    if expected_count > 0:
        percent = max(0, min(100, percent))
    count_label = f"{completed_count} / {expected_count}" if expected_count > 0 else str(completed_count)
    return {
        "completed_count": completed_count,
        "expected_count": expected_count,
        "remaining_count": remaining_count,
        "completion_ratio": round(completion_ratio, 4),
        "count_source": count_source,
        "count_label": count_label,
        "percent": percent,
    }


def build_progress_payload(
    events: list[dict[str, Any]],
    *,
    request_state: str,
    final_status: str | None = None,
    completed_count: int = 0,
    expected_count: int = 0,
    remaining_count: int = 0,
    completion_ratio: float = 0.0,
    count_source: str = "",
    count_label: str = "0",
    percent: int = 0,
) -> dict[str, Any]:
    failure_stage_labels = {
        "connected": "连接失败",
        "dispatched": "下发失败",
        "running": "执行失败",
        "returned": "返回失败",
    }
    handshake = control_handshake_summary(events)
    status_event = last_event_by_phase(events, "STATUS_REQ")
    job_req_event = last_event_by_phase(events, "JOB_REQ")
    job_ack_event = last_event_by_phase(events, "JOB_ACK")
    heartbeat_event = last_event_by_phase(events, "HEARTBEAT")
    job_done_event = last_event_by_phase(events, "JOB_DONE")
    status_response = hook_response_for_phase(events, "STATUS_REQ")
    job_req_response = hook_response_for_phase(events, "JOB_REQ")
    status_transport_failed = hook_transport_failed(status_response)
    job_req_transport_failed = hook_transport_failed(job_req_response)

    job_ack_payload = job_ack_event.get("payload") if isinstance(job_ack_event, dict) else {}
    if not isinstance(job_ack_payload, dict):
        job_ack_payload = {}
    decision = str(job_ack_payload.get("decision") or "").upper()

    connected_status = (
        "done"
        if status_event and not status_transport_failed
        else ("error" if status_transport_failed or (final_status and final_status != "success") else "pending")
    )
    dispatched_status = (
        "done"
        if job_req_event and not job_req_transport_failed
        else ("error" if job_req_transport_failed or (final_status and status_event) else "pending")
    )
    if decision == "DENY":
        running_status = "error"
    elif job_done_event:
        running_status = "done"
    elif heartbeat_event or decision == "ALLOW":
        running_status = "current"
    else:
        running_status = "pending"
    if request_state == "completed":
        if final_status == "success":
            returned_status = "done"
        elif final_status:
            returned_status = "error"
        else:
            returned_status = "pending"
    else:
        returned_status = "current" if job_done_event else "pending"

    connected_detail = "控制面已建立 STATUS_REQ/RESP 读数。"
    if status_event:
        status_resp = safe_nested(status_response, "rx_frame", "status_resp") or {}
        guard = status_resp.get("guard_state_name") or status_response.get("transport_status")
        fault = status_resp.get("last_fault_name") or "UNKNOWN"
        if guard:
            connected_detail = f"STATUS_RESP: {guard} / fault={fault}"
        status_note = str(status_response.get("note") or "").strip()
        if status_note and guard != "status_resp_received":
            connected_detail = status_note
    elif connected_status == "error":
        connected_detail = "本次在线链路未能完成初始状态确认。"

    dispatched_detail = "已向 OpenAMP 控制面提交 JOB_REQ。"
    if dispatched_status == "error":
        dispatched_detail = str(job_req_response.get("note") or "").strip() or "作业未能送达控制面。"

    running_detail = "等待板端接收并进入执行。"
    if decision == "ALLOW":
        guard = job_ack_payload.get("guard_state_name") or job_ack_payload.get("guard_state") or "JOB_ACTIVE"
        running_detail = f"JOB_ACK(ALLOW) / guard={guard}"
        if heartbeat_event:
            heartbeat_payload = heartbeat_event.get("payload") if isinstance(heartbeat_event.get("payload"), dict) else {}
            elapsed_ms = heartbeat_payload.get("elapsed_ms")
            if elapsed_ms is not None:
                running_detail = f"板端执行中，最近 HEARTBEAT elapsed={elapsed_ms} ms"
    elif decision == "DENY":
        fault = job_ack_payload.get("fault_name") or job_ack_payload.get("fault_code") or "UNKNOWN"
        deny_note = str(job_req_response.get("note") or job_ack_payload.get("note") or "").strip()
        transport_status = str(job_req_response.get("transport_status") or job_ack_payload.get("transport_status") or "").strip()
        if hook_denied_by_active_job(job_req_response):
            active_job_id = hook_active_job_id(job_req_response)
            active_suffix = f" / active_job_id={active_job_id}" if active_job_id else ""
            running_detail = (
                "JOB_ACK(DENY) / fault=DUPLICATE_JOB_ID / guard=JOB_ACTIVE"
                f"{active_suffix} / 板端已有活动作业，demo 保守阻断重复 launch"
            )
        elif transport_status == "permission_gate" and deny_note:
            running_detail = f"板端权限门禁：{deny_note}"
        elif deny_note:
            running_detail = f"JOB_ACK(DENY) / fault={fault} / {deny_note}"
        else:
            running_detail = f"JOB_ACK(DENY) / fault={fault}"

    returned_detail = "等待 JOB_DONE。"
    if job_done_event:
        job_done_payload = job_done_event.get("payload") if isinstance(job_done_event.get("payload"), dict) else {}
        returned_detail = (
            f"JOB_DONE 已回收，runner_exit={job_done_payload.get('runner_exit_code', 'NA')} "
            f"/ result={job_done_payload.get('result_code', 'NA')}"
        )
    elif returned_status == "error":
        if events and not handshake["complete"]:
            returned_detail = "STATUS_RESP/JOB_ACK 握手未完成，界面已切回归档样例。"
        else:
            returned_detail = "在线推进未完成，界面将切回归档样例。"

    stages = [
        {
            "key": "connected",
            "label": "已连接",
            "status": connected_status,
            "detail": connected_detail,
        },
        {
            "key": "dispatched",
            "label": "已下发",
            "status": dispatched_status,
            "detail": dispatched_detail,
        },
        {
            "key": "running",
            "label": "板端执行中",
            "status": running_status,
            "detail": running_detail,
        },
        {
            "key": "returned",
            "label": "已返回结果",
            "status": returned_status,
            "detail": returned_detail,
        },
    ]

    if request_state == "completed":
        phase_percent = 100
    elif running_status == "current":
        phase_percent = 76
    elif dispatched_status == "done":
        phase_percent = 52
    elif connected_status == "done":
        phase_percent = 28
    else:
        phase_percent = 8

    current_stage = "准备中"
    for stage in stages:
        if stage["status"] == "error":
            current_stage = failure_stage_labels.get(stage["key"], stage["label"])
            break
        if stage["status"] == "current":
            current_stage = stage["label"]
            break
        if stage["status"] == "done":
            current_stage = stage["label"]

    if request_state == "completed" and final_status == "success":
        label = "真实在线推进"
        tone = "online"
    elif request_state == "completed":
        label = "握手未完成，已回退" if events and not handshake["complete"] else "在线失败已回退"
        tone = "degraded"
    elif events:
        label = "真实在线推进"
        tone = "online"
    else:
        label = "等待板端响应"
        tone = "degraded"

    return {
        "state": request_state,
        "label": label,
        "tone": tone,
        "percent": percent,
        "phase_percent": phase_percent,
        "completed_count": completed_count,
        "expected_count": expected_count,
        "remaining_count": remaining_count,
        "completion_ratio": completion_ratio,
        "count_source": count_source,
        "count_label": count_label,
        "current_stage": current_stage,
        "stages": stages,
        "event_log": [format_trace_event(event) for event in events],
    }


def resolve_demo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def demo_variant_label(variant: str) -> str:
    return "Baseline" if variant == "baseline" else "Current"


def demo_admission_env_names(variant: str) -> dict[str, str]:
    if variant == "baseline":
        return {
            "mode": DEMO_BASELINE_ADMISSION_MODE_ENV,
            "bundle": DEMO_BASELINE_SIGNED_MANIFEST_FILE_ENV,
            "public_key": DEMO_BASELINE_SIGNED_MANIFEST_PUBLIC_KEY_ENV,
        }
    return {
        "mode": DEMO_ADMISSION_MODE_ENV,
        "bundle": DEMO_SIGNED_MANIFEST_FILE_ENV,
        "public_key": DEMO_SIGNED_MANIFEST_PUBLIC_KEY_ENV,
    }


def demo_signed_manifest_config(values: dict[str, str], *, variant: str) -> dict[str, str]:
    env_names = demo_admission_env_names(variant)
    return {
        "mode_env": env_names["mode"],
        "bundle_env": env_names["bundle"],
        "public_key_env": env_names["public_key"],
        "mode_value": str(values.get(env_names["mode"]) or "").strip().lower(),
        "bundle_value": str(values.get(env_names["bundle"]) or "").strip(),
        "public_key_value": str(values.get(env_names["public_key"]) or "").strip(),
    }


def expected_sha_for_variant_from_env(access: BoardAccessConfig, variant: str) -> str:
    values = access.build_env()
    if variant == "baseline":
        return str(values.get("INFERENCE_BASELINE_EXPECTED_SHA256") or values.get("INFERENCE_EXPECTED_SHA256") or "")
    return str(values.get("INFERENCE_CURRENT_EXPECTED_SHA256") or values.get("INFERENCE_EXPECTED_SHA256") or "")


def configured_admission_mode(values: dict[str, str], *, variant: str) -> str:
    config = demo_signed_manifest_config(values, variant=variant)
    raw_mode = config["mode_value"]
    if raw_mode:
        return raw_mode
    if config["bundle_value"]:
        return "signed_manifest_v1"
    return "legacy_sha"


def load_signed_manifest_summary(
    values: dict[str, str],
    *,
    variant: str,
    require_public_key: bool,
) -> dict[str, Any]:
    admission_mode = configured_admission_mode(values, variant=variant)
    if admission_mode != "signed_manifest_v1":
        raise ValueError("signed manifest summary requested while admission mode is not signed_manifest_v1")

    config = demo_signed_manifest_config(values, variant=variant)
    signed_manifest_file = config["bundle_value"]
    if not signed_manifest_file:
        raise ValueError(f"{config['bundle_env']} is required for signed-manifest demo admission")
    public_key_file = config["public_key_value"]
    if require_public_key and not public_key_file:
        raise ValueError(f"{config['public_key_env']} is required for signed-manifest demo admission")

    bundle_path = resolve_demo_path(signed_manifest_file)
    if not bundle_path.exists():
        raise ValueError(f"signed manifest bundle not found: {bundle_path}")
    bundle = load_signed_manifest_bundle(bundle_path)

    artifact_path_raw = str(bundle["manifest"]["artifact"]["path"])
    verification_kwargs: dict[str, Any] = {}
    artifact_path = resolve_demo_path(artifact_path_raw)
    if artifact_path.exists():
        verification_kwargs["artifact_path"] = artifact_path

    if public_key_file:
        public_key_path = resolve_demo_path(public_key_file)
        if not public_key_path.exists():
            raise ValueError(f"signed manifest public key not found: {public_key_path}")
        summary = verify_signed_manifest_bundle(bundle, public_key=public_key_path, **verification_kwargs)
        summary["bundle_path"] = str(bundle_path)
        summary["public_key_path"] = str(public_key_path)
        return summary

    return {
        "admission_mode": "signed_manifest_v1",
        "bundle_path": str(bundle_path),
        "public_key_path": "",
        "artifact_sha256": str(bundle["manifest"]["artifact"]["sha256"]),
        "artifact_path": artifact_path_raw,
        "artifact_size_bytes": int(bundle["manifest"]["artifact"]["size_bytes"]),
        "variant": str(bundle["manifest"]["artifact"]["variant"]),
        "deadline_ms": int(bundle["manifest"]["job"]["deadline_ms"]),
        "expected_outputs": int(bundle["manifest"]["job"]["expected_outputs"]),
        "job_flags": str(bundle["manifest"]["job"]["job_flags"]),
        "manifest_sha256": str(bundle["manifest_sha256"]),
        "key_id": str(bundle["signature"]["key_id"]),
        "signature_algorithm": str(bundle["signature"]["algorithm"]),
        "verified_locally": False,
        "artifact_match": None,
    }


def resolve_live_admission(access: BoardAccessConfig, *, variant: str) -> dict[str, Any]:
    values = access.build_env()
    env_names = demo_admission_env_names(variant)
    admission_mode = configured_admission_mode(values, variant=variant)
    expected_sha256 = expected_sha_for_variant_from_env(access, variant)
    if admission_mode == "legacy_sha":
        return {
            "mode": "legacy_sha",
            "expected_sha256": expected_sha256,
            "wrapper_args": [],
            "summary": None,
        }
    if admission_mode != "signed_manifest_v1":
        raise ValueError(
            f"unsupported {env_names['mode']} value {admission_mode!r}; use legacy_sha or signed_manifest_v1"
        )

    summary = load_signed_manifest_summary(values, variant=variant, require_public_key=True)
    if str(summary.get("variant") or "").strip().lower() != variant:
        raise ValueError(
            f"signed manifest variant {summary.get('variant')!r} does not match demo variant {variant!r}"
        )
    manifest_expected_sha256 = str(summary["artifact_sha256"])
    if expected_sha256 and expected_sha256 != manifest_expected_sha256:
        raise ValueError(
            f"configured {variant} expected SHA does not match the signed manifest artifact SHA"
        )
    return {
        "mode": "signed_manifest_v1",
        "expected_sha256": manifest_expected_sha256,
        "wrapper_args": [
            "--admission-mode",
            "signed_manifest_v1",
            "--signed-manifest-file",
            str(summary["bundle_path"]),
            "--signed-manifest-public-key",
            str(summary["public_key_path"]),
        ],
        "summary": summary,
    }


def describe_demo_admission(access: BoardAccessConfig, *, variant: str = "current") -> dict[str, Any]:
    values = access.build_env()
    config = demo_signed_manifest_config(values, variant=variant)
    variant_label = demo_variant_label(variant)
    admission_mode = configured_admission_mode(values, variant=variant)
    if admission_mode == "legacy_sha":
        expected_sha256 = expected_sha_for_variant_from_env(access, variant)
        note = f"{variant_label} 44-byte JOB_REQ stays on the legacy trusted SHA allowlist path."
        if expected_sha256:
            note = f"Legacy 44-byte JOB_REQ; expected_sha={expected_sha256[:12]}."
        elif variant == "baseline":
            note = "Baseline legacy live needs a formal baseline expected SHA to stay honest."
        return {
            "status": "ready" if expected_sha256 else "config_error",
            "mode": "legacy_sha",
            "label": "Legacy SHA allowlist",
            "tone": "online" if expected_sha256 else "degraded",
            "bundle_path": "",
            "public_key_path": "",
            "manifest_sha256": "",
            "artifact_sha256": expected_sha256,
            "key_id": "",
            "verified_locally": False,
            "artifact_match": None,
            "note": note,
        }

    if admission_mode != "signed_manifest_v1":
        return {
            "status": "config_error",
            "mode": admission_mode,
            "label": "Signed admission config error",
            "tone": "degraded",
            "bundle_path": "",
            "public_key_path": "",
            "manifest_sha256": "",
            "artifact_sha256": "",
            "key_id": "",
            "verified_locally": False,
            "artifact_match": None,
            "note": f"Unsupported {config['mode_env']}={admission_mode!r}.",
        }

    try:
        summary = resolve_live_admission(access, variant=variant)["summary"]
    except ValueError as err:
        return {
            "status": "config_error",
            "mode": "signed_manifest_v1",
            "label": "Signed manifest v1",
            "tone": "degraded",
            "bundle_path": config["bundle_value"],
            "public_key_path": config["public_key_value"],
            "manifest_sha256": "",
            "artifact_sha256": "",
            "key_id": "",
            "verified_locally": False,
            "artifact_match": None,
            "note": str(err),
        }

    assert summary is not None
    note_parts = [
        f"key_id={summary['key_id']}",
        f"bundle={Path(str(summary['bundle_path'])).name}",
    ]
    if summary.get("artifact_match") is True:
        note_parts.append(f"artifact sha={str(summary['artifact_sha256'])[:12]}")
    return {
        "status": "ready",
        "mode": "signed_manifest_v1",
        "label": "Signed manifest v1",
        "tone": "online" if summary.get("verified_locally") else "degraded",
        "bundle_path": str(summary["bundle_path"]),
        "public_key_path": str(summary["public_key_path"]),
        "manifest_sha256": str(summary["manifest_sha256"]),
        "artifact_sha256": str(summary["artifact_sha256"]),
        "key_id": str(summary["key_id"]),
        "verified_locally": bool(summary.get("verified_locally")),
        "artifact_match": summary.get("artifact_match"),
        "note": " | ".join(note_parts),
    }


def describe_demo_variant_support(access: BoardAccessConfig, *, variant: str) -> dict[str, Any]:
    admission = describe_demo_admission(access, variant=variant)
    variant_label = demo_variant_label(variant)
    if admission["mode"] == "signed_manifest_v1":
        ready = admission["status"] == "ready"
        note = f"{variant_label} signed-admission live path is supported."
        if not ready:
            note = f"{variant_label} signed-admission live path is not ready yet."
        if admission.get("note"):
            note = f"{note} {admission['note']}"
        return {
            "variant": variant,
            "status": admission["status"],
            "mode": admission["mode"],
            "label": f"{variant_label} signed live 已支持" if ready else f"{variant_label} signed live 未就绪",
            "tone": "online" if ready else "degraded",
            "note": note,
            "supported": ready,
            "launch_allowed": ready,
        }

    if admission["mode"] == "legacy_sha":
        ready = admission["status"] == "ready"
        note = f"{variant_label} live path is still using the legacy SHA allowlist."
        if ready and admission.get("artifact_sha256"):
            note = f"{note} expected_sha={str(admission['artifact_sha256'])[:12]}."
        elif variant == "baseline":
            note = "缺少 formal baseline expected SHA；第三幕仅保留 formal baseline 归档对比。"
        else:
            note = "Current live path is not ready; the legacy SHA allowlist still needs a trusted current expected SHA."
        return {
            "variant": variant,
            "status": admission["status"],
            "mode": admission["mode"],
            "label": f"{variant_label} legacy live" if ready else f"{variant_label} legacy live 未就绪",
            "tone": "degraded",
            "note": note,
            "supported": ready,
            "launch_allowed": ready,
        }

    note = str(admission.get("note") or f"{variant_label} live config error.")
    return {
        "variant": variant,
        "status": "config_error",
        "mode": str(admission.get("mode") or ""),
        "label": f"{variant_label} live 配置错误",
        "tone": "degraded",
        "note": note,
        "supported": False,
        "launch_allowed": False,
    }


def expected_sha_for_variant(access: BoardAccessConfig, variant: str) -> str:
    expected_sha256 = expected_sha_for_variant_from_env(access, variant)
    if expected_sha256:
        return expected_sha256
    values = access.build_env()
    if configured_admission_mode(values, variant=variant) != "signed_manifest_v1":
        return ""
    try:
        summary = load_signed_manifest_summary(values, variant=variant, require_public_key=False)
    except ValueError:
        return ""
    return str(summary.get("artifact_sha256") or "")


def configured_runner_command(access: BoardAccessConfig, variant: str) -> str:
    values = access.build_env()
    key = "INFERENCE_BASELINE_CMD" if variant == "baseline" else "INFERENCE_CURRENT_CMD"
    return str(values.get(key) or "").strip()


def default_runner_command(variant: str) -> str:
    script = REMOTE_LEGACY_COMPAT_SCRIPT if variant == "baseline" else REMOTE_RECONSTRUCTION_SCRIPT
    return shlex.join(["bash", str(script), "--variant", variant])


def supports_max_inputs_arg(command: str) -> bool:
    command_text = str(command or "")
    return REMOTE_RECONSTRUCTION_SCRIPT.name in command_text or REMOTE_LEGACY_COMPAT_SCRIPT.name in command_text


def supports_seed_arg(command: str) -> bool:
    command_text = str(command or "")
    return REMOTE_RECONSTRUCTION_SCRIPT.name in command_text


def append_runner_options(command: str, *, max_inputs: int, seed: int) -> str:
    if not supports_max_inputs_arg(command) and not supports_seed_arg(command):
        return command
    parts = shlex.split(command)
    changed = False
    if supports_max_inputs_arg(command) and "--max-inputs" not in parts:
        parts.extend(["--max-inputs", str(max_inputs)])
        changed = True
    if supports_seed_arg(command) and "--seed" not in parts:
        parts.extend(["--seed", str(seed)])
        changed = True
    if not changed:
        return command
    return shlex.join(parts)


def build_current_live_runner_command(*, max_inputs: int, seed: int) -> str:
    return shlex.join(
        [
            "bash",
            str(REMOTE_RECONSTRUCTION_SCRIPT),
            "--variant",
            "current",
            "--max-inputs",
            str(max_inputs),
            "--seed",
            str(seed),
        ]
    )


def build_runner_command(
    access: BoardAccessConfig,
    *,
    variant: str,
    max_inputs: int,
    seed: int,
) -> str:
    if variant == "current":
        # Demo live mode pins Current to the reconstruction runner so stale env files
        # cannot drag the UI back onto old single-image or compat semantics.
        return build_current_live_runner_command(max_inputs=max_inputs, seed=seed)
    command = configured_runner_command(access, variant) or default_runner_command(variant)
    return append_runner_options(command, max_inputs=max_inputs, seed=seed)


def build_inference_message(status_category: str, *, variant: str, include_fallback: bool = False) -> str:
    if status_category == "artifact_mismatch" and variant == "baseline":
        message = (
            "板端 baseline 工件与界面展示的 formal baseline expected SHA 不一致，"
            "OpenAMP 控制面已返回 ARTIFACT_SHA_MISMATCH。"
        )
        if include_fallback:
            message += " 当前已回退到预录结果。"
        return message
    return build_operator_message("inference", status_category, include_fallback=include_fallback)


def missing_control_plane_fields(access: BoardAccessConfig, variant: str) -> list[str]:
    values = access.build_env()
    admission_mode = configured_admission_mode(values, variant=variant)
    if admission_mode == "legacy_sha" and expected_sha_for_variant(access, variant):
        return []
    if admission_mode == "signed_manifest_v1":
        config = demo_signed_manifest_config(values, variant=variant)
        missing: list[str] = []
        if not config["bundle_value"]:
            missing.append(config["bundle_env"])
        if not config["public_key_value"]:
            missing.append(config["public_key_env"])
        return missing
    if variant == "baseline":
        return ["INFERENCE_BASELINE_EXPECTED_SHA256"]
    return ["INFERENCE_CURRENT_EXPECTED_SHA256"]


def parse_runner_summary_from_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError("runner log not found")
    return parse_json_stdout(path.read_text(encoding="utf-8"))


def live_control_hook_timeout_sec(timeout_sec: float) -> float:
    if timeout_sec <= 0:
        return DEFAULT_LIVE_CONTROL_HOOK_TIMEOUT_SEC
    return max(MIN_LIVE_CONTROL_HOOK_TIMEOUT_SEC, min(timeout_sec, DEFAULT_LIVE_CONTROL_HOOK_TIMEOUT_SEC))


class LiveRemoteReconstructionJob:
    def __init__(
        self,
        access: BoardAccessConfig,
        *,
        variant: str,
        max_inputs: int = DEFAULT_MAX_INPUTS,
        seed: int = DEFAULT_SEED,
        timeout_sec: float = 900.0,
        heartbeat_interval_sec: float = DEFAULT_HEARTBEAT_INTERVAL_SEC,
    ) -> None:
        self.job_id = generate_live_job_id()
        self.variant = variant
        self._expected_outputs = max_inputs
        self._timeout_sec = timeout_sec
        self._output_dir = Path(tempfile.mkdtemp(prefix="openamp_demo_live_", dir="/tmp"))
        self._trace_path = self._output_dir / "control_trace.jsonl"
        self._summary_path = self._output_dir / "wrapper_summary.json"
        self._runner_log_path = self._output_dir / "runner.log"
        self._lock = Lock()
        self._final_snapshot: dict[str, Any] | None = None
        self._process: subprocess.Popen[str] | None = None

        missing = access.missing_inference_fields(variant)
        if missing:
            status_category = classify_status_category(status="config_error", missing_fields=missing)
            self._final_snapshot = {
                "status": "config_error",
                "request_state": "completed",
                "status_category": status_category,
                "execution_mode": "fallback",
                "variant": variant,
                "message": build_inference_message(status_category, variant=variant, include_fallback=True),
                "runner_summary": {},
                "wrapper_summary": {},
                "diagnostics": build_diagnostics(missing_fields=missing),
                "progress": build_progress_payload(
                    [],
                    request_state="completed",
                    final_status="config_error",
                    expected_count=max_inputs,
                    remaining_count=max_inputs,
                    count_source="demo_default",
                    count_label=f"0 / {max_inputs}",
                ),
                "artifacts": self._artifact_paths(),
            }
            return

        control_plane_missing = missing_control_plane_fields(access, variant)
        if control_plane_missing:
            status_category = classify_status_category(status="config_error", missing_fields=control_plane_missing)
            if configured_admission_mode(access.build_env(), variant=variant) == "signed_manifest_v1":
                message = (
                    f"{demo_variant_label(variant)} live 已切到 signed-manifest admission，但本地签名包或公钥路径仍未补齐；"
                    "界面将先回退到归档样例。"
                )
            elif variant == "baseline":
                message = (
                    "当前演示缺少 formal baseline expected SHA，Baseline 无法诚实进入 OpenAMP live 准入；"
                    "界面将保留正式 baseline 对比结果。"
                )
            else:
                message = build_inference_message(status_category, variant=variant, include_fallback=True)
            self._final_snapshot = {
                "status": "config_error",
                "request_state": "completed",
                "status_category": status_category,
                "execution_mode": "fallback",
                "variant": variant,
                "message": message,
                "runner_summary": {},
                "wrapper_summary": {},
                "diagnostics": build_diagnostics(missing_fields=control_plane_missing),
                "progress": build_progress_payload(
                    [],
                    request_state="completed",
                    final_status="config_error",
                    expected_count=max_inputs,
                    remaining_count=max_inputs,
                    count_source="demo_default",
                    count_label=f"0 / {max_inputs}",
                ),
                "artifacts": self._artifact_paths(),
            }
            return

        try:
            admission = resolve_live_admission(access, variant=variant)
        except ValueError as exc:
            status_category = classify_status_category(status="config_error", error=str(exc))
            message = build_inference_message(status_category, variant=variant, include_fallback=True)
            if configured_admission_mode(access.build_env(), variant=variant) == "signed_manifest_v1":
                message = (
                    f"{demo_variant_label(variant)} live 已切到 signed-manifest admission，但本地签名包校验未通过；"
                    "界面将先回退到归档样例。"
                )
            self._final_snapshot = {
                "status": "config_error",
                "request_state": "completed",
                "status_category": status_category,
                "execution_mode": "fallback",
                "variant": variant,
                "message": message,
                "runner_summary": {},
                "wrapper_summary": {},
                "diagnostics": build_diagnostics(error=str(exc)),
                "progress": build_progress_payload(
                    [],
                    request_state="completed",
                    final_status="config_error",
                    expected_count=max_inputs,
                    remaining_count=max_inputs,
                    count_source="demo_default",
                    count_label=f"0 / {max_inputs}",
                ),
                "artifacts": self._artifact_paths(),
            }
            return

        env = access.build_subprocess_env()
        env["REMOTE_MODE"] = "ssh"
        env[DEMO_MODE_ENV] = "1"
        env[DEMO_MAX_INPUTS_ENV] = str(max_inputs)

        runner_cmd = build_runner_command(access, variant=variant, max_inputs=max_inputs, seed=seed)
        hook_cmd = self._build_hook_command(access)
        hook_timeout_sec = live_control_hook_timeout_sec(timeout_sec)
        command = [
            "python3",
            str(OPENAMP_CONTROL_WRAPPER_SCRIPT),
            "--job-id",
            self.job_id,
            "--variant",
            f"{variant}_reconstruction",
            "--runner-cmd",
            runner_cmd,
            "--expected-sha256",
            admission["expected_sha256"],
            "--expected-outputs",
            str(max_inputs),
            "--output-dir",
            str(self._output_dir),
            "--heartbeat-interval-sec",
            str(heartbeat_interval_sec),
            "--runner-timeout-sec",
            str(timeout_sec),
            "--transport",
            "hook",
            "--control-hook-timeout-sec",
            str(hook_timeout_sec),
            "--control-hook-cmd",
            hook_cmd,
        ]
        command.extend(admission["wrapper_args"])

        try:
            self._process = subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except OSError as exc:
            status_category = classify_status_category(status="launch_error", error=str(exc))
            self._final_snapshot = {
                "status": "launch_error",
                "request_state": "completed",
                "status_category": status_category,
                "execution_mode": "fallback",
                "variant": variant,
                "message": build_inference_message(status_category, variant=variant, include_fallback=True),
                "runner_summary": {},
                "wrapper_summary": {},
                "diagnostics": build_diagnostics(error=str(exc)),
                "progress": build_progress_payload(
                    [],
                    request_state="completed",
                    final_status="launch_error",
                    expected_count=max_inputs,
                    remaining_count=max_inputs,
                    count_source="demo_default",
                    count_label=f"0 / {max_inputs}",
                ),
                "artifacts": self._artifact_paths(),
            }
            return

        watcher = Thread(target=self._wait_for_completion, daemon=True)
        watcher.start()

    def _artifact_paths(self) -> dict[str, str]:
        return {
            "output_dir": str(self._output_dir),
            "control_trace_path": str(self._trace_path),
            "wrapper_summary_path": str(self._summary_path),
            "runner_log_path": str(self._runner_log_path),
        }

    def _build_hook_command(self, access: BoardAccessConfig) -> str:
        values = access.build_env()
        command = [
            "python3",
            str(REMOTE_HOOK_PROXY_SCRIPT),
            "--host",
            access.host,
            "--user",
            access.user,
            "--password",
            access.password,
            "--port",
            access.port,
            "--remote-output-root",
            f"/tmp/openamp_demo_hook/{self.job_id}",
        ]
        remote_jscc_dir = str(values.get("REMOTE_JSCC_DIR") or "")
        # Keep the live demo on the exact host-side bridge bundle that was previously validated.
        # Demo defaults may preload transient remote project roots from FIT manifests, and using
        # those board-side checkouts changes STATUS_REQ/JOB_REQ semantics before inference starts.
        if remote_jscc_dir:
            command.extend(["--remote-jscc-dir", remote_jscc_dir])
        return shlex.join(command)

    def _wait_for_completion(self) -> None:
        assert self._process is not None
        timed_out = False
        try:
            stdout, stderr = self._process.communicate(timeout=self._timeout_sec + 20.0)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._process.kill()
            stdout, stderr = self._process.communicate()

        wrapper_summary: dict[str, Any] = {}
        if self._summary_path.exists():
            try:
                wrapper_summary = read_json_file(self._summary_path)
            except (OSError, json.JSONDecodeError):
                wrapper_summary = {}
        if not wrapper_summary:
            try:
                wrapper_summary = parse_json_stdout(stdout)
            except (json.JSONDecodeError, ValueError):
                wrapper_summary = {}

        trace_events = load_trace_events(self._trace_path)
        handshake = control_handshake_summary(trace_events) if trace_events else {}
        transport_timeout_message = build_transport_timeout_handshake_message(handshake)
        last_hook_response = latest_hook_response(trace_events)
        hook_error_text = control_hook_error_text(last_hook_response)
        control_hook_stats = build_control_hook_stats(trace_events)
        classify_stdout = sanitize_wrapper_stdout_for_classification(stdout)
        runner_log_tail = read_runner_log_tail(self._runner_log_path)
        classification_error_text = "\n".join(part for part in (hook_error_text, runner_log_tail) if part)

        if timed_out:
            status = "timeout"
            status_category = "timeout"
            runner_summary: dict[str, Any] = {}
            message = transport_timeout_message or build_inference_message(
                status_category,
                variant=self.variant,
                include_fallback=True,
            )
            performance_diag: dict[str, Any] = {}
        elif (self._process.returncode or 0) == 0:
            try:
                runner_summary = parse_runner_summary_from_log(self._runner_log_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                status = "parse_error"
                status_category = classify_status_category(
                    status="parse_error",
                    stdout=classify_stdout,
                    stderr=stderr,
                    error="\n".join(part for part in (str(exc), classification_error_text) if part),
                )
                runner_summary = {}
                message = build_inference_message(status_category, variant=self.variant, include_fallback=True)
                performance_diag = {}
            else:
                status = "success"
                status_category = "success"
                performance_diag = detect_current_live_slowdown(
                    variant=self.variant,
                    runner_summary=runner_summary,
                    control_hook_stats=control_hook_stats,
                )
                if performance_diag:
                    message = build_current_live_slowdown_message(performance_diag)
                elif control_hook_stats.get("timeout_count", 0) > 0:
                    message = (
                        "板端执行已完成；控制 hook 超时已记录，界面不再将其误报为 runner timeout。"
                    )
                else:
                    message = "OpenAMP 控制面已完成作业下发、板端执行与结果回收。"
        else:
            status = "error"
            status_category = hook_status_category(last_hook_response) or classify_status_category(
                status="error",
                stdout=classify_stdout,
                stderr=stderr,
                error=classification_error_text,
            )
            runner_summary = {}
            performance_diag = {}
            if wrapper_summary.get("result") == "denied_by_control_hook":
                if transport_timeout_message:
                    message = transport_timeout_message
                elif status_category != "error":
                    message = build_inference_message(status_category, variant=self.variant, include_fallback=True)
                else:
                    message = "OpenAMP 控制面未放行本次作业，界面已回退到归档样例。"
            else:
                message = transport_timeout_message or build_inference_message(
                    status_category,
                    variant=self.variant,
                    include_fallback=True,
                )

        diagnostics = build_diagnostics(stdout=stdout, stderr=stderr, returncode=self._process.returncode)
        if runner_log_tail and status != "success":
            diagnostics["runner_log_tail"] = runner_log_tail
        if status_category == "artifact_mismatch":
            diagnostics.update(extract_artifact_sha_mismatch(stderr, stdout, runner_log_tail, hook_error_text))
        if handshake:
            diagnostics["control_handshake"] = handshake
        hook_diagnostics = control_hook_diagnostics(last_hook_response)
        if hook_diagnostics:
            diagnostics["control_hook"] = hook_diagnostics
        if control_hook_stats:
            diagnostics["control_hook_stats"] = control_hook_stats
        if performance_diag:
            diagnostics["performance_regression"] = performance_diag
        count_payload = build_completion_counts(
            runner_log_path=self._runner_log_path,
            runner_summary=runner_summary,
            expected_outputs=getattr(self, "_expected_outputs", DEFAULT_MAX_INPUTS),
        )

        final_snapshot = {
            "status": status,
            "request_state": "completed",
            "status_category": status_category,
            "execution_mode": "live" if status == "success" else "fallback",
            "variant": self.variant,
            "message": message,
            "control_handshake_complete": handshake.get("complete") if handshake else None,
            "runner_summary": runner_summary,
            "wrapper_summary": wrapper_summary,
            "diagnostics": diagnostics,
            "progress": build_progress_payload(
                trace_events,
                request_state="completed",
                final_status=status,
                **count_payload,
            ),
            "artifacts": self._artifact_paths(),
        }
        with self._lock:
            self._final_snapshot = final_snapshot

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._final_snapshot is not None:
                return dict(self._final_snapshot)

        trace_events = load_trace_events(self._trace_path)
        handshake = control_handshake_summary(trace_events) if trace_events else {}
        count_payload = build_completion_counts(
            runner_log_path=self._runner_log_path,
            expected_outputs=getattr(self, "_expected_outputs", DEFAULT_MAX_INPUTS),
        )
        return {
            "status": "running",
            "request_state": "running",
            "status_category": "running",
            "execution_mode": "live",
            "variant": self.variant,
            "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
            "control_handshake_complete": handshake.get("complete") if handshake else None,
            "runner_summary": {},
            "wrapper_summary": {},
            "diagnostics": {},
            "progress": build_progress_payload(trace_events, request_state="running", **count_payload),
            "artifacts": self._artifact_paths(),
        }


def launch_remote_reconstruction_job(
    access: BoardAccessConfig,
    *,
    variant: str,
    max_inputs: int = DEFAULT_MAX_INPUTS,
    seed: int = DEFAULT_SEED,
    timeout_sec: float = 900.0,
) -> LiveRemoteReconstructionJob:
    return LiveRemoteReconstructionJob(
        access,
        variant=variant,
        max_inputs=max_inputs,
        seed=seed,
        timeout_sec=timeout_sec,
    )


def run_remote_reconstruction(
    access: BoardAccessConfig,
    *,
    variant: str,
    max_inputs: int = DEFAULT_MAX_INPUTS,
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
            "message": build_inference_message(status_category, variant=variant, include_fallback=True),
            "missing_fields": missing,
            "diagnostics": build_diagnostics(missing_fields=missing),
        }

    runner_cmd = build_runner_command(access, variant=variant, max_inputs=max_inputs, seed=seed)
    command = ["bash", "-lc", runner_cmd]
    env = access.build_subprocess_env()
    env["REMOTE_MODE"] = "ssh"
    env[DEMO_MODE_ENV] = "1"
    env[DEMO_MAX_INPUTS_ENV] = str(max_inputs)

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
            "message": build_inference_message("timeout", variant=variant, include_fallback=True),
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
            "message": build_inference_message(status_category, variant=variant, include_fallback=True),
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
            "message": build_inference_message(status_category, variant=variant, include_fallback=True),
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
            "message": build_inference_message(status_category, variant=variant, include_fallback=True),
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
