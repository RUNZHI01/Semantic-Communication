#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$SESSION_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  run_big_little_compare.sh [options]

Options:
  --env <path>             Optional env file to source before running.
  --run-id <id>            Override the local compare run_id.
  --serial-cmd <command>   Override the serial command.
  --pipeline-cmd <command> Override the pipeline command.
  --allow-overwrite        Allow overwriting an existing local run_id.
  -h, --help               Show this message.

Defaults:
  serial command   -> BIG_LITTLE_SERIAL_CMD or
                      bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current
  pipeline command -> BIG_LITTLE_PIPELINE_CMD or
                      bash ./session_bootstrap/scripts/run_big_little_pipeline.sh --variant current
EOF
}

resolve_path() {
  local maybe_relative="$1"
  if [[ "$maybe_relative" = /* ]]; then
    printf '%s\n' "$maybe_relative"
  else
    printf '%s\n' "$PROJECT_DIR/$maybe_relative"
  fi
}

parse_last_json_line() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
for raw in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
    line = raw.strip()
    if not line:
        continue
    try:
        payload = json.loads(line)
    except Exception:
        continue
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0)
raise SystemExit(1)
PY
}

render_compare_report() {
  local serial_json_file="$1"
  local pipeline_json_file="$2"
  local report_json="$3"
  local report_md="$4"
  local run_id="$5"
  local env_file="$6"
  local serial_cmd="$7"
  local pipeline_cmd="$8"
  python3 - "$serial_json_file" "$pipeline_json_file" "$report_json" "$report_md" "$run_id" "$env_file" "$serial_cmd" "$pipeline_cmd" <<'PY'
import json
import sys
from pathlib import Path

serial_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
pipeline_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
report_json = Path(sys.argv[3])
report_md = Path(sys.argv[4])
run_id = sys.argv[5]
env_file = sys.argv[6] or None
serial_cmd = sys.argv[7]
pipeline_cmd = sys.argv[8]


def unwrap(payload):
    if isinstance(payload, dict) and "pipeline" in payload:
        return payload["pipeline"]
    return payload


def total_wall_ms(payload):
    core = unwrap(payload)
    if core.get("total_wall_ms") is not None:
        return float(core["total_wall_ms"])
    samples = core.get("run_samples_ms") or []
    load_ms = float(core.get("load_ms") or 0.0)
    vm_init_ms = float(core.get("vm_init_ms") or 0.0)
    return round(load_ms + vm_init_ms + sum(float(value) for value in samples), 3)


def processed_count(payload):
    core = unwrap(payload)
    value = core.get("processed_count")
    if value is None:
        value = core.get("run_count")
    return int(value or 0)


serial_core = unwrap(serial_payload)
pipeline_core = unwrap(pipeline_payload)
serial_total_ms = total_wall_ms(serial_payload)
pipeline_total_ms = total_wall_ms(pipeline_payload)
serial_count = processed_count(serial_payload)
pipeline_count = processed_count(pipeline_payload)
serial_ips = None if serial_total_ms <= 0 or serial_count <= 0 else round(serial_count / (serial_total_ms / 1000.0), 3)
pipeline_ips = None if pipeline_total_ms <= 0 or pipeline_count <= 0 else round(pipeline_count / (pipeline_total_ms / 1000.0), 3)
uplift_pct = None
if serial_ips and pipeline_ips:
    uplift_pct = round(((pipeline_ips / serial_ips) - 1.0) * 100.0, 3)

status = "ok"
if serial_core.get("status", "ok") != "ok" or pipeline_core.get("status", "ok") != "ok":
    status = "error"

payload = {
    "status": status,
    "run_id": run_id,
    "runner": "run_big_little_compare.sh",
    "env_file": env_file,
    "serial_command": serial_cmd,
    "pipeline_command": pipeline_cmd,
    "serial": serial_payload,
    "pipeline": pipeline_payload,
    "comparison": {
        "serial_total_wall_ms": serial_total_ms,
        "pipeline_total_wall_ms": pipeline_total_ms,
        "serial_processed_count": serial_count,
        "pipeline_processed_count": pipeline_count,
        "serial_images_per_sec": serial_ips,
        "pipeline_images_per_sec": pipeline_ips,
        "throughput_uplift_pct": uplift_pct,
    },
}

lines = [
    "# big.LITTLE Compare Report",
    "",
    f"- status: {status}",
    f"- run_id: {run_id}",
    f"- env_file: {env_file}",
    f"- serial_total_wall_ms: {serial_total_ms}",
    f"- pipeline_total_wall_ms: {pipeline_total_ms}",
    f"- serial_images_per_sec: {serial_ips}",
    f"- pipeline_images_per_sec: {pipeline_ips}",
    f"- throughput_uplift_pct: {uplift_pct}",
    "",
    "## Commands",
    "",
    f"- serial: `{serial_cmd}`",
    f"- pipeline: `{pipeline_cmd}`",
]

report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
PY
}

ENV_FILE=""
RUN_ID_OVERRIDE=""
SERIAL_CMD_OVERRIDE=""
PIPELINE_CMD_OVERRIDE=""
ALLOW_OVERWRITE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --run-id)
      RUN_ID_OVERRIDE="${2:-}"
      shift 2
      ;;
    --serial-cmd)
      SERIAL_CMD_OVERRIDE="${2:-}"
      shift 2
      ;;
    --pipeline-cmd)
      PIPELINE_CMD_OVERRIDE="${2:-}"
      shift 2
      ;;
    --allow-overwrite)
      ALLOW_OVERWRITE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -n "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found: $ENV_FILE" >&2
    exit 1
  fi
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

SERIAL_CMD="${SERIAL_CMD_OVERRIDE:-${BIG_LITTLE_SERIAL_CMD:-bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current}}"
PIPELINE_CMD="${PIPELINE_CMD_OVERRIDE:-${BIG_LITTLE_PIPELINE_CMD:-bash ./session_bootstrap/scripts/run_big_little_pipeline.sh --variant current}}"
LOG_DIR_RESOLVED="$(resolve_path "${LOG_DIR:-./session_bootstrap/logs}")"
REPORT_DIR_RESOLVED="$(resolve_path "${REPORT_DIR:-./session_bootstrap/reports}")"
mkdir -p "$LOG_DIR_RESOLVED" "$REPORT_DIR_RESOLVED"

STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_ID="${RUN_ID_OVERRIDE:-big_little_compare_${STAMP}}"
LOG_FILE="$LOG_DIR_RESOLVED/${RUN_ID}.log"
REPORT_JSON="$REPORT_DIR_RESOLVED/${RUN_ID}.json"
REPORT_MD="$REPORT_DIR_RESOLVED/${RUN_ID}.md"
SERIAL_RAW="$REPORT_DIR_RESOLVED/${RUN_ID}.serial.raw.log"
PIPELINE_RAW="$REPORT_DIR_RESOLVED/${RUN_ID}.pipeline.raw.log"

if [[ "$ALLOW_OVERWRITE" != "1" ]]; then
  existing_outputs=()
  [[ -e "$LOG_FILE" ]] && existing_outputs+=("$LOG_FILE")
  [[ -e "$REPORT_JSON" ]] && existing_outputs+=("$REPORT_JSON")
  [[ -e "$REPORT_MD" ]] && existing_outputs+=("$REPORT_MD")
  [[ -e "$SERIAL_RAW" ]] && existing_outputs+=("$SERIAL_RAW")
  [[ -e "$PIPELINE_RAW" ]] && existing_outputs+=("$PIPELINE_RAW")
  if [[ "${#existing_outputs[@]}" -gt 0 ]]; then
    printf 'ERROR: run artifacts already exist for RUN_ID=%s\n' "$RUN_ID" >&2
    printf 'Refusing to overwrite:\n' >&2
    printf '  %s\n' "${existing_outputs[@]}" >&2
    echo "Hint: use --run-id with a fresh value or pass --allow-overwrite." >&2
    exit 1
  fi
fi

{
  echo "[$(date -Iseconds)] big.LITTLE compare started"
  echo "run_id=$RUN_ID"
  echo "env_file=${ENV_FILE:-NA}"
  echo "serial_cmd=$SERIAL_CMD"
  echo "pipeline_cmd=$PIPELINE_CMD"
} >"$LOG_FILE"

SERIAL_JSON_FILE="$(mktemp)"
PIPELINE_JSON_FILE="$(mktemp)"
SERIAL_TMP="$(mktemp)"
PIPELINE_TMP="$(mktemp)"

set +e
bash -lc "cd \"$PROJECT_DIR\" && $SERIAL_CMD" >"$SERIAL_TMP" 2>&1
SERIAL_RC=$?
set -e
cat "$SERIAL_TMP" >>"$SERIAL_RAW"
cat "$SERIAL_TMP" >>"$LOG_FILE"
if ! parse_last_json_line "$SERIAL_TMP" >"$SERIAL_JSON_FILE"; then
  echo "ERROR: failed to parse serial JSON output. See $SERIAL_RAW" >&2
  exit "${SERIAL_RC:-1}"
fi
if [[ "$SERIAL_RC" -ne 0 ]]; then
  echo "ERROR: serial command failed. See $SERIAL_RAW" >&2
  exit "$SERIAL_RC"
fi

set +e
bash -lc "cd \"$PROJECT_DIR\" && $PIPELINE_CMD" >"$PIPELINE_TMP" 2>&1
PIPELINE_RC=$?
set -e
cat "$PIPELINE_TMP" >>"$PIPELINE_RAW"
cat "$PIPELINE_TMP" >>"$LOG_FILE"
if ! parse_last_json_line "$PIPELINE_TMP" >"$PIPELINE_JSON_FILE"; then
  echo "ERROR: failed to parse pipeline JSON output. See $PIPELINE_RAW" >&2
  exit "${PIPELINE_RC:-1}"
fi
if [[ "$PIPELINE_RC" -ne 0 ]]; then
  echo "ERROR: pipeline command failed. See $PIPELINE_RAW" >&2
  exit "$PIPELINE_RC"
fi

COMPARE_STDOUT="$(render_compare_report "$SERIAL_JSON_FILE" "$PIPELINE_JSON_FILE" "$REPORT_JSON" "$REPORT_MD" "$RUN_ID" "${ENV_FILE:-}" "$SERIAL_CMD" "$PIPELINE_CMD")"
printf '%s\n' "$COMPARE_STDOUT"
