#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import json
import os
from pathlib import Path
import select
import struct
import sys
import time
from typing import Any
import zlib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openamp_mock.protocol import Decision, FaultCode, MAGIC, MessageType, VERSION  # noqa: E402


HEADER_STRUCT = struct.Struct("<IHHIIII")
STATUS_RESP_STRUCT = struct.Struct("<IIIIII")
JOB_REQ_STRUCT = struct.Struct("<32sIII")
JOB_ACK_STRUCT = struct.Struct("<III")
HEARTBEAT_STRUCT = struct.Struct("<IIII")
HEARTBEAT_ACK_STRUCT = struct.Struct("<II")
JOB_DONE_STRUCT = struct.Struct("<IIII")

FLAG_NAME_TO_WIRE = {
    "payload": 1,
    "reconstruction": 2,
    "smoke": 3,
}
FLAG_WIRE_TO_NAME = {value: key for key, value in FLAG_NAME_TO_WIRE.items()}
RUNTIME_STATE_NAME_TO_WIRE = {
    "PRECHECK": 1,
    "RUNNING": 2,
    "FINALIZING": 3,
}
RUNTIME_STATE_WIRE_TO_NAME = {value: key for key, value in RUNTIME_STATE_NAME_TO_WIRE.items()}
GUARD_STATE_NAMES = {
    0: "BOOT",
    1: "READY",
    2: "JOB_ACTIVE",
    3: "WAIT_DONE",
    4: "DENY_PENDING",
    5: "FAULT_LATCHED",
}
DEFAULT_GUARD_STATE = 0
CONTROL_PATH_FAULT_CODE = int(FaultCode.NONE)
INPUT_RANGE_FAULT_CODE = int(FaultCode.ILLEGAL_PARAM_RANGE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Minimal Linux-side OpenAMP/RPMsg bridge for the phase-5 control plane. "
            "Direct mode preserves the existing STATUS_REQ probe. Hook mode also forwards "
            "minimal binary JOB_REQ/HEARTBEAT/JOB_DONE/SAFE_STOP frames and parses "
            "JOB_ACK/HEARTBEAT_ACK/STATUS_RESP results."
        )
    )
    parser.add_argument(
        "--rpmsg-ctrl",
        default="/dev/rpmsg_ctrl0",
        help="Existing rpmsg control node. The bridge only verifies its presence in this phase.",
    )
    parser.add_argument(
        "--rpmsg-dev",
        default="/dev/rpmsg0",
        help="Existing rpmsg endpoint device used for raw read/write.",
    )
    parser.add_argument(
        "--output-dir",
        default="session_bootstrap/reports/openamp_status_req_bridge_latest",
        help="Directory used to store tx/rx artifacts and summary JSON.",
    )
    parser.add_argument(
        "--phase",
        default="STATUS_REQ",
        help=(
            "Direct mode phase. Direct mode only forwards STATUS_REQ; "
            "hook mode also supports JOB_REQ, HEARTBEAT, JOB_DONE, and SAFE_STOP."
        ),
    )
    parser.add_argument("--job-id", type=int, default=0, help="job_id field used in the control header.")
    parser.add_argument("--seq", type=int, default=1, help="Sequence field used in the control header.")
    parser.add_argument(
        "--response-timeout-sec",
        type=float,
        default=2.0,
        help="How long to wait for a response after the request is sent.",
    )
    parser.add_argument(
        "--settle-timeout-sec",
        type=float,
        default=0.05,
        help="Extra read coalescing window after the first response bytes arrive.",
    )
    parser.add_argument(
        "--max-rx-bytes",
        type=int,
        default=4096,
        help="Maximum number of response bytes to retain.",
    )
    parser.add_argument(
        "--hook-stdin",
        action="store_true",
        help=(
            "Read wrapper hook event JSON from stdin. OPENAMP_PHASE/event.phase decides the phase. "
            "STATUS_REQ stays unchanged; JOB_REQ/HEARTBEAT/JOB_DONE/SAFE_STOP are forwarded as "
            "minimal binary control frames. Unsupported phases are denied locally."
        ),
    )
    parser.add_argument(
        "--require-devices",
        action="store_true",
        default=True,
        help="Require --rpmsg-ctrl and --rpmsg-dev to exist before probing.",
    )
    parser.add_argument(
        "--no-require-devices",
        dest="require_devices",
        action="store_false",
        help="Skip device existence checks. Useful only for local parsing tests.",
    )
    parser.add_argument(
        "--drain-before-send",
        action="store_true",
        default=True,
        help="Drain stale bytes from the endpoint before sending the new request.",
    )
    parser.add_argument(
        "--no-drain-before-send",
        dest="drain_before_send",
        action="store_false",
        help="Do not drain the endpoint before sending the request.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def resolve_output_dir(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_hex(path: Path, payload: bytes) -> None:
    path.write_text(payload.hex() + ("\n" if payload else ""), encoding="ascii")


def write_raw(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def compute_binary_header_crc(
    *,
    magic: int,
    version: int,
    msg_type: int,
    seq: int,
    job_id: int,
    payload_len: int,
) -> int:
    header_without_crc = struct.pack(
        "<IHHIII",
        magic,
        version,
        msg_type,
        seq,
        job_id,
        payload_len,
    )
    return zlib.crc32(header_without_crc) & 0xFFFFFFFF


def build_frame(*, msg_type: MessageType, seq: int, job_id: int, payload: bytes = b"") -> bytes:
    header_crc32 = compute_binary_header_crc(
        magic=MAGIC,
        version=VERSION,
        msg_type=int(msg_type),
        seq=seq,
        job_id=job_id,
        payload_len=len(payload),
    )
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        int(msg_type),
        seq,
        job_id,
        len(payload),
        header_crc32,
    )
    return header + payload


def safe_msg_name(value: int) -> str:
    try:
        return MessageType(value).name
    except ValueError:
        return f"UNKNOWN_{value:#x}"


def safe_fault_name(value: int) -> str:
    try:
        return FaultCode(value).name
    except ValueError:
        return f"UNKNOWN_{value:#x}"


def safe_decision_name(value: int) -> str:
    try:
        return Decision(value).name
    except ValueError:
        return f"UNKNOWN_{value:#x}"


def safe_guard_state_name(value: int) -> str:
    return GUARD_STATE_NAMES.get(value, f"UNKNOWN_{value:#x}")


def safe_runtime_state_name(value: int) -> str:
    return RUNTIME_STATE_WIRE_TO_NAME.get(value, f"UNKNOWN_{value:#x}")


def describe_transport_failure(*, phase: str, rpmsg_dev: Path, err: BaseException) -> tuple[str, str, str, str]:
    if isinstance(err, PermissionError) or (
        isinstance(err, OSError) and err.errno in {errno.EACCES, errno.EPERM}
    ):
        return (
            "linux_bridge_permission_guard",
            "permission_gate",
            "not_attempted",
            (
                f"{phase} could not access {rpmsg_dev}: {err}. "
                "The board-side bridge needs root or passwordless sudo for RPMsg device access."
            ),
        )
    return (
        "linux_bridge_transport_guard",
        "transport_error",
        "not_verified",
        f"{phase} transport failed before a valid response was received: {err}",
    )


def parse_frame(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "raw_len": len(payload),
        "is_protocol_frame": False,
        "is_valid_header_crc": False,
    }
    if len(payload) < HEADER_STRUCT.size:
        result["parse_error"] = "short_frame"
        return result
    magic, version, msg_type, seq, job_id, payload_len, header_crc32 = HEADER_STRUCT.unpack_from(payload)
    result.update(
        {
            "magic": magic,
            "version": version,
            "msg_type": msg_type,
            "msg_name": safe_msg_name(msg_type),
            "seq": seq,
            "job_id": job_id,
            "payload_len": payload_len,
            "header_crc32": header_crc32,
        }
    )
    expected_crc = compute_binary_header_crc(
        magic=magic,
        version=version,
        msg_type=msg_type,
        seq=seq,
        job_id=job_id,
        payload_len=payload_len,
    )
    result["expected_header_crc32"] = expected_crc
    result["is_valid_header_crc"] = expected_crc == header_crc32
    frame_len = HEADER_STRUCT.size + payload_len
    if magic != MAGIC:
        result["parse_error"] = "magic_mismatch"
        return result
    if len(payload) < frame_len:
        result["parse_error"] = "truncated_payload"
        return result
    body = payload[HEADER_STRUCT.size:frame_len]
    result["payload_hex"] = body.hex()
    result["is_protocol_frame"] = True
    if msg_type == int(MessageType.STATUS_RESP):
        result["status_resp"] = parse_status_resp_payload(body)
    elif msg_type == int(MessageType.HEARTBEAT):
        result["heartbeat"] = parse_heartbeat_payload(body)
    elif msg_type == int(MessageType.HEARTBEAT_ACK):
        result["heartbeat_ack"] = parse_heartbeat_ack_payload(body)
    elif msg_type == int(MessageType.JOB_DONE):
        result["job_done"] = parse_job_done_payload(body)
    elif msg_type == int(MessageType.JOB_REQ):
        result["job_req"] = parse_job_req_payload(body)
    elif msg_type == int(MessageType.JOB_ACK):
        result["job_ack"] = parse_job_ack_payload(body)
    return result


def parse_status_resp_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != STATUS_RESP_STRUCT.size:
        result["parse_error"] = "unexpected_status_resp_size"
        return result
    (
        guard_state,
        active_job_id,
        last_fault_code,
        heartbeat_ok,
        sticky_fault,
        total_fault_count,
    ) = STATUS_RESP_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "guard_state": guard_state,
            "guard_state_name": safe_guard_state_name(guard_state),
            "active_job_id": active_job_id,
            "last_fault_code": last_fault_code,
            "last_fault_name": safe_fault_name(last_fault_code),
            "heartbeat_ok": heartbeat_ok,
            "sticky_fault": sticky_fault,
            "total_fault_count": total_fault_count,
        }
    )
    return result


