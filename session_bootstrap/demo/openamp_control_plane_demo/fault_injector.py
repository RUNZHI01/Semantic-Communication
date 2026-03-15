from __future__ import annotations

import json
from pathlib import Path
import subprocess
import textwrap
import time
from typing import Any

from board_access import BoardAccessConfig
from remote_failure import build_diagnostics, build_operator_message, classify_status_category


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SSH_HELPER = PROJECT_ROOT / "session_bootstrap" / "scripts" / "ssh_with_password.sh"

FAULT_TYPE_TO_ACTION = {
    "wrong_sha": "wrong_sha",
    "illegal_param": "illegal_param",
    "heartbeat_timeout": "heartbeat_timeout",
    "recover": "recover",
    "status": "status",
}

REMOTE_DRIVER_TEMPLATE = textwrap.dedent(
    r"""
    import json
    import os
    import select
    import struct
    import time
    import zlib

    CONFIG = json.loads(__CONFIG_JSON__)

    MAGIC = 0x53434F4D
    VERSION = 1
    JOB_REQ = 0x01
    JOB_ACK = 0x02
    HEARTBEAT = 0x03
    HEARTBEAT_ACK = 0x04
    SAFE_STOP = 0x07
    STATUS_REQ = 0x08
    STATUS_RESP = 0x09

    HEADER_STRUCT = struct.Struct("<IHHIIII")
    STATUS_RESP_STRUCT = struct.Struct("<IIIIII")
    JOB_REQ_STRUCT = struct.Struct("<32sIII")
    JOB_ACK_STRUCT = struct.Struct("<III")
    HEARTBEAT_STRUCT = struct.Struct("<IIII")
    HEARTBEAT_ACK_STRUCT = struct.Struct("<II")

    GUARD_STATE_NAMES = {
        0: "BOOT",
        1: "READY",
        2: "JOB_ACTIVE",
        3: "WAIT_DONE",
        4: "DENY_PENDING",
        5: "FAULT_LATCHED",
    }
    FAULT_CODE_NAMES = {
        0: "NONE",
        1: "ARTIFACT_SHA_MISMATCH",
        3: "HEARTBEAT_TIMEOUT",
        9: "ILLEGAL_PARAM_RANGE",
        10: "MANUAL_SAFE_STOP",
    }
    DECISION_NAMES = {
        0: "DENY",
        1: "ALLOW",
    }

    def now_label():
        return time.strftime("%H:%M:%S")

    def log(lines, text):
        lines.append(f"[{now_label()}] {text}")

    def safe_guard_name(value):
        return GUARD_STATE_NAMES.get(value, f"UNKNOWN_{value}")

    def safe_fault_name(value):
        return FAULT_CODE_NAMES.get(value, f"UNKNOWN_{value}")

    def safe_decision_name(value):
        return DECISION_NAMES.get(value, f"UNKNOWN_{value}")

    def compute_header_crc(msg_type, seq, job_id, payload_len):
        header_without_crc = struct.pack("<IHHIII", MAGIC, VERSION, msg_type, seq, job_id, payload_len)
        return zlib.crc32(header_without_crc) & 0xFFFFFFFF

    def build_frame(msg_type, seq, job_id, payload=b""):
        return HEADER_STRUCT.pack(
            MAGIC,
            VERSION,
            msg_type,
            seq,
            job_id,
            len(payload),
            compute_header_crc(msg_type, seq, job_id, len(payload)),
        ) + payload

    def parse_frame(raw):
        result = {"raw_hex": raw.hex(), "raw_len": len(raw)}
        if len(raw) < HEADER_STRUCT.size:
            result["error"] = "short_frame"
            return result
        magic, version, msg_type, seq, job_id, payload_len, header_crc32 = HEADER_STRUCT.unpack_from(raw)
        payload = raw[HEADER_STRUCT.size:HEADER_STRUCT.size + payload_len]
        result.update(
            {
                "magic": magic,
                "version": version,
                "msg_type": msg_type,
                "seq": seq,
                "job_id": job_id,
                "payload_len": payload_len,
                "payload_hex": payload.hex(),
            }
        )
        if msg_type == STATUS_RESP and len(payload) >= STATUS_RESP_STRUCT.size:
            guard_state, active_job_id, last_fault_code, heartbeat_ok, sticky_fault, total_fault_count = STATUS_RESP_STRUCT.unpack(
                payload[:STATUS_RESP_STRUCT.size]
            )
            result["status_resp"] = {
                "guard_state": guard_state,
                "guard_state_name": safe_guard_name(guard_state),
                "active_job_id": active_job_id,
                "last_fault_code": last_fault_code,
                "last_fault_name": safe_fault_name(last_fault_code),
                "heartbeat_ok": heartbeat_ok,
                "sticky_fault": sticky_fault,
                "total_fault_count": total_fault_count,
            }
        elif msg_type == JOB_ACK and len(payload) >= JOB_ACK_STRUCT.size:
            decision, fault_code, guard_state = JOB_ACK_STRUCT.unpack(payload[:JOB_ACK_STRUCT.size])
            result["job_ack"] = {
                "decision": decision,
                "decision_name": safe_decision_name(decision),
                "fault_code": fault_code,
                "fault_name": safe_fault_name(fault_code),
                "guard_state": guard_state,
                "guard_state_name": safe_guard_name(guard_state),
            }
        elif msg_type == HEARTBEAT_ACK and len(payload) >= HEARTBEAT_ACK_STRUCT.size:
            guard_state, heartbeat_ok = HEARTBEAT_ACK_STRUCT.unpack(payload[:HEARTBEAT_ACK_STRUCT.size])
            result["heartbeat_ack"] = {
                "guard_state": guard_state,
                "guard_state_name": safe_guard_name(guard_state),
                "heartbeat_ok": heartbeat_ok,
            }
        return result

    def open_endpoint():
        rpmsg_dev = CONFIG["rpmsg_dev"]
        if not os.path.exists(rpmsg_dev):
            raise FileNotFoundError(f"RPMsg 设备不存在: {rpmsg_dev}")
        return os.open(rpmsg_dev, os.O_RDWR | os.O_NONBLOCK)

    def drain(fd):
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                return
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                return
            if not chunk:
                return

    def transact(tx_bytes):
        fd = open_endpoint()
        try:
            drain(fd)
            os.write(fd, tx_bytes)
            rx = b""
            deadline = time.time() + float(CONFIG["response_timeout_sec"])
            while time.time() < deadline and len(rx) < int(CONFIG["max_rx_bytes"]):
                remaining = max(0.0, deadline - time.time())
                ready, _, _ = select.select([fd], [], [], remaining)
                if not ready:
                    break
                try:
                    chunk = os.read(fd, int(CONFIG["max_rx_bytes"]) - len(rx))
                except BlockingIOError:
                    continue
                if not chunk:
                    continue
                rx += chunk
                settle_deadline = time.time() + float(CONFIG["settle_timeout_sec"])
                while time.time() < settle_deadline and len(rx) < int(CONFIG["max_rx_bytes"]):
                    ready_more, _, _ = select.select([fd], [], [], max(0.0, settle_deadline - time.time()))
                    if not ready_more:
                        break
                    try:
                        more = os.read(fd, int(CONFIG["max_rx_bytes"]) - len(rx))
                    except BlockingIOError:
                        continue
                    if not more:
                        break
                    rx += more
                break
            return parse_frame(rx)
        finally:
            os.close(fd)

    def status_req(seq, job_id):
        return transact(build_frame(STATUS_REQ, seq, job_id))

    def job_req(seq, job_id, sha_hex, expected_outputs):
        payload = JOB_REQ_STRUCT.pack(bytes.fromhex(sha_hex), int(CONFIG["deadline_ms"]), int(expected_outputs), int(CONFIG["job_flags"]))
        return transact(build_frame(JOB_REQ, seq, job_id, payload))

    def heartbeat(seq, job_id):
        payload = HEARTBEAT_STRUCT.pack(2, 1234, 0, 100)
        return transact(build_frame(HEARTBEAT, seq, job_id, payload))

    def safe_stop(seq, job_id):
        return transact(build_frame(SAFE_STOP, seq, job_id))

    def base_result(action, logs):
        return {
            "status": "success",
            "action": action,
            "rpmsg_ctrl_exists": os.path.exists(CONFIG["rpmsg_ctrl"]),
            "rpmsg_dev_exists": os.path.exists(CONFIG["rpmsg_dev"]),
            "logs": logs,
        }

    def current_status_fields(frame):
        status = frame.get("status_resp") or {}
        return {
            "guard_state": status.get("guard_state_name", "UNKNOWN"),
            "active_job_id": status.get("active_job_id", 0),
            "last_fault_code": status.get("last_fault_name", "UNKNOWN"),
            "heartbeat_ok": status.get("heartbeat_ok", 0),
            "total_fault_count": status.get("total_fault_count", 0),
        }

    def run_status():
        logs = []
        job_id = int(CONFIG["job_id"])
        log(logs, "▶ 发送 STATUS_REQ")
        status = status_req(1, job_id)
        fields = current_status_fields(status)
        log(logs, f"◀ STATUS_RESP: guard={fields['guard_state']} last_fault={fields['last_fault_code']}")
        result = base_result("status", logs)
        result.update({"status_frame": status})
        result.update(fields)
        return result

    def run_wrong_sha():
        logs = []
        job_id = int(CONFIG["job_id"])
        pre = status_req(1, job_id)
        pre_fields = current_status_fields(pre)
        log(logs, f"▶ STATUS_REQ: 初始 guard={pre_fields['guard_state']}")
        sha = CONFIG["wrong_sha"]
        log(logs, f"▶ 发送 JOB_REQ，expected_sha={sha[:12]}...")
        ack = job_req(2, job_id, sha, 1)
        ack_fields = ack.get("job_ack") or {}
        log(logs, f"◀ JOB_ACK: {ack_fields.get('decision_name', 'UNKNOWN')}，fault={ack_fields.get('fault_name', 'UNKNOWN')}")
        post = status_req(3, job_id)
        post_fields = current_status_fields(post)
        log(logs, f"◀ STATUS_RESP: guard={post_fields['guard_state']} last_fault={post_fields['last_fault_code']}")
        result = base_result("wrong_sha", logs)
        result.update(
            {
                "pre_status": pre,
                "job_ack": ack,
                "post_status": post,
                "board_response": {
                    "decision": ack_fields.get("decision_name", "UNKNOWN"),
                    "fault_code": ack_fields.get("fault_name", "UNKNOWN"),
                    "guard_state": post_fields["guard_state"],
                },
            }
        )
        result.update(post_fields)
        return result

    def run_illegal_param():
        logs = []
        job_id = int(CONFIG["job_id"])
        pre = status_req(1, job_id)
        pre_fields = current_status_fields(pre)
        log(logs, f"▶ STATUS_REQ: 初始 guard={pre_fields['guard_state']}")
        sha = CONFIG["trusted_sha"]
        log(logs, "▶ 发送 JOB_REQ，expected_outputs=2")
        ack = job_req(2, job_id, sha, 2)
        ack_fields = ack.get("job_ack") or {}
        log(logs, f"◀ JOB_ACK: {ack_fields.get('decision_name', 'UNKNOWN')}，fault={ack_fields.get('fault_name', 'UNKNOWN')}")
        post = status_req(3, job_id)
        post_fields = current_status_fields(post)
        log(logs, f"◀ STATUS_RESP: guard={post_fields['guard_state']} last_fault={post_fields['last_fault_code']}")
        result = base_result("illegal_param", logs)
        result.update(
            {
                "pre_status": pre,
                "job_ack": ack,
                "post_status": post,
                "board_response": {
                    "decision": ack_fields.get("decision_name", "UNKNOWN"),
                    "fault_code": ack_fields.get("fault_name", "UNKNOWN"),
                    "guard_state": post_fields["guard_state"],
                },
            }
        )
        result.update(post_fields)
        return result

    def run_heartbeat_timeout():
        logs = []
        job_id = int(CONFIG["job_id"])
        pre = status_req(1, job_id)
        pre_fields = current_status_fields(pre)
        log(logs, f"▶ STATUS_REQ: 初始 guard={pre_fields['guard_state']}")
        job = job_req(2, job_id, CONFIG["trusted_sha"], 1)
        job_ack = job.get("job_ack") or {}
        log(logs, f"◀ JOB_ACK: {job_ack.get('decision_name', 'UNKNOWN')}")
        hb = heartbeat(3, job_id)
        hb_ack = hb.get("heartbeat_ack") or {}
        log(logs, f"◀ HEARTBEAT_ACK: guard={hb_ack.get('guard_state_name', 'UNKNOWN')} ok={hb_ack.get('heartbeat_ok', 0)}")
        wait_sec = float(CONFIG["wait_without_heartbeat_sec"])
        log(logs, f"⏳ 停发 heartbeat {wait_sec:.1f} 秒，等待 FIT-03 watchdog 结果")
        time.sleep(wait_sec)
        timeout_status = status_req(4, job_id)
        timeout_fields = current_status_fields(timeout_status)
        log(logs, f"◀ STATUS_RESP: guard={timeout_fields['guard_state']} last_fault={timeout_fields['last_fault_code']}")
        cleanup = safe_stop(5, job_id)
        cleanup_fields = current_status_fields(cleanup)
        log(logs, f"▶ SAFE_STOP 清理，返回 guard={cleanup_fields['guard_state']}")
        final_status = status_req(6, job_id)
        final_fields = current_status_fields(final_status)
        log(logs, f"◀ 最终 STATUS_RESP: guard={final_fields['guard_state']} last_fault={final_fields['last_fault_code']}")
        result = base_result("heartbeat_timeout", logs)
        result.update(
            {
                "pre_status": pre,
                "job_ack": job,
                "heartbeat_ack": hb,
                "timeout_status": timeout_status,
                "cleanup_status": cleanup,
                "final_status": final_status,
                "board_response": {
                    "decision": job_ack.get("decision_name", "UNKNOWN"),
                    "fault_code": timeout_fields["last_fault_code"],
                    "guard_state": final_fields["guard_state"],
                },
            }
        )
        result.update(final_fields)
        return result

    def run_recover():
        logs = []
        job_id = int(CONFIG["job_id"])
        cleanup = safe_stop(1, job_id)
        cleanup_fields = current_status_fields(cleanup)
        log(logs, f"▶ SAFE_STOP: guard={cleanup_fields['guard_state']} last_fault={cleanup_fields['last_fault_code']}")
        final_status = status_req(2, job_id)
        final_fields = current_status_fields(final_status)
        log(logs, f"◀ STATUS_RESP: guard={final_fields['guard_state']} last_fault={final_fields['last_fault_code']}")
        result = base_result("recover", logs)
        result.update(
            {
                "cleanup_status": cleanup,
                "final_status": final_status,
                "board_response": {
                    "decision": "ACK",
                    "fault_code": final_fields["last_fault_code"],
                    "guard_state": final_fields["guard_state"],
                },
            }
        )
        result.update(final_fields)
        return result

    def main():
        action = CONFIG["action"]
        if action == "status":
            return run_status()
        if action == "wrong_sha":
            return run_wrong_sha()
        if action == "illegal_param":
            return run_illegal_param()
        if action == "heartbeat_timeout":
            return run_heartbeat_timeout()
        if action == "recover":
            return run_recover()
        return {"status": "error", "action": action, "message": f"unsupported action: {action}", "logs": []}

    try:
        print(json.dumps(main(), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"status": "error", "action": CONFIG.get("action", "unknown"), "message": str(exc), "logs": []}, ensure_ascii=False))
    """
)


