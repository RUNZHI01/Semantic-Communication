#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Wrap an existing trusted-current runner with control-plane events. "
            "This wrapper never rewrites the inference data path."
        )
    )
    parser.add_argument("--runner-cmd", required=True, help="Existing benchmark or reconstruction command.")
    parser.add_argument("--output-dir", required=True, help="Where manifest/log/control traces should be written.")
    parser.add_argument("--job-id", type=int, default=int(time.time()), help="Control-plane job identifier.")
    parser.add_argument("--variant", default="current", help="Human-readable variant tag.")
    parser.add_argument("--expected-sha256", default="", help="Trusted current SHA, defaults to env if unset.")
    parser.add_argument("--deadline-ms", type=int, default=300000, help="Control-plane deadline metadata.")
    parser.add_argument("--expected-outputs", type=int, default=300, help="Expected output count metadata.")
    parser.add_argument("--job-flags", default="reconstruction", help="Payload or reconstruction marker.")
    parser.add_argument(
        "--heartbeat-interval-sec",
        type=float,
        default=5.0,
        help="Heartbeat cadence while the runner is active.",
    )
    parser.add_argument(
        "--runner-timeout-sec",
        type=float,
        default=0.0,
        help="Kill the wrapped runner after this many seconds; 0 disables the timeout.",
    )
    parser.add_argument(
        "--transport",
        choices=("none", "hook"),
        default="none",
        help="none=only emit local traces; hook=invoke an external control hook for each phase.",
    )
    parser.add_argument(
        "--control-hook-cmd",
        default="",
        help=(
            "When --transport hook is used, this shell command is invoked for each control event. "
            "The event JSON is passed on stdin; OPENAMP_PHASE is set in the environment."
        ),
    )
    parser.add_argument(
        "--control-hook-timeout-sec",
        type=float,
        default=5.0,
        help="Timeout for each external hook invocation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Emit control traces and manifest without executing the wrapped runner.",
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


def json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jsonl_append(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as outfile:
        outfile.write(json.dumps(payload, ensure_ascii=False) + "\n")


def parse_response(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def normalize_decision(response: dict[str, Any] | None) -> str | None:
    if not response:
        return None
    if "decision" in response:
        value = response["decision"]
    elif "allow" in response:
        value = "ALLOW" if response["allow"] else "DENY"
    else:
        return None
    if isinstance(value, bool):
        return "ALLOW" if value else "DENY"
    text = str(value).strip().upper()
    if text in {"1", "ALLOW", "ALLOWED", "TRUE"}:
        return "ALLOW"
    if text in {"0", "DENY", "DENIED", "FALSE"}:
        return "DENY"
    return text or None


def emit_event(
    *,
    trace_path: Path,
    phase: str,
    payload: dict[str, Any],
    transport: str,
    hook_cmd: str,
    hook_timeout_sec: float,
) -> dict[str, Any]:
    event = {
        "at": now_iso(),
        "phase": phase,
        "payload": payload,
    }
    hook_result: dict[str, Any] | None = None
    if transport == "hook":
        env = os.environ.copy()
        env["OPENAMP_PHASE"] = phase
        env["OPENAMP_JOB_ID"] = str(payload.get("job_id", ""))
        result = subprocess.run(
            ["bash", "-lc", hook_cmd],
            check=False,
            input=json.dumps(event, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT,
            env=env,
            timeout=hook_timeout_sec,
        )
        hook_result = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "response": parse_response(result.stdout),
        }
        event["hook_result"] = hook_result
    jsonl_append(trace_path, event)
    return hook_result or {}


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    process.kill()
    process.wait(timeout=5)


def build_manifest(args: argparse.Namespace, output_dir: Path, expected_sha256: str) -> dict[str, Any]:
    return {
        "created_at": now_iso(),
        "job_id": args.job_id,
        "variant": args.variant,
        "job_flags": args.job_flags,
        "runner_cmd": args.runner_cmd,
        "runner_cmd_shell_quoted": shlex.join(["bash", "-lc", args.runner_cmd]),
        "expected_sha256": expected_sha256,
        "expected_outputs": args.expected_outputs,
        "deadline_ms": args.deadline_ms,
        "heartbeat_interval_sec": args.heartbeat_interval_sec,
        "runner_timeout_sec": args.runner_timeout_sec,
        "transport": args.transport,
        "control_hook_cmd": args.control_hook_cmd,
        "dry_run": args.dry_run,
        "output_dir": str(output_dir),
        "boundary_note": "control plane only; the wrapped runner remains the existing inference data path",
    }


def main() -> int:
    args = parse_args()
    if args.transport == "hook" and not args.control_hook_cmd:
        raise SystemExit("ERROR: --control-hook-cmd is required when --transport hook is used.")
    if args.heartbeat_interval_sec <= 0:
        raise SystemExit("ERROR: --heartbeat-interval-sec must be > 0.")
    if args.control_hook_timeout_sec <= 0:
        raise SystemExit("ERROR: --control-hook-timeout-sec must be > 0.")
    if args.deadline_ms <= 0:
        raise SystemExit("ERROR: --deadline-ms must be > 0.")

    output_dir = resolve_output_dir(args.output_dir)
    trace_path = output_dir / "control_trace.jsonl"
    summary_path = output_dir / "wrapper_summary.json"
    manifest_path = output_dir / "job_manifest.json"
    runner_log_path = output_dir / "runner.log"

    expected_sha256 = args.expected_sha256 or os.environ.get("INFERENCE_CURRENT_EXPECTED_SHA256", "")
    manifest = build_manifest(args, output_dir, expected_sha256)
    json_dump(manifest_path, manifest)

    status_req_payload = {
        "job_id": args.job_id,
        "variant": args.variant,
        "expected_sha256": expected_sha256,
        "job_flags": args.job_flags,
    }
    status_response = emit_event(
        trace_path=trace_path,
        phase="STATUS_REQ",
        payload=status_req_payload,
        transport=args.transport,
        hook_cmd=args.control_hook_cmd,
        hook_timeout_sec=args.control_hook_timeout_sec,
    )

    job_req_payload = {
        "job_id": args.job_id,
        "expected_sha256": expected_sha256,
        "deadline_ms": args.deadline_ms,
        "expected_outputs": args.expected_outputs,
        "job_flags": args.job_flags,
        "runner_cmd": args.runner_cmd,
    }
    job_req_response = emit_event(
        trace_path=trace_path,
        phase="JOB_REQ",
        payload=job_req_payload,
        transport=args.transport,
        hook_cmd=args.control_hook_cmd,
        hook_timeout_sec=args.control_hook_timeout_sec,
    )
    decision = normalize_decision(job_req_response.get("response") if job_req_response else None)
    if decision == "DENY":
        summary = {
            "finished_at": now_iso(),
            "job_id": args.job_id,
            "result": "denied_by_control_hook",
            "status_response": status_response,
            "job_req_response": job_req_response,
            "runner_exit_code": None,
            "runner_log": str(runner_log_path),
            "manifest_path": str(manifest_path),
            "control_trace_path": str(trace_path),
        }
        json_dump(summary_path, summary)
        emit_event(
            trace_path=trace_path,
            phase="JOB_ACK",
            payload={"job_id": args.job_id, "decision": "DENY"},
            transport="none",
            hook_cmd="",
            hook_timeout_sec=args.control_hook_timeout_sec,
        )
        print(json.dumps(summary, ensure_ascii=False))
        return 2

    emit_event(
        trace_path=trace_path,
        phase="JOB_ACK",
        payload={"job_id": args.job_id, "decision": "ALLOW" if decision != "DENY" else "DENY"},
        transport="none",
        hook_cmd="",
        hook_timeout_sec=args.control_hook_timeout_sec,
    )

    if args.dry_run:
        summary = {
            "finished_at": now_iso(),
            "job_id": args.job_id,
            "result": "dry_run_only",
            "status_response": status_response,
            "job_req_response": job_req_response,
            "runner_exit_code": None,
            "runner_log": str(runner_log_path),
            "manifest_path": str(manifest_path),
            "control_trace_path": str(trace_path),
        }
        json_dump(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    start_time = time.monotonic()
    return_code = None
    timed_out = False

    with runner_log_path.open("w", encoding="utf-8") as logfile:
        logfile.write(f"[{now_iso()}] openamp wrapper start\n")
        logfile.write(f"runner_cmd={args.runner_cmd}\n")
        logfile.flush()
        process = subprocess.Popen(
            ["bash", "-lc", args.runner_cmd],
            cwd=PROJECT_ROOT,
            stdout=logfile,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )
        try:
            last_heartbeat = start_time
            while True:
                return_code = process.poll()
                elapsed = time.monotonic() - start_time
                if return_code is not None:
                    break
                if args.runner_timeout_sec > 0 and elapsed > args.runner_timeout_sec:
                    timed_out = True
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(1.0)
                    if process.poll() is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    return_code = process.wait(timeout=5)
                    break
                if time.monotonic() - last_heartbeat >= args.heartbeat_interval_sec:
                    emit_event(
                        trace_path=trace_path,
                        phase="HEARTBEAT",
                        payload={
                            "job_id": args.job_id,
                            "elapsed_ms": int(elapsed * 1000),
                            "runtime_state": "RUNNING",
                        },
                        transport=args.transport,
                        hook_cmd=args.control_hook_cmd,
                        hook_timeout_sec=args.control_hook_timeout_sec,
                    )
                    last_heartbeat = time.monotonic()
                time.sleep(0.2)
        except KeyboardInterrupt:
            timed_out = True
            terminate_process(process)
            return_code = process.returncode
            emit_event(
                trace_path=trace_path,
                phase="SAFE_STOP",
                payload={"job_id": args.job_id, "reason": "keyboard_interrupt"},
                transport=args.transport,
                hook_cmd=args.control_hook_cmd,
                hook_timeout_sec=args.control_hook_timeout_sec,
            )
            raise

    finished_at = now_iso()
    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    if timed_out:
        emit_event(
            trace_path=trace_path,
            phase="SAFE_STOP",
            payload={"job_id": args.job_id, "reason": "runner_timeout", "elapsed_ms": elapsed_ms},
            transport=args.transport,
            hook_cmd=args.control_hook_cmd,
            hook_timeout_sec=args.control_hook_timeout_sec,
        )

    emit_event(
        trace_path=trace_path,
        phase="JOB_DONE",
        payload={
            "job_id": args.job_id,
            "elapsed_ms": elapsed_ms,
            "result_code": 0 if (return_code or 0) == 0 and not timed_out else 1,
            "runner_exit_code": return_code,
            "timed_out": timed_out,
        },
        transport=args.transport,
        hook_cmd=args.control_hook_cmd,
        hook_timeout_sec=args.control_hook_timeout_sec,
    )

    summary = {
        "finished_at": finished_at,
        "job_id": args.job_id,
        "result": "timeout" if timed_out else ("success" if (return_code or 0) == 0 else "runner_failed"),
        "status_response": status_response,
        "job_req_response": job_req_response,
        "runner_exit_code": return_code,
        "runner_log": str(runner_log_path),
        "manifest_path": str(manifest_path),
        "control_trace_path": str(trace_path),
        "summary_path": str(summary_path),
    }
    json_dump(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 124 if timed_out else (return_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
