#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
LAUNCHER="${OPENAMP_DEMO_PROBE_ONCE_LAUNCHER:-$SCRIPT_DIR/run_openamp_demo.sh}"
PYTHON_BIN="${OPENAMP_DEMO_PROBE_ONCE_PYTHON:-python3}"
WAIT_STEPS="${OPENAMP_DEMO_PROBE_ONCE_WAIT_STEPS:-40}"
WAIT_SEC="${OPENAMP_DEMO_PROBE_ONCE_WAIT_SEC:-0.5}"

HOST="127.0.0.1"
PORT="18079"
OUTPUT_DIR=""
PASSWORD=""
PROMPT_PASSWORD=0
PROBE_ENV=""
EXTRA_LAUNCHER_ARGS=()

usage() {
  cat <<'EOF'
Usage: run_openamp_demo_probe_once.sh [options]

Launch demo once, request startup probe path, capture:
  - /api/health
  - /api/system-status
  - /api/snapshot
print a compact summary, then stop the demo process.

Options:
  --host <host>         Bind host for temporary demo server (default: 127.0.0.1)
  --port <port>         Bind port for temporary demo server (default: 18079)
  --output-dir <dir>    Capture directory
  --probe-env <path>    Forward a probe env file to the launcher
  --probe-timeout-sec <n>  Forward startup probe timeout to the launcher
  --password <value>    Use one runtime password without prompting
  --prompt-password     Prompt once (no echo) for runtime password
  -- <args...>          Forward any remaining args to run_openamp_demo.sh
  --help                Show this help
EOF
}

while (($#)); do
  case "$1" in
    --host)
      HOST="${2:?missing value for --host}"
      shift 2
      ;;
    --port)
      PORT="${2:?missing value for --port}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    --probe-env)
      PROBE_ENV="${2:?missing value for --probe-env}"
      shift 2
      ;;
    --probe-timeout-sec)
      EXTRA_LAUNCHER_ARGS+=("$1" "${2:?missing value for --probe-timeout-sec}")
      shift 2
      ;;
    --probe-timeout-sec=*)
      EXTRA_LAUNCHER_ARGS+=("$1")
      shift
      ;;
    --password)
      PASSWORD="${2:?missing value for --password}"
      shift 2
      ;;
    --prompt-password)
      PROMPT_PASSWORD=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_LAUNCHER_ARGS+=("$@")
      break
      ;;
    *)
      EXTRA_LAUNCHER_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$PASSWORD" && "$PROMPT_PASSWORD" -eq 1 ]]; then
  echo "Refusing to combine --password with --prompt-password. Use one password input path." >&2
  exit 2
fi

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$PROJECT_ROOT/session_bootstrap/tmp/openamp_demo_probe_once_$(date +%Y%m%d_%H%M%S)"
fi
mkdir -p "$OUTPUT_DIR"

API_BASE="http://${HOST}:${PORT}"
HEALTH_JSON="$OUTPUT_DIR/api_health.json"
SYSTEM_STATUS_JSON="$OUTPUT_DIR/api_system_status.json"
SNAPSHOT_JSON="$OUTPUT_DIR/api_snapshot.json"
SUMMARY_JSON="$OUTPUT_DIR/summary.json"
LAUNCHER_LOG="$OUTPUT_DIR/launcher.log"
DEMO_PID=""

prompt_password() {
  local -n out_ref="$1"
  local prompt_text="OpenAMP demo runtime password: "
  if [[ -t 0 ]]; then
    read -r -s -p "$prompt_text" out_ref
    printf '\n' >&2
  else
    IFS= read -r out_ref
  fi
}

cleanup() {
  local exit_code=$?
  if [[ -n "$DEMO_PID" ]] && kill -0 "$DEMO_PID" 2>/dev/null; then
    kill "$DEMO_PID" 2>/dev/null || true
    wait "$DEMO_PID" 2>/dev/null || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT

wait_for_health() {
  local attempt=0
  while (( attempt < WAIT_STEPS )); do
    if "$PYTHON_BIN" - <<'PY' "$API_BASE"
from __future__ import annotations
import json
import sys
import urllib.request

base = sys.argv[1].rstrip("/")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
request = urllib.request.Request(base + "/api/health", headers={"Accept": "application/json"})
try:
    with opener.open(request, timeout=1.5) as response:
        payload = json.loads(response.read().decode("utf-8"))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if str(payload.get("status") or "").strip().lower() == "ok" else 1)
PY
    then
      return 0
    fi
    if [[ -n "$DEMO_PID" ]] && ! kill -0 "$DEMO_PID" 2>/dev/null; then
      return 1
    fi
    attempt=$((attempt + 1))
    sleep "$WAIT_SEC"
  done
  return 1
}