def parse_json_stdout(raw: str) -> dict[str, Any]:
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    raise ValueError("remote fault action produced no JSON payload")


def mutate_sha(sha: str) -> str:
    if not sha:
        return sha
    last = sha[-1]
    replacement = "0" if last != "0" else "1"
    return sha[:-1] + replacement


def build_remote_script(config: dict[str, Any]) -> str:
    return REMOTE_DRIVER_TEMPLATE.replace("__CONFIG_JSON__", repr(json.dumps(config, ensure_ascii=False)))


def run_remote_driver(access: BoardAccessConfig, config: dict[str, Any], timeout_sec: float) -> dict[str, Any]:
    command = [
        "bash",
        str(SSH_HELPER),
        "--host",
        access.host,
        "--user",
        access.user,
        "--pass",
        access.password,
        "--port",
        access.port,
        "--",
        "python3",
        "-",
    ]
    script = build_remote_script(config)
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            input=script,
            capture_output=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "status_category": "timeout",
            "action": config["action"],
            "message": build_operator_message(config["action"], "timeout"),
            "logs": [],
            "diagnostics": {},
        }
    except OSError as exc:
        status_category = classify_status_category(status="launch_error", error=str(exc))
        return {
            "status": "launch_error",
            "status_category": status_category,
            "action": config["action"],
            "message": build_operator_message(config["action"], status_category),
            "logs": [],
            "diagnostics": build_diagnostics(error=str(exc)),
        }

    try:
        payload = parse_json_stdout(result.stdout)
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
            "action": config["action"],
            "message": build_operator_message(config["action"], status_category),
            "logs": [],
            "diagnostics": build_diagnostics(stdout=stdout, stderr=stderr, error=str(exc), returncode=result.returncode),
        }

    payload["stdout"] = result.stdout.strip()
    payload["stderr"] = result.stderr.strip()
    payload["status_category"] = "success" if payload.get("status") == "success" else classify_status_category(
        status=str(payload.get("status") or "error"),
        stdout=result.stdout,
        stderr=result.stderr,
    )
    payload["diagnostics"] = build_diagnostics(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )
    return payload