def parse_job_req_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != JOB_REQ_STRUCT.size:
        result["parse_error"] = "unexpected_job_req_size"
        return result
    expected_sha256, deadline_ms, expected_outputs, flags = JOB_REQ_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "expected_sha256_hex": expected_sha256.hex(),
            "deadline_ms": deadline_ms,
            "expected_outputs": expected_outputs,
            "flags": flags,
            "flag_name": FLAG_WIRE_TO_NAME.get(flags, f"unknown_{flags:#x}"),
        }
    )
    return result


def parse_heartbeat_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != HEARTBEAT_STRUCT.size:
        result["parse_error"] = "unexpected_heartbeat_size"
        return result
    runtime_state, elapsed_ms, completed_outputs, progress_x100 = HEARTBEAT_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "runtime_state": runtime_state,
            "runtime_state_name": safe_runtime_state_name(runtime_state),
            "elapsed_ms": elapsed_ms,
            "completed_outputs": completed_outputs,
            "progress_x100": progress_x100,
        }
    )
    return result


def parse_heartbeat_ack_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != HEARTBEAT_ACK_STRUCT.size:
        result["parse_error"] = "unexpected_heartbeat_ack_size"
        return result
    guard_state, heartbeat_ok = HEARTBEAT_ACK_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "guard_state": guard_state,
            "guard_state_name": safe_guard_state_name(guard_state),
            "heartbeat_ok": heartbeat_ok,
            "acknowledged": heartbeat_ok == 1,
        }
    )
    return result


def parse_job_done_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != JOB_DONE_STRUCT.size:
        result["parse_error"] = "unexpected_job_done_size"
        return result
    result_code, output_count, result_crc32, reserved = JOB_DONE_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "result_code": result_code,
            "output_count": output_count,
            "result_crc32": result_crc32,
            "reserved": reserved,
            "reported_success": result_code == 0,
        }
    )
    return result


def parse_job_ack_payload(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payload_len": len(payload),
        "parsed": False,
    }
    if len(payload) != JOB_ACK_STRUCT.size:
        result["parse_error"] = "unexpected_job_ack_size"
        return result
    decision, fault_code, guard_state = JOB_ACK_STRUCT.unpack(payload)
    result.update(
        {
            "parsed": True,
            "decision": decision,
            "decision_name": safe_decision_name(decision),
            "fault_code": fault_code,
            "fault_name": safe_fault_name(fault_code),
            "guard_state": guard_state,
            "guard_state_name": safe_guard_state_name(guard_state),
        }
    )
    return result


def read_hook_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as err:
        raise SystemExit(f"ERROR: failed to parse hook stdin JSON: {err}") from err
    if not isinstance(payload, dict):
        raise SystemExit("ERROR: hook stdin payload must be a JSON object.")
    return payload


def determine_phase(args: argparse.Namespace, hook_event: dict[str, Any]) -> str:
    event_phase = hook_event.get("phase") if isinstance(hook_event, dict) else None
    env_phase = os.environ.get("OPENAMP_PHASE")
    phase = str(event_phase or env_phase or args.phase).strip().upper()
    return phase or "STATUS_REQ"


def derive_job_id(args: argparse.Namespace, hook_event: dict[str, Any]) -> int:
    payload = hook_event.get("payload") if isinstance(hook_event, dict) else None
    if isinstance(payload, dict) and "job_id" in payload:
        try:
            return int(payload["job_id"])
        except (TypeError, ValueError):
            pass
    return args.job_id


def preflight_devices(*, rpmsg_ctrl: Path, rpmsg_dev: Path, require_devices: bool) -> dict[str, Any]:
    return {
        "rpmsg_ctrl": {
            "path": str(rpmsg_ctrl),
            "exists": rpmsg_ctrl.exists(),
            "used_for": "presence_check_only_in_phase5_prep",
        },
        "rpmsg_dev": {
            "path": str(rpmsg_dev),
            "exists": rpmsg_dev.exists(),
            "used_for": "read_write_transport",
        },
        "require_devices": require_devices,
    }


def require_existing_device(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"ERROR: {label} not found: {path}")


