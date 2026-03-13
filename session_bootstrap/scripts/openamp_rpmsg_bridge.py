#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from openamp_mock.protocol import MAGIC, MessageType, VERSION  # noqa: E402


HEADER_STRUCT = struct.Struct("<IHHIIII")
STATUS_RESP_STRUCT = struct.Struct("<IIIIII")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Minimal Linux-side OpenAMP/RPMsg bridge for STATUS_REQ probing. "
            "This script only proves the Linux transport path and never fabricates STATUS_RESP."
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
        help="Direct mode phase. Only STATUS_REQ is forwarded in this phase.",
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
            "Unsupported phases are denied locally without pretending to be firmware responses."
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
            "active_job_id": active_job_id,
            "last_fault_code": last_fault_code,
            "heartbeat_ok": heartbeat_ok,
            "sticky_fault": sticky_fault,
            "total_fault_count": total_fault_count,
        }
    )
    return result


def safe_msg_name(value: int) -> str:
    try:
        return MessageType(value).name
    except ValueError:
        return f"UNKNOWN_{value:#x}"


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


def write_all(fd: int, payload: bytes, timeout_sec: float) -> int:
    end_time = time.monotonic() + timeout_sec
    written = 0
    view = memoryview(payload)
    while written < len(payload):
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("write timeout")
        _, writable, _ = select.select([], [fd], [], remaining)
        if not writable:
            raise TimeoutError("write timeout")
        chunk = os.write(fd, view[written:])
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
                "Received bytes exactly match the transmitted STATUS_REQ candidate frame. "
                "This is consistent with the current demo echo firmware, not with a real STATUS_RESP handler."
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
            "note": "Received STATUS_RESP msg_type but payload shape does not yet match the expected 24-byte layout.",
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


def persist_exchange_artifacts(
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
    txn = transact(
        rpmsg_dev=rpmsg_dev,
        tx_bytes=tx_bytes,
        response_timeout_sec=args.response_timeout_sec,
        settle_timeout_sec=args.settle_timeout_sec,
        max_rx_bytes=args.max_rx_bytes,
        drain_before_send=args.drain_before_send,
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
            "blocker": (
                "Current Linux bridge is ready, but real STATUS_REQ/RESP semantics still depend on "
                "remote firmware replacing the demo echo service with a protocol handler."
            ),
        }
    )
    summary["artifact_paths"] = persist_exchange_artifacts(
        output_dir=output_dir,
        hook_event=hook_event,
        tx_bytes=tx_bytes,
        rx_bytes=txn["rx_bytes"],
        summary=summary,
        txn=txn,
    )
    write_json(output_dir / "bridge_summary.json", summary)
    return summary


def build_local_deny_summary(
    *,
    args: argparse.Namespace,
    output_dir: Path,
    phase: str,
    hook_event: dict[str, Any],
) -> dict[str, Any]:
    summary = {
        "generated_at": now_iso(),
        "bridge_mode": "hook" if args.hook_stdin else "direct",
        "phase": phase,
        "decision": "DENY",
        "source": "linux_bridge_local_guard",
        "transport_status": "not_attempted",
        "protocol_semantics": "not_available",
        "note": (
            "This bridge skeleton only forwards STATUS_REQ in the current phase. "
            "Unsupported wrapper phases are denied locally so the wrapper does not pretend to have a real firmware-backed policy path."
        ),
        "job_id": derive_job_id(args, hook_event),
        "rpmsg_ctrl": args.rpmsg_ctrl,
        "rpmsg_dev": args.rpmsg_dev,
        "output_dir": str(output_dir),
        "hook_event": hook_event or {},
    }
    write_json(output_dir / "bridge_summary.json", summary)
    if hook_event:
        write_json(output_dir / "stdin_event.json", hook_event)
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

    if phase != "STATUS_REQ":
        summary = build_local_deny_summary(
            args=args,
            output_dir=output_dir,
            phase=phase,
            hook_event=hook_event,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 2

    summary = run_status_probe(
        args=args,
        output_dir=output_dir,
        phase=phase,
        hook_event=hook_event,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