def default_driver_config(action: str, trusted_sha: str) -> dict[str, Any]:
    return {
        "action": action,
        "job_id": int((time.time() * 1000) % 100000) + 9300,
        "trusted_sha": trusted_sha,
        "wrong_sha": mutate_sha(trusted_sha),
        "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
        "rpmsg_dev": "/dev/rpmsg0",
        "response_timeout_sec": 2.0,
        "settle_timeout_sec": 0.05,
        "max_rx_bytes": 4096,
        "wait_without_heartbeat_sec": 5.0,
        "deadline_ms": 60000,
        "job_flags": 3,
    }


def query_live_status(access: BoardAccessConfig, *, trusted_sha: str, timeout_sec: float = 12.0) -> dict[str, Any]:
    config = default_driver_config("status", trusted_sha)
    payload = run_remote_driver(access, config, timeout_sec)
    payload["execution_mode"] = "live" if payload.get("status") == "success" else "error"
    return payload


def run_fault_action(
    access: BoardAccessConfig,
    *,
    fault_type: str,
    trusted_sha: str,
    timeout_sec: float = 20.0,
) -> dict[str, Any]:
    action = FAULT_TYPE_TO_ACTION.get(fault_type, fault_type)
    config = default_driver_config(action, trusted_sha)
    payload = run_remote_driver(access, config, timeout_sec)
    payload["execution_mode"] = "live" if payload.get("status") == "success" else "error"
    return payload


def run_recover_action(access: BoardAccessConfig, *, trusted_sha: str, timeout_sec: float = 12.0) -> dict[str, Any]:
    config = default_driver_config("recover", trusted_sha)
    payload = run_remote_driver(access, config, timeout_sec)
    payload["execution_mode"] = "live" if payload.get("status") == "success" else "error"
    return payload