def drain_fd(fd: int, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes
    while remaining > 0:
        try:
            chunk = os.read(fd, remaining)
        except BlockingIOError:
            break
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def is_retryable_write_error(err: OSError) -> bool:
    return err.errno in {errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR}


def write_all(fd: int, payload: bytes, timeout_sec: float) -> int:
    end_time = time.monotonic() + timeout_sec
    written = 0
    view = memoryview(payload)
    while written < len(payload):
        try:
            chunk = os.write(fd, view[written:])
        except BlockingIOError:
            chunk = None
        except OSError as err:
            if not is_retryable_write_error(err):
                raise
            chunk = None
        if chunk is None:
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("write timeout")
            _, writable, _ = select.select([], [fd], [], remaining)
            if not writable:
                raise TimeoutError("write timeout")
            continue
        if chunk <= 0:
            raise OSError("rpmsg write returned zero bytes")
        written += chunk
    return written


def read_response(fd: int, max_bytes: int, timeout_sec: float, settle_timeout_sec: float) -> tuple[bytes, bool]:
    readable, _, _ = select.select([fd], [], [], timeout_sec)
    if not readable:
        return b"", True
    chunks: list[bytes] = []
    remaining = max_bytes
    settle_deadline = time.monotonic() + settle_timeout_sec
    while remaining > 0:
        try:
            chunk = os.read(fd, remaining)
        except BlockingIOError:
            chunk = b""
        if chunk:
            chunks.append(chunk)
            remaining -= len(chunk)
            settle_deadline = time.monotonic() + settle_timeout_sec
            continue
        wait = settle_deadline - time.monotonic()
        if wait <= 0:
            break
        readable, _, _ = select.select([fd], [], [], wait)
        if not readable:
            break
    return b"".join(chunks), False


def transact(
    *,
    rpmsg_dev: Path,
    tx_bytes: bytes,
    response_timeout_sec: float,
    settle_timeout_sec: float,
    max_rx_bytes: int,
    drain_before_send: bool,
) -> dict[str, Any]:
    fd = os.open(rpmsg_dev, os.O_RDWR | os.O_NONBLOCK)
    try:
        drained = b""
        if drain_before_send:
            drained = drain_fd(fd, max_rx_bytes)
        written = write_all(fd, tx_bytes, response_timeout_sec)
        rx_bytes, rx_timeout = read_response(fd, max_rx_bytes, response_timeout_sec, settle_timeout_sec)
        return {
            "drained_bytes": drained,
            "written_bytes": written,
            "rx_bytes": rx_bytes,
            "rx_timeout": rx_timeout,
        }
    finally:
        os.close(fd)


def classify_status_probe(
    *,
    phase: str,
    tx_bytes: bytes,
    rx_bytes: bytes,
    rx_timeout: bool,
) -> dict[str, Any]:
    tx_parsed = parse_frame(tx_bytes)
    if rx_timeout:
        return {
            "phase": phase,
            "transport_status": "tx_ok_rx_timeout",
            "protocol_semantics": "not_verified",
            "note": (
                "write to /dev/rpmsg0 succeeded but no response arrived before timeout. "
                "Do not claim STATUS_RESP semantics from this result."
            ),
            "tx_frame": tx_parsed,
            "rx_frame": None,
        }
    rx_parsed = parse_frame(rx_bytes)
    if rx_bytes == tx_bytes:
        return {
            "phase": phase,
            "transport_status": "transport_echo_only",
            "protocol_semantics": "not_implemented",
            "note": (
                "Received bytes exactly match the transmitted STATUS_REQ frame. "
                "That is consistent with the demo echo firmware, not with a real STATUS_RESP handler."
            ),
            "tx_frame": tx_parsed,
            "rx_frame": rx_parsed,
        }
    if rx_parsed.get("is_protocol_frame") and rx_parsed.get("msg_type") == int(MessageType.STATUS_RESP):
        status_resp = rx_parsed.get("status_resp", {})
        if status_resp.get("parsed"):
            return {
                "phase": phase,
                "transport_status": "status_resp_received",
                "protocol_semantics": "implemented",
                "note": "Received a decodable STATUS_RESP frame.",
                "tx_frame": tx_parsed,
                "rx_frame": rx_parsed,
            }
        return {
            "phase": phase,
            "transport_status": "status_resp_received_unparsed_payload",
            "protocol_semantics": "partially_verified",
            "note": "Received STATUS_RESP msg_type but payload shape does not match the expected 24-byte layout.",
            "tx_frame": tx_parsed,
            "rx_frame": rx_parsed,
        }
    return {
        "phase": phase,
        "transport_status": "unexpected_response",
        "protocol_semantics": "not_verified",
        "note": (
            "A response arrived, but it is neither a byte-for-byte echo nor a decodable STATUS_RESP frame. "
            "Treat transport as reachable but protocol semantics as unresolved."
        ),
        "tx_frame": tx_parsed,
        "rx_frame": rx_parsed,
    }


def build_job_transport_deny_summary(
    *,
    phase: str,
    tx_parsed: dict[str, Any],
    rx_parsed: dict[str, Any] | None,
    transport_status: str,
    protocol_semantics: str,
    note: str,
    source: str = "linux_bridge_transport_guard",
) -> dict[str, Any]:
    return {
        "phase": phase,
        "decision": "DENY",
        "fault_code": CONTROL_PATH_FAULT_CODE,
        "fault_name": safe_fault_name(CONTROL_PATH_FAULT_CODE),
        "guard_state": DEFAULT_GUARD_STATE,
        "guard_state_name": safe_guard_state_name(DEFAULT_GUARD_STATE),
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "tx_frame": tx_parsed,
        "rx_frame": rx_parsed,
    }


def classify_job_probe(
    *,
    phase: str,
    tx_bytes: bytes,
    rx_bytes: bytes,
    rx_timeout: bool,
) -> dict[str, Any]:
    tx_parsed = parse_frame(tx_bytes)
    if rx_timeout:
        return build_job_transport_deny_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=None,
            transport_status="tx_ok_rx_timeout",
            protocol_semantics="not_verified",
            note=(
                "JOB_REQ was written to /dev/rpmsg0 but no JOB_ACK arrived before timeout. "
                "The wrapper must deny locally instead of assuming admission."
            ),
        )
    rx_parsed = parse_frame(rx_bytes)
    if rx_bytes == tx_bytes:
        return build_job_transport_deny_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            transport_status="transport_echo_only",
            protocol_semantics="not_implemented",
            note=(
                "Received an exact echo of the transmitted JOB_REQ frame. "
                "That is not a firmware-backed JOB_ACK, so the wrapper must deny locally."
            ),
        )
    if rx_parsed.get("is_protocol_frame") and rx_parsed.get("msg_type") == int(MessageType.JOB_ACK):
        job_ack = rx_parsed.get("job_ack", {})
        if job_ack.get("parsed"):
            if job_ack.get("decision_name") not in {"ALLOW", "DENY"}:
                return build_job_transport_deny_summary(
                    phase=phase,
                    tx_parsed=tx_parsed,
                    rx_parsed=rx_parsed,
                    transport_status="job_ack_received_invalid_decision",
                    protocol_semantics="partially_verified",
                    note=(
                        "Received JOB_ACK with an unknown decision code. "
                        "The wrapper must deny locally unless firmware explicitly returns ALLOW."
                    ),
                )
            return {
                "phase": phase,
                "decision": job_ack["decision_name"],
                "fault_code": job_ack["fault_code"],
                "fault_name": job_ack["fault_name"],
                "guard_state": job_ack["guard_state"],
                "guard_state_name": job_ack["guard_state_name"],
                "source": "firmware_job_ack",
                "transport_status": "job_ack_received",
                "protocol_semantics": "implemented",
                "note": "Received a decodable JOB_ACK frame from firmware.",
                "tx_frame": tx_parsed,
                "rx_frame": rx_parsed,
            }
        return build_job_transport_deny_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            transport_status="job_ack_received_unparsed_payload",
            protocol_semantics="partially_verified",
            note=(
                "Received JOB_ACK msg_type but the payload shape does not match the expected 12-byte layout. "
                "The wrapper must deny locally."
            ),
        )
    return build_job_transport_deny_summary(
        phase=phase,
        tx_parsed=tx_parsed,
        rx_parsed=rx_parsed,
        transport_status="unexpected_response",
        protocol_semantics="not_verified",
        note=(
            "A response arrived after JOB_REQ, but it is not a decodable JOB_ACK frame. "
            "The wrapper must deny locally."
        ),
    )


def build_heartbeat_transport_summary(
    *,
    phase: str,
    tx_parsed: dict[str, Any],
    rx_parsed: dict[str, Any] | None,
    acknowledged: bool,
    heartbeat_ok: int,
    guard_state: int,
    source: str,
    transport_status: str,
    protocol_semantics: str,
    note: str,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "acknowledged": acknowledged,
        "heartbeat_ok": heartbeat_ok,
        "guard_state": guard_state,
        "guard_state_name": safe_guard_state_name(guard_state),
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "tx_frame": tx_parsed,
        "rx_frame": rx_parsed,
    }


def classify_heartbeat_probe(
    *,
    phase: str,
    tx_bytes: bytes,
    rx_bytes: bytes,
    rx_timeout: bool,
) -> dict[str, Any]:
    tx_parsed = parse_frame(tx_bytes)
    if rx_timeout:
        return build_heartbeat_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=None,
            acknowledged=False,
            heartbeat_ok=0,
            guard_state=DEFAULT_GUARD_STATE,
            source="linux_bridge_transport_guard",
            transport_status="tx_ok_rx_timeout",
            protocol_semantics="not_verified",
            note=(
                "HEARTBEAT was written to /dev/rpmsg0 but no HEARTBEAT_ACK arrived before timeout. "
                "Treat the transport as reachable but the heartbeat semantics as unverified."
            ),
        )
    rx_parsed = parse_frame(rx_bytes)
    if rx_bytes == tx_bytes:
        return build_heartbeat_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            heartbeat_ok=0,
            guard_state=DEFAULT_GUARD_STATE,
            source="linux_bridge_transport_guard",
            transport_status="transport_echo_only",
            protocol_semantics="not_implemented",
            note=(
                "Received an exact echo of the transmitted HEARTBEAT frame. "
                "That is not a firmware-backed HEARTBEAT_ACK."
            ),
        )
    if rx_parsed.get("is_protocol_frame") and rx_parsed.get("msg_type") == int(MessageType.HEARTBEAT_ACK):
        heartbeat_ack = rx_parsed.get("heartbeat_ack", {})
        if heartbeat_ack.get("parsed"):
            heartbeat_ok = int(heartbeat_ack["heartbeat_ok"])
            if heartbeat_ok == 1:
                return build_heartbeat_transport_summary(
                    phase=phase,
                    tx_parsed=tx_parsed,
                    rx_parsed=rx_parsed,
                    acknowledged=True,
                    heartbeat_ok=heartbeat_ok,
                    guard_state=int(heartbeat_ack["guard_state"]),
                    source="firmware_heartbeat_ack",
                    transport_status="heartbeat_ack_received",
                    protocol_semantics="implemented",
                    note="Received a decodable HEARTBEAT_ACK frame from firmware.",
                )
            return build_heartbeat_transport_summary(
                phase=phase,
                tx_parsed=tx_parsed,
                rx_parsed=rx_parsed,
                acknowledged=False,
                heartbeat_ok=heartbeat_ok,
                guard_state=int(heartbeat_ack["guard_state"]),
                source="firmware_heartbeat_ack",
                transport_status="heartbeat_ack_received_negative",
                protocol_semantics="implemented",
                note=(
                    "Received a decodable HEARTBEAT_ACK frame, but firmware did not mark the heartbeat as ok."
                ),
            )
        return build_heartbeat_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            heartbeat_ok=0,
            guard_state=DEFAULT_GUARD_STATE,
            source="linux_bridge_transport_guard",
            transport_status="heartbeat_ack_received_unparsed_payload",
            protocol_semantics="partially_verified",
            note=(
                "Received HEARTBEAT_ACK msg_type but the payload shape does not match the expected 8-byte layout."
            ),
        )
    return build_heartbeat_transport_summary(
        phase=phase,
        tx_parsed=tx_parsed,
        rx_parsed=rx_parsed,
        acknowledged=False,
        heartbeat_ok=0,
        guard_state=DEFAULT_GUARD_STATE,
        source="linux_bridge_transport_guard",
        transport_status="unexpected_response",
        protocol_semantics="not_verified",
        note=(
            "A response arrived after HEARTBEAT, but it is not a decodable HEARTBEAT_ACK frame. "
            "Treat heartbeat semantics as unresolved."
        ),
    )


