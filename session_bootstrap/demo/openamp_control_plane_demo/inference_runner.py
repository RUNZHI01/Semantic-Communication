from __future__ import annotations

import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import tempfile
from threading import Lock, Thread
import time
from typing import Any

from board_access import BoardAccessConfig
from remote_failure import build_diagnostics, build_operator_message, classify_status_category


PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
DEFAULT_HEARTBEAT_INTERVAL_SEC = 0.5
DEFAULT_LIVE_CONTROL_HOOK_TIMEOUT_SEC = 30.0
MIN_LIVE_CONTROL_HOOK_TIMEOUT_SEC = 5.0
# Demo live runs stay on a fixed 300-image budget so baseline/current remain aligned
# without drifting into a full dataset benchmark.
DEFAULT_MAX_INPUTS = 300
DEFAULT_SEED = 0
UINT32_MAX = (1 << 32) - 1
DEMO_MODE_ENV = "OPENAMP_DEMO_MODE"
DEMO_MAX_INPUTS_ENV = "OPENAMP_DEMO_MAX_INPUTS"

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


def hook_transport_failed(response: dict[str, Any]) -> bool:
    transport_status = str(response.get("transport_status") or "").strip().lower()
    if not transport_status:
        return False
    return transport_status.endswith("_failed")


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


def hook_status_category(response: dict[str, Any]) -> str | None:
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
        "last_fault_name",
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
        "last_fault_name",
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
        guard = (
            safe_nested(response, "rx_frame", "status_resp", "guard_state_name")
            or response.get("guard_state_name")
            or response.get("transport_status")
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
    else:
        completed_count = count_completed_images_from_runner_log(runner_log_path)
        count_source = "runner_log.sample_latency_lines"

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
        if transport_status == "permission_gate" and deny_note:
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
        if stage["status"] in {"current", "error"}:
            current_stage = stage["label"]
            break
        if stage["status"] == "done":
            current_stage = stage["label"]

    if request_state == "completed" and final_status == "success":
        label = "真实在线推进"
        tone = "online"
    elif request_state == "completed":
        label = "在线失败已回退"
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


def expected_sha_for_variant(access: BoardAccessConfig, variant: str) -> str:
    values = access.build_env()
    if variant == "baseline":
        return str(values.get("INFERENCE_BASELINE_EXPECTED_SHA256") or values.get("INFERENCE_EXPECTED_SHA256") or "")
    return str(values.get("INFERENCE_CURRENT_EXPECTED_SHA256") or values.get("INFERENCE_EXPECTED_SHA256") or "")


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
    if expected_sha_for_variant(access, variant):
        return []
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
            if variant == "baseline":
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
            expected_sha_for_variant(access, variant),
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
        remote_project_root = str(values.get("REMOTE_PROJECT_ROOT") or values.get("OPENAMP_REMOTE_PROJECT_ROOT") or "")
        remote_jscc_dir = str(values.get("REMOTE_JSCC_DIR") or "")
        if remote_project_root:
            command.extend(["--remote-project-root", remote_project_root])
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
        last_hook_response = latest_hook_response(trace_events)
        hook_error_text = control_hook_error_text(last_hook_response)

        if timed_out:
            status = "timeout"
            status_category = "timeout"
            runner_summary: dict[str, Any] = {}
            message = build_inference_message(status_category, variant=self.variant, include_fallback=True)
        elif (self._process.returncode or 0) == 0:
            try:
                runner_summary = parse_runner_summary_from_log(self._runner_log_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                status = "parse_error"
                status_category = classify_status_category(
                    status="parse_error",
                    stdout=stdout,
                    stderr=stderr,
                    error="\n".join(part for part in (str(exc), hook_error_text) if part),
                )
                runner_summary = {}
                message = build_inference_message(status_category, variant=self.variant, include_fallback=True)
            else:
                status = "success"
                status_category = "success"
                message = "OpenAMP 控制面已完成作业下发、板端执行与结果回收。"
        else:
            status = "error"
            status_category = hook_status_category(last_hook_response) or classify_status_category(
                status="error",
                stdout=stdout,
                stderr=stderr,
                error=hook_error_text,
            )
            runner_summary = {}
            if wrapper_summary.get("result") == "denied_by_control_hook":
                if status_category != "error":
                    message = build_inference_message(status_category, variant=self.variant, include_fallback=True)
                else:
                    message = "OpenAMP 控制面未放行本次作业，界面已回退到归档样例。"
            else:
                message = build_inference_message(status_category, variant=self.variant, include_fallback=True)

        diagnostics = build_diagnostics(stdout=stdout, stderr=stderr, returncode=self._process.returncode)
        if status_category == "artifact_mismatch":
            diagnostics.update(extract_artifact_sha_mismatch(stderr, stdout))
        hook_diagnostics = control_hook_diagnostics(last_hook_response)
        if hook_diagnostics:
            diagnostics["control_hook"] = hook_diagnostics
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
