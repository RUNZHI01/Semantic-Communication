#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
from functools import lru_cache
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SSH_HELPER = PROJECT_ROOT / "session_bootstrap" / "scripts" / "ssh_with_password.sh"
BRIDGE_SCRIPT = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_rpmsg_bridge.py"
PROTOCOL_SCRIPT = PROJECT_ROOT / "openamp_mock" / "protocol.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Forward OpenAMP wrapper hook stdin to the board-side rpmsg bridge over SSH so the "
            "demo can expose real control-plane phases without rewriting the inference data path."
        )
    )
    parser.add_argument("--host", required=True, help="Board SSH host.")
    parser.add_argument("--user", required=True, help="Board SSH user.")
    parser.add_argument("--password", required=True, help="Board SSH password.")
    parser.add_argument("--port", default="22", help="Board SSH port.")
    parser.add_argument("--remote-project-root", default="", help="Optional remote repo root override.")
    parser.add_argument("--remote-jscc-dir", default="", help="Optional remote JSCC workspace for root inference.")
    parser.add_argument(
        "--remote-output-root",
        default="/tmp/openamp_demo_hook",
        help="Remote directory used for per-phase bridge artifacts.",
    )
    parser.add_argument("--rpmsg-ctrl", default="/dev/rpmsg_ctrl0", help="Board rpmsg control device.")
    parser.add_argument("--rpmsg-dev", default="/dev/rpmsg0", help="Board rpmsg endpoint device.")
    return parser.parse_args()


def read_event(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def detect_phase(event: dict[str, Any]) -> str:
    phase = str(event.get("phase") or "").strip().upper()
    if phase:
        return phase
    return "STATUS_REQ"


def detect_job_id(event: dict[str, Any]) -> int:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    try:
        return int(payload.get("job_id", 0) or 0)
    except (TypeError, ValueError):
        return 0


@lru_cache(maxsize=1)
def build_bridge_bundle_base64() -> str:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gzip_file:
        with tarfile.open(fileobj=gzip_file, mode="w") as archive:
            for relative_path, source in (
                ("session_bootstrap/scripts/openamp_rpmsg_bridge.py", BRIDGE_SCRIPT),
                ("openamp_mock/protocol.py", PROTOCOL_SCRIPT),
            ):
                payload = source.read_bytes()
                info = tarfile.TarInfo(relative_path)
                info.size = len(payload)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(payload))

            init_info = tarfile.TarInfo("openamp_mock/__init__.py")
            init_info.size = 0
            init_info.mode = 0o644
            init_info.mtime = 0
            archive.addfile(init_info, io.BytesIO(b""))
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_remote_command(args: argparse.Namespace, *, phase: str, job_id: int) -> str:
    remote_output_dir = f"{args.remote_output_root.rstrip('/')}/{job_id or 'adhoc'}/{phase.lower()}"
    # Ship the validated bridge runtime from the local repo so the board does not need a repo checkout.
    bridge_bundle = build_bridge_bundle_base64()
    return f"""
set -euo pipefail
PHASE={shlex.quote(phase)}
OUTPUT_DIR={shlex.quote(remote_output_dir)}
STAGE_ROOT="$(mktemp -d /tmp/openamp_demo_bridge.XXXXXX)"
cleanup() {{
  rm -rf "$STAGE_ROOT"
}}
trap cleanup EXIT
STAGE_ROOT="$STAGE_ROOT" python3 - <<'PY'
import base64
import gzip
import io
import os
from pathlib import Path
import tarfile

stage_root = Path(os.environ["STAGE_ROOT"])
stage_root.mkdir(parents=True, exist_ok=True)
bundle = base64.b64decode({bridge_bundle!r})
with gzip.GzipFile(fileobj=io.BytesIO(bundle), mode="rb") as gzip_file:
    with tarfile.open(fileobj=gzip_file, mode="r:") as archive:
        archive.extractall(stage_root)
PY
mkdir -p "$OUTPUT_DIR"
OPENAMP_PHASE="$PHASE" python3 "$STAGE_ROOT/session_bootstrap/scripts/openamp_rpmsg_bridge.py" --hook-stdin --rpmsg-ctrl {shlex.quote(args.rpmsg_ctrl)} --rpmsg-dev {shlex.quote(args.rpmsg_dev)} --output-dir "$OUTPUT_DIR"
""".strip()


def main() -> int:
    args = parse_args()
    raw_event = sys.stdin.read()
    event = read_event(raw_event)
    phase = detect_phase(event)
    job_id = detect_job_id(event)
    remote_command = build_remote_command(args, phase=phase, job_id=job_id)
    command = [
        "bash",
        str(SSH_HELPER),
        "--host",
        args.host,
        "--user",
        args.user,
        "--pass",
        args.password,
        "--port",
        args.port,
        "--",
        "bash",
        "-lc",
        remote_command,
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        input=raw_event,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode == 0 or result.stdout.strip():
        return result.returncode
    sys.stdout.write(
        json.dumps(
            {
                "phase": phase,
                "source": "openamp_demo_remote_hook_proxy",
                "transport_status": "ssh_bridge_launch_failed",
                "protocol_semantics": "not_verified",
                "note": f"远端 bridge 启动失败，rc={result.returncode}。",
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