def build_job_done_transport_summary(
    *,
    phase: str,
    tx_parsed: dict[str, Any],
    rx_parsed: dict[str, Any] | None,
    acknowledged: bool,
    reported_result_code: int,
    reported_output_count: int,
    guard_state: int,
    active_job_id: int,
    last_fault_code: int,
    heartbeat_ok: int,
    sticky_fault: int,
    total_fault_count: int,
    source: str,
    transport_status: str,
    protocol_semantics: str,
    note: str,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "acknowledged": acknowledged,
        "reported_result_code": reported_result_code,
        "reported_output_count": reported_output_count,
        "reported_success": reported_result_code == 0,
        "guard_state": guard_state,
        "guard_state_name": safe_guard_state_name(guard_state),
        "active_job_id": active_job_id,
        "last_fault_code": last_fault_code,
        "last_fault_name": safe_fault_name(last_fault_code),
        "heartbeat_ok": heartbeat_ok,
        "sticky_fault": sticky_fault,
        "total_fault_count": total_fault_count,
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "tx_frame": tx_parsed,
        "rx_frame": rx_parsed,
    }


def classify_job_done_probe(
    *,
    phase: str,
    tx_bytes: bytes,
    rx_bytes: bytes,
    rx_timeout: bool,
) -> dict[str, Any]:
    tx_parsed = parse_frame(tx_bytes)
    job_done = tx_parsed.get("job_done", {})
    reported_result_code = int(job_done.get("result_code", 1))
    reported_output_count = int(job_done.get("output_count", 0))
    if rx_timeout:
        return build_job_done_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=None,
            acknowledged=False,
            reported_result_code=reported_result_code,
            reported_output_count=reported_output_count,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="tx_ok_rx_timeout",
            protocol_semantics="not_verified",
            note=(
                "JOB_DONE was written to /dev/rpmsg0 but no STATUS_RESP result arrived before timeout. "
                "Treat completion semantics as unresolved."
            ),
        )
    rx_parsed = parse_frame(rx_bytes)
    if rx_bytes == tx_bytes:
        return build_job_done_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            reported_result_code=reported_result_code,
            reported_output_count=reported_output_count,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="transport_echo_only",
            protocol_semantics="not_implemented",
            note=(
                "Received an exact echo of the transmitted JOB_DONE frame. "
                "That is not a firmware-backed completion result."
            ),
        )
    if rx_parsed.get("is_protocol_frame") and rx_parsed.get("msg_type") == int(MessageType.STATUS_RESP):
        status_resp = rx_parsed.get("status_resp", {})
        if status_resp.get("parsed"):
            guard_state = int(status_resp["guard_state"])
            active_job_id = int(status_resp["active_job_id"])
            last_fault_code = int(status_resp["last_fault_code"])
            heartbeat_ok = int(status_resp["heartbeat_ok"])
            sticky_fault = int(status_resp["sticky_fault"])
            total_fault_count = int(status_resp["total_fault_count"])
            cleared_job = guard_state == 1 and active_job_id == 0 and heartbeat_ok == 0
            if reported_result_code == 0:
                acknowledged = cleared_job and last_fault_code == int(FaultCode.NONE)
                note = (
                    "Received STATUS_RESP after JOB_DONE and firmware reported the active job as cleared."
                    if acknowledged
                    else (
                        "Received STATUS_RESP after JOB_DONE, but firmware did not report the expected "
                        "READY/active_job_id=0/last_fault_code=NONE post-done state."
                    )
                )
            else:
                acknowledged = cleared_job and last_fault_code == int(FaultCode.OUTPUT_INCOMPLETE)
                note = (
                    "Received STATUS_RESP after failed JOB_DONE and firmware cleared the active job with OUTPUT_INCOMPLETE."
                    if acknowledged
                    else (
                        "Received STATUS_RESP after failed JOB_DONE, but firmware did not report the expected "
                        "READY/active_job_id=0/last_fault_code=OUTPUT_INCOMPLETE post-done state."
                    )
                )
            return build_job_done_transport_summary(
                phase=phase,
                tx_parsed=tx_parsed,
                rx_parsed=rx_parsed,
                acknowledged=acknowledged,
                reported_result_code=reported_result_code,
                reported_output_count=reported_output_count,
                guard_state=guard_state,
                active_job_id=active_job_id,
                last_fault_code=last_fault_code,
                heartbeat_ok=heartbeat_ok,
                sticky_fault=sticky_fault,
                total_fault_count=total_fault_count,
                source="firmware_job_done_status",
                transport_status=(
                    "job_done_status_received"
                    if acknowledged
                    else "job_done_status_received_not_applied"
                ),
                protocol_semantics="implemented",
                note=note,
            )
        return build_job_done_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            reported_result_code=reported_result_code,
            reported_output_count=reported_output_count,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="job_done_status_received_unparsed_payload",
            protocol_semantics="partially_verified",
            note=(
                "Received STATUS_RESP after JOB_DONE, but the payload shape does not match the expected "
                "24-byte layout."
            ),
        )
    return build_job_done_transport_summary(
        phase=phase,
        tx_parsed=tx_parsed,
        rx_parsed=rx_parsed,
        acknowledged=False,
        reported_result_code=reported_result_code,
        reported_output_count=reported_output_count,
        guard_state=DEFAULT_GUARD_STATE,
        active_job_id=0,
        last_fault_code=int(FaultCode.NONE),
        heartbeat_ok=0,
        sticky_fault=0,
        total_fault_count=0,
        source="linux_bridge_transport_guard",
        transport_status="unexpected_response",
        protocol_semantics="not_verified",
        note=(
            "A response arrived after JOB_DONE, but it is not a decodable STATUS_RESP frame. "
            "Treat completion semantics as unresolved."
        ),
    )


def build_safe_stop_transport_summary(
    *,
    phase: str,
    tx_parsed: dict[str, Any],
    rx_parsed: dict[str, Any] | None,
    acknowledged: bool,
    guard_state: int,
    active_job_id: int,
    last_fault_code: int,
    heartbeat_ok: int,
    sticky_fault: int,
    total_fault_count: int,
    source: str,
    transport_status: str,
    protocol_semantics: str,
    note: str,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "acknowledged": acknowledged,
        "guard_state": guard_state,
        "guard_state_name": safe_guard_state_name(guard_state),
        "active_job_id": active_job_id,
        "last_fault_code": last_fault_code,
        "last_fault_name": safe_fault_name(last_fault_code),
        "heartbeat_ok": heartbeat_ok,
        "sticky_fault": sticky_fault,
        "total_fault_count": total_fault_count,
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "tx_frame": tx_parsed,
        "rx_frame": rx_parsed,
    }


