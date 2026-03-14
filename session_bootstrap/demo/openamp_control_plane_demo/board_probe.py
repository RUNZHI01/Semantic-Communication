from __future__ import annotations

import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONNECT_SCRIPT = PROJECT_ROOT / "session_bootstrap" / "scripts" / "connect_phytium_pi.sh"
SSH_WITH_PASSWORD_SCRIPT = PROJECT_ROOT / "session_bootstrap" / "scripts" / "ssh_with_password.sh"

REMOTE_PROBE_CODE = r"""
import glob
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""

def sha256(path):
    if not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

remoteproc = []
for state_path in sorted(glob.glob("/sys/class/remoteproc/remoteproc*/state")):
    base = Path(state_path).parent
    remoteproc.append(
        {
            "name": base.name,
            "state": read_text(state_path),
            "firmware": read_text(base / "firmware"),
        }
    )

rpmsg_devices = sorted(glob.glob("/dev/rpmsg*"))
rpmsg_channels = []
for name_path in sorted(glob.glob("/sys/bus/rpmsg/devices/*/name")):
    name = read_text(name_path)
    if name:
        rpmsg_channels.append(name)

firmware_path = "/lib/firmware/openamp_core0.elf"
payload = {
    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "hostname": socket.gethostname(),
    "whoami": subprocess.check_output(["whoami"], text=True).strip(),
    "remoteproc": remoteproc,
    "rpmsg_devices": rpmsg_devices,
    "rpmsg_channels": sorted(set(rpmsg_channels)),
    "firmware": {
        "path": firmware_path,
        "exists": os.path.exists(firmware_path),
        "size": os.path.getsize(firmware_path) if os.path.exists(firmware_path) else 0,
        "sha256": sha256(firmware_path),
    },
}
print(json.dumps(payload, ensure_ascii=True))
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def parse_env_file(env_file: str | None) -> dict[str, str]:
    if not env_file:
        return {}
    path = Path(env_file)
    if not path.is_absolute():
        path = (PROJECT_ROOT / env_file).resolve()
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_probe_command(env_file: str | None = None) -> list[str]:
    remote_cmd = f"python3 -c {shlex.quote(REMOTE_PROBE_CODE)}"
    values = parse_env_file(env_file)
    if values.get("REMOTE_HOST") and values.get("REMOTE_USER") and values.get("REMOTE_PASS"):
        return [
            "bash",
            str(SSH_WITH_PASSWORD_SCRIPT),
            "--host",
            values["REMOTE_HOST"],
            "--user",
            values["REMOTE_USER"],
            "--pass",
            values["REMOTE_PASS"],
            "--port",
            values.get("REMOTE_SSH_PORT", "22"),
            "--",
            remote_cmd,
        ]

    command = ["bash", str(CONNECT_SCRIPT)]
    if env_file:
        command.extend(["--env", env_file])
    command.extend(["--", remote_cmd])
    return command


def parse_json_stdout(raw: str) -> dict[str, Any]:
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if not line:
            continue
        return json.loads(line)
    raise ValueError("probe produced no JSON payload")


def summarize_probe(details: dict[str, Any]) -> str:
    remoteproc = details.get("remoteproc", [])
    states = ", ".join(
        f"{item.get('name', 'remoteproc')}={item.get('state', 'unknown')}" for item in remoteproc
    ) or "no remoteproc entries"
    rpmsg_count = len(details.get("rpmsg_devices", []))
    firmware_sha = details.get("firmware", {}).get("sha256", "")
    firmware_note = f"firmware {firmware_sha[:12]}" if firmware_sha else "firmware sha unavailable"
    return f"{details.get('hostname', 'board')} reachable; {states}; {rpmsg_count} rpmsg device(s); {firmware_note}."


def run_live_probe(env_file: str | None = None, timeout_sec: float = 30.0) -> dict[str, Any]:
    requested_at = now_iso()
    command = build_probe_command(env_file)
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "requested_at": requested_at,
            "reachable": False,
            "status": "timeout",
            "summary": "The read-only SSH probe timed out before a response arrived.",
            "error": "probe timeout",
            "details": {},
        }

    if result.returncode != 0:
        return {
            "requested_at": requested_at,
            "reachable": False,
            "status": "error",
            "summary": "The read-only SSH probe could not reach the board from this environment.",
            "error": (result.stderr or result.stdout).strip(),
            "details": {},
        }

    try:
        details = parse_json_stdout(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "requested_at": requested_at,
            "reachable": False,
            "status": "parse_error",
            "summary": "The read-only SSH probe returned output that could not be parsed as JSON.",
            "error": str(exc),
            "details": {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
        }

    return {
        "requested_at": requested_at,
        "reachable": True,
        "status": "success",
        "summary": summarize_probe(details),
        "error": "",
        "details": details,
    }


def write_probe_output(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