capture_endpoint() {
  local path="$1"
  local output_path="$2"
  "$PYTHON_BIN" - <<'PY' "$API_BASE" "$path" "$output_path"
from __future__ import annotations
import json
import sys
import urllib.request
from pathlib import Path

base, path, output_path = sys.argv[1:4]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
request = urllib.request.Request(base.rstrip("/") + path, headers={"Accept": "application/json"})
with opener.open(request, timeout=2.0) as response:
    payload = json.loads(response.read().decode("utf-8"))
Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

launch_demo() {
  local -a launch_args=("--host" "$HOST" "--port" "$PORT" "--probe-startup")
  if [[ -n "$PROBE_ENV" ]]; then
    launch_args+=("--probe-env" "$PROBE_ENV")
  fi
  launch_args+=("${EXTRA_LAUNCHER_ARGS[@]}")

  if [[ "$PROMPT_PASSWORD" -eq 1 ]]; then
    local runtime_password=""
    prompt_password runtime_password
    env REMOTE_PASS="$runtime_password" PHYTIUM_PI_PASSWORD="$runtime_password" \
      bash "$LAUNCHER" "${launch_args[@]}" >"$LAUNCHER_LOG" 2>&1 &
  elif [[ -n "$PASSWORD" ]]; then
    env REMOTE_PASS="$PASSWORD" PHYTIUM_PI_PASSWORD="$PASSWORD" \
      bash "$LAUNCHER" "${launch_args[@]}" >"$LAUNCHER_LOG" 2>&1 &
  else
    bash "$LAUNCHER" "${launch_args[@]}" >"$LAUNCHER_LOG" 2>&1 &
  fi
  DEMO_PID="$!"
}

launch_demo

if ! wait_for_health; then
  if [[ -n "$DEMO_PID" ]] && ! kill -0 "$DEMO_PID" 2>/dev/null; then
    echo "ERROR: demo launcher exited before ${API_BASE} became healthy" >&2
  else
    echo "ERROR: demo health endpoint did not become ready at ${API_BASE}" >&2
  fi
  echo "launcher_log=${LAUNCHER_LOG}" >&2
  exit 1
fi

capture_endpoint "/api/health" "$HEALTH_JSON"
capture_endpoint "/api/system-status" "$SYSTEM_STATUS_JSON"
capture_endpoint "/api/snapshot" "$SNAPSHOT_JSON"

"$PYTHON_BIN" - <<'PY' "$HEALTH_JSON" "$SYSTEM_STATUS_JSON" "$SNAPSHOT_JSON" "$SUMMARY_JSON"
from __future__ import annotations
import json
import sys
from pathlib import Path

health = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
system = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
snapshot = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
summary_path = Path(sys.argv[4])

board_status = snapshot.get("board", {}).get("current_status", {})
board_label = str(board_status.get("label") or "")
board_summary = str(board_status.get("summary") or "")
fresh_probe_visible = board_label != "保存的只读 SSH 探板"
startup_probe_note = (
    "fresh probe visible in snapshot"
    if fresh_probe_visible
    else "snapshot still reflects saved probe record; do not overclaim fresh startup probe success"
)
summary = {
    "health_status": health.get("status"),
    "execution_mode": system.get("execution_mode", {}).get("label"),
    "connection_ready": system.get("board_access", {}).get("connection_ready"),
    "missing_connection_fields": system.get("board_access", {}).get("missing_connection_fields"),
    "mode_effective_label": snapshot.get("mode", {}).get("effective_label"),
    "board_current_status_label": board_label,
    "board_current_status_summary": board_summary,
    "valid_instance": snapshot.get("latest_live_status", {}).get("valid_instance"),
    "fresh_probe_visible": fresh_probe_visible,
    "startup_probe_note": startup_probe_note,
}
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("[probe-once] summary:")
print(f"  execution_mode: {summary['execution_mode']}")
print(f"  connection_ready: {summary['connection_ready']}")
print(f"  missing_connection_fields: {summary['missing_connection_fields']}")
print(f"  mode.effective_label: {summary['mode_effective_label']}")
print(f"  board.current_status.label: {summary['board_current_status_label']}")
print(f"  board.current_status.summary: {summary['board_current_status_summary']}")
print(f"  valid_instance: {summary['valid_instance']}")
print(f"  fresh_probe_visible: {summary['fresh_probe_visible']}")
print(f"  startup_probe_note: {summary['startup_probe_note']}")
print(f"[probe-once] capture_dir: {summary_path.parent}")
PY