def classify_safe_stop_probe(
    *,
    phase: str,
    tx_bytes: bytes,
    rx_bytes: bytes,
    rx_timeout: bool,
) -> dict[str, Any]:
    tx_parsed = parse_frame(tx_bytes)
    if rx_timeout:
        return build_safe_stop_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=None,
            acknowledged=False,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="tx_ok_rx_timeout",
            protocol_semantics="not_verified",
            note=(
                "SAFE_STOP was written to /dev/rpmsg0 but no STATUS_RESP result arrived before timeout. "
                "Treat stop semantics as unresolved."
            ),
        )
    rx_parsed = parse_frame(rx_bytes)
    if rx_bytes == tx_bytes:
        return build_safe_stop_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="transport_echo_only",
            protocol_semantics="not_implemented",
            note=(
                "Received an exact echo of the transmitted SAFE_STOP frame. "
                "That is not a firmware-backed stop result."
            ),
        )
    if rx_parsed.get("is_protocol_frame") and rx_parsed.get("msg_type") == int(MessageType.STATUS_RESP):
        status_resp = rx_parsed.get("status_resp", {})
        if status_resp.get("parsed"):
            guard_state = int(status_resp["guard_state"])
            active_job_id = int(status_resp["active_job_id"])
            last_fault_code = int(status_resp["last_fault_code"])
            heartbeat_ok = int(status_resp["heartbeat_ok"])
            sticky_fault = int(status_resp["sticky_fault"])
            total_fault_count = int(status_resp["total_fault_count"])
            acknowledged = (
                guard_state == 1
                and active_job_id == 0
                and heartbeat_ok == 0
                and last_fault_code == int(FaultCode.MANUAL_SAFE_STOP)
            )
            return build_safe_stop_transport_summary(
                phase=phase,
                tx_parsed=tx_parsed,
                rx_parsed=rx_parsed,
                acknowledged=acknowledged,
                guard_state=guard_state,
                active_job_id=active_job_id,
                last_fault_code=last_fault_code,
                heartbeat_ok=heartbeat_ok,
                sticky_fault=sticky_fault,
                total_fault_count=total_fault_count,
                source="firmware_safe_stop_status",
                transport_status=(
                    "safe_stop_status_received"
                    if acknowledged
                    else "safe_stop_status_received_not_applied"
                ),
                protocol_semantics="implemented",
                note=(
                    "Received STATUS_RESP after SAFE_STOP and firmware reported the active job as cleared."
                    if acknowledged
                    else (
                        "Received STATUS_RESP after SAFE_STOP, but firmware did not report the expected "
                        "READY/active_job_id=0/manual-safe-stop state."
                    )
                ),
            )
        return build_safe_stop_transport_summary(
            phase=phase,
            tx_parsed=tx_parsed,
            rx_parsed=rx_parsed,
            acknowledged=False,
            guard_state=DEFAULT_GUARD_STATE,
            active_job_id=0,
            last_fault_code=int(FaultCode.NONE),
            heartbeat_ok=0,
            sticky_fault=0,
            total_fault_count=0,
            source="linux_bridge_transport_guard",
            transport_status="safe_stop_status_received_unparsed_payload",
            protocol_semantics="partially_verified",
            note=(
                "Received STATUS_RESP after SAFE_STOP, but the payload shape does not match the expected "
                "24-byte layout."
            ),
        )
    return build_safe_stop_transport_summary(
        phase=phase,
        tx_parsed=tx_parsed,
        rx_parsed=rx_parsed,
        acknowledged=False,
        guard_state=DEFAULT_GUARD_STATE,
        active_job_id=0,
        last_fault_code=int(FaultCode.NONE),
        heartbeat_ok=0,
        sticky_fault=0,
        total_fault_count=0,
        source="linux_bridge_transport_guard",
        transport_status="unexpected_response",
        protocol_semantics="not_verified",
        note=(
            "A response arrived after SAFE_STOP, but it is not a decodable STATUS_RESP frame. "
            "Treat stop semantics as unresolved."
        ),
    )


def persist_status_exchange_artifacts(
    *,
    output_dir: Path,
    hook_event: dict[str, Any],
    tx_bytes: bytes,
    rx_bytes: bytes,
    summary: dict[str, Any],
    txn: dict[str, Any],
) -> dict[str, str]:
    artifacts = {
        "stdin_event": output_dir / "stdin_event.json",
        "tx_raw": output_dir / "status_req_tx.bin",
        "tx_hex": output_dir / "status_req_tx.hex",
        "tx_json": output_dir / "status_req_tx.json",
        "rx_raw": output_dir / "status_resp_or_echo_rx.bin",
        "rx_hex": output_dir / "status_resp_or_echo_rx.hex",
        "rx_json": output_dir / "status_resp_or_echo_rx.json",
        "summary": output_dir / "bridge_summary.json",
    }
    write_json(artifacts["stdin_event"], hook_event or {})
    write_raw(artifacts["tx_raw"], tx_bytes)
    write_hex(artifacts["tx_hex"], tx_bytes)
    write_json(
        artifacts["tx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(tx_bytes),
            "hex": tx_bytes.hex(),
            "parsed_frame": summary["tx_frame"],
        },
    )
    write_raw(artifacts["rx_raw"], rx_bytes)
    write_hex(artifacts["rx_hex"], rx_bytes)
    write_json(
        artifacts["rx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(rx_bytes),
            "hex": rx_bytes.hex(),
            "rx_timeout": txn["rx_timeout"],
            "parsed_frame": summary["rx_frame"],
        },
    )
    return {name: str(path) for name, path in artifacts.items()}


def persist_job_exchange_artifacts(
    *,
    output_dir: Path,
    hook_event: dict[str, Any],
    tx_bytes: bytes,
    rx_bytes: bytes,
    summary: dict[str, Any],
    txn: dict[str, Any],
) -> dict[str, str]:
    artifacts = {
        "stdin_event": output_dir / "stdin_event.json",
        "tx_raw": output_dir / "job_req_tx.bin",
        "tx_hex": output_dir / "job_req_tx.hex",
        "tx_json": output_dir / "job_req_tx.json",
        "rx_raw": output_dir / "job_ack_rx.bin",
        "rx_hex": output_dir / "job_ack_rx.hex",
        "rx_json": output_dir / "job_ack_rx.json",
        "summary": output_dir / "bridge_summary.json",
    }
    write_json(artifacts["stdin_event"], hook_event or {})
    write_raw(artifacts["tx_raw"], tx_bytes)
    write_hex(artifacts["tx_hex"], tx_bytes)
    write_json(
        artifacts["tx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(tx_bytes),
            "hex": tx_bytes.hex(),
            "parsed_frame": summary["tx_frame"],
        },
    )
    write_raw(artifacts["rx_raw"], rx_bytes)
    write_hex(artifacts["rx_hex"], rx_bytes)
    write_json(
        artifacts["rx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(rx_bytes),
            "hex": rx_bytes.hex(),
            "rx_timeout": txn["rx_timeout"],
            "parsed_frame": summary["rx_frame"],
        },
    )
    return {name: str(path) for name, path in artifacts.items()}


def persist_heartbeat_exchange_artifacts(
    *,
    output_dir: Path,
    hook_event: dict[str, Any],
    tx_bytes: bytes,
    rx_bytes: bytes,
    summary: dict[str, Any],
    txn: dict[str, Any],
) -> dict[str, str]:
    artifacts = {
        "stdin_event": output_dir / "stdin_event.json",
        "tx_raw": output_dir / "heartbeat_tx.bin",
        "tx_hex": output_dir / "heartbeat_tx.hex",
        "tx_json": output_dir / "heartbeat_tx.json",
        "rx_raw": output_dir / "heartbeat_ack_rx.bin",
        "rx_hex": output_dir / "heartbeat_ack_rx.hex",
        "rx_json": output_dir / "heartbeat_ack_rx.json",
        "summary": output_dir / "bridge_summary.json",
    }
    write_json(artifacts["stdin_event"], hook_event or {})
    write_raw(artifacts["tx_raw"], tx_bytes)
    write_hex(artifacts["tx_hex"], tx_bytes)
    write_json(
        artifacts["tx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(tx_bytes),
            "hex": tx_bytes.hex(),
            "parsed_frame": summary["tx_frame"],
        },
    )
    write_raw(artifacts["rx_raw"], rx_bytes)
    write_hex(artifacts["rx_hex"], rx_bytes)
    write_json(
        artifacts["rx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(rx_bytes),
            "hex": rx_bytes.hex(),
            "rx_timeout": txn["rx_timeout"],
            "parsed_frame": summary["rx_frame"],
        },
    )
    return {name: str(path) for name, path in artifacts.items()}


def persist_job_done_exchange_artifacts(
    *,
    output_dir: Path,
    hook_event: dict[str, Any],
    tx_bytes: bytes,
    rx_bytes: bytes,
    summary: dict[str, Any],
    txn: dict[str, Any],
) -> dict[str, str]:
    artifacts = {
        "stdin_event": output_dir / "stdin_event.json",
        "tx_raw": output_dir / "job_done_tx.bin",
        "tx_hex": output_dir / "job_done_tx.hex",
        "tx_json": output_dir / "job_done_tx.json",
        "rx_raw": output_dir / "job_done_status_rx.bin",
        "rx_hex": output_dir / "job_done_status_rx.hex",
        "rx_json": output_dir / "job_done_status_rx.json",
        "summary": output_dir / "bridge_summary.json",
    }
    write_json(artifacts["stdin_event"], hook_event or {})
    write_raw(artifacts["tx_raw"], tx_bytes)
    write_hex(artifacts["tx_hex"], tx_bytes)
    write_json(
        artifacts["tx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(tx_bytes),
            "hex": tx_bytes.hex(),
            "parsed_frame": summary["tx_frame"],
        },
    )
    write_raw(artifacts["rx_raw"], rx_bytes)
    write_hex(artifacts["rx_hex"], rx_bytes)
    write_json(
        artifacts["rx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(rx_bytes),
            "hex": rx_bytes.hex(),
            "rx_timeout": txn["rx_timeout"],
            "parsed_frame": summary["rx_frame"],
        },
    )
    return {name: str(path) for name, path in artifacts.items()}


def persist_safe_stop_exchange_artifacts(
    *,
    output_dir: Path,
    hook_event: dict[str, Any],
    tx_bytes: bytes,
    rx_bytes: bytes,
    summary: dict[str, Any],
    txn: dict[str, Any],
) -> dict[str, str]:
    artifacts = {
        "stdin_event": output_dir / "stdin_event.json",
        "tx_raw": output_dir / "safe_stop_tx.bin",
        "tx_hex": output_dir / "safe_stop_tx.hex",
        "tx_json": output_dir / "safe_stop_tx.json",
        "rx_raw": output_dir / "safe_stop_status_rx.bin",
        "rx_hex": output_dir / "safe_stop_status_rx.hex",
        "rx_json": output_dir / "safe_stop_status_rx.json",
        "summary": output_dir / "bridge_summary.json",
    }
    write_json(artifacts["stdin_event"], hook_event or {})
    write_raw(artifacts["tx_raw"], tx_bytes)
    write_hex(artifacts["tx_hex"], tx_bytes)
    write_json(
        artifacts["tx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(tx_bytes),
            "hex": tx_bytes.hex(),
            "parsed_frame": summary["tx_frame"],
        },
    )
    write_raw(artifacts["rx_raw"], rx_bytes)
    write_hex(artifacts["rx_hex"], rx_bytes)
    write_json(
        artifacts["rx_json"],
        {
            "captured_at": now_iso(),
            "byte_len": len(rx_bytes),
            "hex": rx_bytes.hex(),
            "rx_timeout": txn["rx_timeout"],
            "parsed_frame": summary["rx_frame"],
        },
    )
    return {name: str(path) for name, path in artifacts.items()}


def run_status_probe(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    rpmsg_ctrl = Path(args.rpmsg_ctrl)
    rpmsg_dev = Path(args.rpmsg_dev)
    device_status = preflight_devices(
        rpmsg_ctrl=rpmsg_ctrl,
        rpmsg_dev=rpmsg_dev,
        require_devices=args.require_devices,
    )
    if args.require_devices:
        require_existing_device(rpmsg_ctrl, "--rpmsg-ctrl")
        require_existing_device(rpmsg_dev, "--rpmsg-dev")
    job_id = derive_job_id(args, hook_event)
    tx_bytes = build_frame(
        msg_type=MessageType.STATUS_REQ,
        seq=args.seq,
        job_id=job_id,
        payload=b"",
    )
    try:
        txn = transact(
            rpmsg_dev=rpmsg_dev,
            tx_bytes=tx_bytes,
            response_timeout_sec=args.response_timeout_sec,
            settle_timeout_sec=args.settle_timeout_sec,
            max_rx_bytes=args.max_rx_bytes,
            drain_before_send=args.drain_before_send,
        )
    except (OSError, TimeoutError, SystemExit) as err:
        source, transport_status, protocol_semantics, note = describe_transport_failure(
            phase=phase,
            rpmsg_dev=rpmsg_dev,
            err=err,
        )
        return build_status_local_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=note,
            source=source,
            transport_status=transport_status,
            protocol_semantics=protocol_semantics,
            device_status=device_status,
        )
    summary = classify_status_probe(
        phase=phase,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        rx_timeout=txn["rx_timeout"],
    )
    summary.update(
        {
            "generated_at": now_iso(),
            "job_id": job_id,
            "seq": args.seq,
            "rpmsg_ctrl": str(rpmsg_ctrl),
            "rpmsg_dev": str(rpmsg_dev),
            "device_status": device_status,
            "bridge_mode": "hook" if args.hook_stdin else "direct",
            "hook_event_phase": hook_event.get("phase") if isinstance(hook_event, dict) else None,
            "hook_event_payload": hook_event.get("payload") if isinstance(hook_event, dict) else None,
            "written_bytes": txn["written_bytes"],
            "drained_bytes_hex": txn["drained_bytes"].hex(),
            "rx_bytes_hex": txn["rx_bytes"].hex(),
            "output_dir": str(output_dir),
        }
    )
    summary["artifact_paths"] = persist_status_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def decode_sha256_hex(raw: Any) -> bytes:
    text = str(raw or "").strip().lower()
    if not text:
        raise ValueError("expected_sha256 is required for JOB_REQ hook events.")
    try:
        sha_bytes = bytes.fromhex(text)
    except ValueError as err:
        raise ValueError("expected_sha256 must be a 64-character hex string.") from err
    if len(sha_bytes) != 32:
        raise ValueError("expected_sha256 must decode to exactly 32 bytes.")
    return sha_bytes


def coerce_positive_int(raw: Any, label: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{label} must be an integer.") from err
    if value < 0:
        raise ValueError(f"{label} must be >= 0.")
    if value > 0xFFFFFFFF:
        raise ValueError(f"{label} must fit in u32.")
    return value


def map_job_flags(raw: Any) -> int:
    if isinstance(raw, int):
        return raw if raw in FLAG_WIRE_TO_NAME else 0
    text = str(raw or "").strip().lower()
    if text in FLAG_NAME_TO_WIRE:
        return FLAG_NAME_TO_WIRE[text]
    return 0


def map_runtime_state(raw: Any) -> int:
    if isinstance(raw, int):
        return raw if raw in RUNTIME_STATE_WIRE_TO_NAME else 0
    text = str(raw or "").strip().upper()
    if text in RUNTIME_STATE_NAME_TO_WIRE:
        return RUNTIME_STATE_NAME_TO_WIRE[text]
    return 0


def build_job_req_payload_from_hook(hook_event: dict[str, Any]) -> bytes:
    payload = hook_event.get("payload") if isinstance(hook_event, dict) else None
    if not isinstance(payload, dict):
        raise ValueError("hook JOB_REQ event must contain a payload object.")
    expected_sha256 = decode_sha256_hex(payload.get("expected_sha256"))
    deadline_ms = coerce_positive_int(payload.get("deadline_ms"), "deadline_ms")
    expected_outputs = coerce_positive_int(payload.get("expected_outputs"), "expected_outputs")
    flags = map_job_flags(payload.get("job_flags", payload.get("flags")))
    return JOB_REQ_STRUCT.pack(
        expected_sha256,
        deadline_ms,
        expected_outputs,
        flags,
    )


def build_heartbeat_payload_from_hook(hook_event: dict[str, Any]) -> bytes:
    payload = hook_event.get("payload") if isinstance(hook_event, dict) else None
    if not isinstance(payload, dict):
        raise ValueError("hook HEARTBEAT event must contain a payload object.")
    runtime_state = map_runtime_state(payload.get("runtime_state", "RUNNING"))
    elapsed_ms = coerce_positive_int(payload.get("elapsed_ms", 0), "elapsed_ms")
    completed_outputs = coerce_positive_int(payload.get("completed_outputs", 0), "completed_outputs")
    progress_x100 = coerce_positive_int(payload.get("progress_x100", 0), "progress_x100")
    return HEARTBEAT_STRUCT.pack(
        runtime_state,
        elapsed_ms,
        completed_outputs,
        progress_x100,
    )


def build_safe_stop_payload_from_hook(hook_event: dict[str, Any]) -> bytes:
    payload = hook_event.get("payload") if isinstance(hook_event, dict) else None
    if not isinstance(payload, dict):
        raise ValueError("hook SAFE_STOP event must contain a payload object.")
    return b""


def build_job_done_payload_from_hook(hook_event: dict[str, Any]) -> bytes:
    payload = hook_event.get("payload") if isinstance(hook_event, dict) else None
    if not isinstance(payload, dict):
        raise ValueError("hook JOB_DONE event must contain a payload object.")
    result_code = coerce_positive_int(payload.get("result_code", 1), "result_code")
    output_count = coerce_positive_int(
        payload.get("output_count", payload.get("completed_outputs", 0)),
        "output_count",
    )
    result_crc32 = coerce_positive_int(payload.get("result_crc32", 0), "result_crc32")
    reserved = coerce_positive_int(payload.get("reserved", 0), "reserved")
    return JOB_DONE_STRUCT.pack(
        result_code,
        output_count,
        result_crc32,
        reserved,
    )


def build_local_deny_summary(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
    note: str,
    fault_code: int = INPUT_RANGE_FAULT_CODE,
    guard_state: int = DEFAULT_GUARD_STATE,
    source: str = "linux_bridge_local_guard",
    transport_status: str = "not_attempted",
    protocol_semantics: str = "not_available",
    device_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "generated_at": now_iso(),
        "bridge_mode": "hook" if args.hook_stdin else "direct",
        "phase": phase,
        "decision": "DENY",
        "fault_code": fault_code,
        "fault_name": safe_fault_name(fault_code),
        "guard_state": guard_state,
        "guard_state_name": safe_guard_state_name(guard_state),
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "job_id": derive_job_id(args, hook_event),
        "rpmsg_ctrl": args.rpmsg_ctrl,
        "rpmsg_dev": args.rpmsg_dev,
        "output_dir": str(output_dir),
        "hook_event": hook_event or {},
    }
    if device_status is not None:
        summary["device_status"] = device_status
    write_json(output_dir / "bridge_summary.json", summary)
    if hook_event:
        write_json(output_dir / "stdin_event.json", hook_event)
    return summary


def build_status_local_summary(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
    note: str,
    source: str = "linux_bridge_local_guard",
    transport_status: str = "not_attempted",
    protocol_semantics: str = "not_available",
    device_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "generated_at": now_iso(),
        "bridge_mode": "hook" if args.hook_stdin else "direct",
        "phase": phase,
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "job_id": derive_job_id(args, hook_event),
        "rpmsg_ctrl": args.rpmsg_ctrl,
        "rpmsg_dev": args.rpmsg_dev,
        "output_dir": str(output_dir),
        "hook_event": hook_event or {},
    }
    if device_status is not None:
        summary["device_status"] = device_status
    write_json(output_dir / "bridge_summary.json", summary)
    if hook_event:
        write_json(output_dir / "stdin_event.json", hook_event)
    return summary


def build_job_done_local_summary(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
    note: str,
    source: str = "linux_bridge_local_guard",
    transport_status: str = "not_attempted",
    protocol_semantics: str = "not_available",
    device_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "generated_at": now_iso(),
        "bridge_mode": "hook" if args.hook_stdin else "direct",
        "phase": phase,
        "acknowledged": False,
        "reported_result_code": 1,
        "reported_output_count": 0,
        "reported_success": False,
        "last_fault_code": int(FaultCode.NONE),
        "last_fault_name": safe_fault_name(int(FaultCode.NONE)),
        "guard_state": DEFAULT_GUARD_STATE,
        "guard_state_name": safe_guard_state_name(DEFAULT_GUARD_STATE),
        "active_job_id": 0,
        "heartbeat_ok": 0,
        "sticky_fault": 0,
        "total_fault_count": 0,
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "job_id": derive_job_id(args, hook_event),
        "rpmsg_ctrl": args.rpmsg_ctrl,
        "rpmsg_dev": args.rpmsg_dev,
        "output_dir": str(output_dir),
        "hook_event": hook_event or {},
    }
    if device_status is not None:
        summary["device_status"] = device_status
    write_json(output_dir / "bridge_summary.json", summary)
    if hook_event:
        write_json(output_dir / "stdin_event.json", hook_event)
    return summary


def build_safe_stop_local_summary(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
    note: str,
    source: str = "linux_bridge_local_guard",
    transport_status: str = "not_attempted",
    protocol_semantics: str = "not_available",
    device_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "generated_at": now_iso(),
        "bridge_mode": "hook" if args.hook_stdin else "direct",
        "phase": phase,
        "acknowledged": False,
        "last_fault_code": int(FaultCode.NONE),
        "last_fault_name": safe_fault_name(int(FaultCode.NONE)),
        "guard_state": DEFAULT_GUARD_STATE,
        "guard_state_name": safe_guard_state_name(DEFAULT_GUARD_STATE),
        "active_job_id": 0,
        "heartbeat_ok": 0,
        "sticky_fault": 0,
        "total_fault_count": 0,
        "source": source,
        "transport_status": transport_status,
        "protocol_semantics": protocol_semantics,
        "note": note,
        "job_id": derive_job_id(args, hook_event),
        "rpmsg_ctrl": args.rpmsg_ctrl,
        "rpmsg_dev": args.rpmsg_dev,
        "output_dir": str(output_dir),
        "hook_event": hook_event or {},
    }
    if device_status is not None:
        summary["device_status"] = device_status
    write_json(output_dir / "bridge_summary.json", summary)
    if hook_event:
        write_json(output_dir / "stdin_event.json", hook_event)
    return summary


def run_job_probe(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    rpmsg_ctrl = Path(args.rpmsg_ctrl)
    rpmsg_dev = Path(args.rpmsg_dev)
    device_status = preflight_devices(
        rpmsg_ctrl=rpmsg_ctrl,
        rpmsg_dev=rpmsg_dev,
        require_devices=args.require_devices,
    )
    try:
        if args.require_devices:
            require_existing_device(rpmsg_ctrl, "--rpmsg-ctrl")
            require_existing_device(rpmsg_dev, "--rpmsg-dev")
        job_payload = build_job_req_payload_from_hook(hook_event)
    except ValueError as err:
        return build_local_deny_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=f"JOB_REQ hook payload is not encodable as the minimal binary payload: {err}",
        )
    job_id = derive_job_id(args, hook_event)
    tx_bytes = build_frame(
        msg_type=MessageType.JOB_REQ,
        seq=args.seq,
        job_id=job_id,
        payload=job_payload,
    )
    try:
        txn = transact(
            rpmsg_dev=rpmsg_dev,
            tx_bytes=tx_bytes,
            response_timeout_sec=args.response_timeout_sec,
            settle_timeout_sec=args.settle_timeout_sec,
            max_rx_bytes=args.max_rx_bytes,
            drain_before_send=args.drain_before_send,
        )
    except (OSError, TimeoutError, SystemExit) as err:
        source, transport_status, protocol_semantics, note = describe_transport_failure(
            phase=phase,
            rpmsg_dev=rpmsg_dev,
            err=err,
        )
        return build_local_deny_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=note,
            fault_code=CONTROL_PATH_FAULT_CODE,
            source=source,
            transport_status=transport_status,
            protocol_semantics=protocol_semantics,
            device_status=device_status,
        )
    summary = classify_job_probe(
        phase=phase,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        rx_timeout=txn["rx_timeout"],
    )
    summary.update(
        {
            "generated_at": now_iso(),
            "job_id": job_id,
            "seq": args.seq,
            "rpmsg_ctrl": str(rpmsg_ctrl),
            "rpmsg_dev": str(rpmsg_dev),
            "device_status": device_status,
            "bridge_mode": "hook",
            "hook_event_phase": hook_event.get("phase") if isinstance(hook_event, dict) else None,
            "hook_event_payload": hook_event.get("payload") if isinstance(hook_event, dict) else None,
            "written_bytes": txn["written_bytes"],
            "drained_bytes_hex": txn["drained_bytes"].hex(),
            "rx_bytes_hex": txn["rx_bytes"].hex(),
            "output_dir": str(output_dir),
        }
    )
    summary["artifact_paths"] = persist_job_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def run_heartbeat_probe(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    rpmsg_ctrl = Path(args.rpmsg_ctrl)
    rpmsg_dev = Path(args.rpmsg_dev)
    device_status = preflight_devices(
        rpmsg_ctrl=rpmsg_ctrl,
        rpmsg_dev=rpmsg_dev,
        require_devices=args.require_devices,
    )
    try:
        if args.require_devices:
            require_existing_device(rpmsg_ctrl, "--rpmsg-ctrl")
            require_existing_device(rpmsg_dev, "--rpmsg-dev")
        heartbeat_payload = build_heartbeat_payload_from_hook(hook_event)
    except ValueError as err:
        return build_local_deny_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=f"HEARTBEAT hook payload is not encodable as the minimal binary payload: {err}",
        )
    job_id = derive_job_id(args, hook_event)
    tx_bytes = build_frame(
        msg_type=MessageType.HEARTBEAT,
        seq=args.seq,
        job_id=job_id,
        payload=heartbeat_payload,
    )
    try:
        txn = transact(
            rpmsg_dev=rpmsg_dev,
            tx_bytes=tx_bytes,
            response_timeout_sec=args.response_timeout_sec,
            settle_timeout_sec=args.settle_timeout_sec,
            max_rx_bytes=args.max_rx_bytes,
            drain_before_send=args.drain_before_send,
        )
    except (OSError, TimeoutError, SystemExit) as err:
        source, transport_status, protocol_semantics, note = describe_transport_failure(
            phase=phase,
            rpmsg_dev=rpmsg_dev,
            err=err,
        )
        return build_local_deny_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=note,
            fault_code=CONTROL_PATH_FAULT_CODE,
            source=source,
            transport_status=transport_status,
            protocol_semantics=protocol_semantics,
            device_status=device_status,
        )
    summary = classify_heartbeat_probe(
        phase=phase,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        rx_timeout=txn["rx_timeout"],
    )
    summary.update(
        {
            "generated_at": now_iso(),
            "job_id": job_id,
            "seq": args.seq,
            "rpmsg_ctrl": str(rpmsg_ctrl),
            "rpmsg_dev": str(rpmsg_dev),
            "device_status": device_status,
            "bridge_mode": "hook",
            "hook_event_phase": hook_event.get("phase") if isinstance(hook_event, dict) else None,
            "hook_event_payload": hook_event.get("payload") if isinstance(hook_event, dict) else None,
            "written_bytes": txn["written_bytes"],
            "drained_bytes_hex": txn["drained_bytes"].hex(),
            "rx_bytes_hex": txn["rx_bytes"].hex(),
            "output_dir": str(output_dir),
        }
    )
    summary["artifact_paths"] = persist_heartbeat_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def run_job_done_probe(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    rpmsg_ctrl = Path(args.rpmsg_ctrl)
    rpmsg_dev = Path(args.rpmsg_dev)
    device_status = preflight_devices(
        rpmsg_ctrl=rpmsg_ctrl,
        rpmsg_dev=rpmsg_dev,
        require_devices=args.require_devices,
    )
    try:
        if args.require_devices:
            require_existing_device(rpmsg_ctrl, "--rpmsg-ctrl")
            require_existing_device(rpmsg_dev, "--rpmsg-dev")
        job_done_payload = build_job_done_payload_from_hook(hook_event)
    except ValueError as err:
        return build_job_done_local_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=f"JOB_DONE hook payload is not encodable as the minimal binary payload: {err}",
        )
    job_id = derive_job_id(args, hook_event)
    tx_bytes = build_frame(
        msg_type=MessageType.JOB_DONE,
        seq=args.seq,
        job_id=job_id,
        payload=job_done_payload,
    )
    try:
        txn = transact(
            rpmsg_dev=rpmsg_dev,
            tx_bytes=tx_bytes,
            response_timeout_sec=args.response_timeout_sec,
            settle_timeout_sec=args.settle_timeout_sec,
            max_rx_bytes=args.max_rx_bytes,
            drain_before_send=args.drain_before_send,
        )
    except (OSError, TimeoutError, SystemExit) as err:
        source, transport_status, protocol_semantics, note = describe_transport_failure(
            phase=phase,
            rpmsg_dev=rpmsg_dev,
            err=err,
        )
        return build_job_done_local_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=note,
            source=source,
            transport_status=transport_status,
            protocol_semantics=protocol_semantics,
            device_status=device_status,
        )
    summary = classify_job_done_probe(
        phase=phase,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        rx_timeout=txn["rx_timeout"],
    )
    summary.update(
        {
            "generated_at": now_iso(),
            "job_id": job_id,
            "seq": args.seq,
            "rpmsg_ctrl": str(rpmsg_ctrl),
            "rpmsg_dev": str(rpmsg_dev),
            "device_status": device_status,
            "bridge_mode": "hook",
            "hook_event_phase": hook_event.get("phase") if isinstance(hook_event, dict) else None,
            "hook_event_payload": hook_event.get("payload") if isinstance(hook_event, dict) else None,
            "written_bytes": txn["written_bytes"],
            "drained_bytes_hex": txn["drained_bytes"].hex(),
            "rx_bytes_hex": txn["rx_bytes"].hex(),
            "output_dir": str(output_dir),
        }
    )
    summary["artifact_paths"] = persist_job_done_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def run_safe_stop_probe(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    rpmsg_ctrl = Path(args.rpmsg_ctrl)
    rpmsg_dev = Path(args.rpmsg_dev)
    device_status = preflight_devices(
        rpmsg_ctrl=rpmsg_ctrl,
        rpmsg_dev=rpmsg_dev,
        require_devices=args.require_devices,
    )
    try:
        if args.require_devices:
            require_existing_device(rpmsg_ctrl, "--rpmsg-ctrl")
            require_existing_device(rpmsg_dev, "--rpmsg-dev")
        safe_stop_payload = build_safe_stop_payload_from_hook(hook_event)
    except ValueError as err:
        return build_safe_stop_local_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=f"SAFE_STOP hook payload is not encodable as the minimal binary payload: {err}",
        )
    job_id = derive_job_id(args, hook_event)
    tx_bytes = build_frame(
        msg_type=MessageType.SAFE_STOP,
        seq=args.seq,
        job_id=job_id,
        payload=safe_stop_payload,
    )
    try:
        txn = transact(
            rpmsg_dev=rpmsg_dev,
            tx_bytes=tx_bytes,
            response_timeout_sec=args.response_timeout_sec,
            settle_timeout_sec=args.settle_timeout_sec,
            max_rx_bytes=args.max_rx_bytes,
            drain_before_send=args.drain_before_send,
        )
    except (OSError, TimeoutError, SystemExit) as err:
        source, transport_status, protocol_semantics, note = describe_transport_failure(
            phase=phase,
            rpmsg_dev=rpmsg_dev,
            err=err,
        )
        return build_safe_stop_local_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
            note=note,
            source=source,
            transport_status=transport_status,
            protocol_semantics=protocol_semantics,
            device_status=device_status,
        )
    summary = classify_safe_stop_probe(
        phase=phase,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        rx_timeout=txn["rx_timeout"],
    )
    summary.update(
        {
            "generated_at": now_iso(),
            "job_id": job_id,
            "seq": args.seq,
            "rpmsg_ctrl": str(rpmsg_ctrl),
            "rpmsg_dev": str(rpmsg_dev),
            "device_status": device_status,
            "bridge_mode": "hook",
            "hook_event_phase": hook_event.get("phase") if isinstance(hook_event, dict) else None,
            "hook_event_payload": hook_event.get("payload") if isinstance(hook_event, dict) else None,
            "written_bytes": txn["written_bytes"],
            "drained_bytes_hex": txn["drained_bytes"].hex(),
            "rx_bytes_hex": txn["rx_bytes"].hex(),
            "output_dir": str(output_dir),
        }
    )
    summary["artifact_paths"] = persist_safe_stop_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    if args.response_timeout_sec <= 0:
        raise SystemExit("ERROR: --response-timeout-sec must be > 0.")
    if args.settle_timeout_sec < 0:
        raise SystemExit("ERROR: --settle-timeout-sec must be >= 0.")
    if args.max_rx_bytes <= 0:
        raise SystemExit("ERROR: --max-rx-bytes must be > 0.")

    output_dir = resolve_output_dir(args.output_dir)
    hook_event = read_hook_event() if args.hook_stdin else {}
    phase = determine_phase(args, hook_event)

    if phase == "STATUS_REQ":
        summary = run_status_probe(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    if phase == "JOB_REQ" and args.hook_stdin:
        summary = run_job_probe(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary.get("decision") == "ALLOW" else 2

    if phase == "HEARTBEAT" and args.hook_stdin:
        summary = run_heartbeat_probe(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary.get("acknowledged") else 2

    if phase == "JOB_DONE" and args.hook_stdin:
        summary = run_job_done_probe(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary.get("acknowledged") else 2

    if phase == "SAFE_STOP" and args.hook_stdin:
        summary = run_safe_stop_probe(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary.get("acknowledged") else 2

    summary = build_local_deny_summary(
        args=args,
        output_dir=output_dir,
        phase=phase,
        hook_event=hook_event,
        note=(
            "This bridge phase only forwards STATUS_REQ in direct mode and STATUS_REQ/JOB_REQ/HEARTBEAT/"
            "JOB_DONE/SAFE_STOP in hook mode. Later phases remain locally denied until firmware support is implemented."
        ),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
