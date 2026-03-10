#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$SESSION_DIR/.." && pwd)"
DEFAULT_ENV_FILE="$SESSION_DIR/config/local.env"

usage() {
  cat <<'EOF'
Usage:
  run_inference_benchmark.sh [--env <path>]

Notes:
  - Safe remote inference benchmark:
      load_module() once -> VM init once -> warmup -> repeated inference runs
  - Default commands:
      baseline -> run_remote_tvm_inference_payload.sh --variant baseline
      current  -> run_remote_tvm_inference_payload.sh --variant current
  - Optional vars:
      INFERENCE_BASELINE_CMD, INFERENCE_CURRENT_CMD
      INFERENCE_REPEAT, INFERENCE_WARMUP_RUNS, INFERENCE_TIMEOUT_SEC
      INFERENCE_BASELINE_ARCHIVE, INFERENCE_CURRENT_ARCHIVE
      INFERENCE_CURRENT_EXPECTED_SHA256
      EXECUTION_ID, INFERENCE_EXECUTION_ID, LOG_DIR, REPORT_DIR
      ALLOW_REPORT_OVERWRITE=1
EOF
}

ENV_FILE="$DEFAULT_ENV_FILE"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --env requires a file path." >&2
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
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

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Hint: copy $SESSION_DIR/config/local.example to $SESSION_DIR/config/local.env" >&2
  exit 1
fi

# shellcheck source=/dev/null
set -a
source "$ENV_FILE"
set +a

resolve_path() {
  local maybe_relative="$1"
  if [[ "$maybe_relative" = /* ]]; then
    printf '%s\n' "$maybe_relative"
  else
    printf '%s\n' "$PROJECT_DIR/$maybe_relative"
  fi
}

require_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "ERROR: Missing required variable: $var_name" >&2
    exit 1
  fi
}

require_var MODEL_NAME
require_var TARGET
require_var SHAPE_BUCKETS
require_var TUNE_INPUT_SHAPE
require_var TUNE_INPUT_DTYPE

THREADS="${THREADS:-unknown}"
INFERENCE_TIMEOUT_SEC="${INFERENCE_TIMEOUT_SEC:-900}"
INFERENCE_REPEAT="${INFERENCE_REPEAT:-5}"
INFERENCE_WARMUP_RUNS="${INFERENCE_WARMUP_RUNS:-1}"
INFERENCE_BASELINE_CMD="${INFERENCE_BASELINE_CMD:-bash ./session_bootstrap/scripts/run_remote_tvm_inference_payload.sh --variant baseline}"
INFERENCE_CURRENT_CMD="${INFERENCE_CURRENT_CMD:-bash ./session_bootstrap/scripts/run_remote_tvm_inference_payload.sh --variant current}"
LOG_DIR_RESOLVED="$(resolve_path "${LOG_DIR:-./session_bootstrap/logs}")"
REPORT_DIR_RESOLVED="$(resolve_path "${REPORT_DIR:-./session_bootstrap/reports}")"

if ! [[ "$INFERENCE_TIMEOUT_SEC" =~ ^[0-9]+$ ]]; then
  echo "ERROR: INFERENCE_TIMEOUT_SEC must be a non-negative integer." >&2
  exit 1
fi
if ! [[ "$INFERENCE_REPEAT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: INFERENCE_REPEAT must be a non-negative integer." >&2
  exit 1
fi
if ! [[ "$INFERENCE_WARMUP_RUNS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: INFERENCE_WARMUP_RUNS must be a non-negative integer." >&2
  exit 1
fi
if [[ "$INFERENCE_TIMEOUT_SEC" -gt 0 ]] && ! command -v timeout >/dev/null 2>&1; then
  echo "ERROR: timeout command not found but INFERENCE_TIMEOUT_SEC is set." >&2
  exit 1
fi

mkdir -p "$LOG_DIR_RESOLVED" "$REPORT_DIR_RESOLVED"

STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_ID="${INFERENCE_EXECUTION_ID:-${EXECUTION_ID:-inference_${STAMP}}}"
ALLOW_REPORT_OVERWRITE="${ALLOW_REPORT_OVERWRITE:-0}"
LOG_FILE="$LOG_DIR_RESOLVED/${RUN_ID}.log"
RAW_CSV_FILE="$REPORT_DIR_RESOLVED/${RUN_ID}_raw.csv"
REPORT_FILE="$REPORT_DIR_RESOLVED/${RUN_ID}.md"

if [[ "$ALLOW_REPORT_OVERWRITE" != "1" ]]; then
  existing_outputs=()
  [[ -e "$LOG_FILE" ]] && existing_outputs+=("$LOG_FILE")
  [[ -e "$RAW_CSV_FILE" ]] && existing_outputs+=("$RAW_CSV_FILE")
  [[ -e "$REPORT_FILE" ]] && existing_outputs+=("$REPORT_FILE")
  if [[ "${#existing_outputs[@]}" -gt 0 ]]; then
    printf 'ERROR: run artifacts already exist for RUN_ID=%s\n' "$RUN_ID" >&2
    printf 'Refusing to overwrite:%s\n' "" >&2
    printf '  %s\n' "${existing_outputs[@]}" >&2
    echo "Hint: set a new INFERENCE_EXECUTION_ID/EXECUTION_ID or export ALLOW_REPORT_OVERWRITE=1 to overwrite intentionally." >&2
    exit 1
  fi
fi

cat >"$RAW_CSV_FILE" <<'EOF'
mode,load_ms,vm_init_ms,run_median_ms,run_mean_ms,run_min_ms,run_max_ms,run_variance_ms2,run_count,exit_code,start_at,end_at
EOF

{
  echo "[$(date -Iseconds)] inference benchmark started"
  echo "run_id=$RUN_ID"
  echo "model_name=$MODEL_NAME"
  echo "target=$TARGET"
  echo "shape_buckets=$SHAPE_BUCKETS"
  echo "threads=$THREADS"
  echo "env_file=$ENV_FILE"
  echo "input_shape=$TUNE_INPUT_SHAPE"
  echo "input_dtype=$TUNE_INPUT_DTYPE"
  echo "inference_repeat=$INFERENCE_REPEAT"
  echo "inference_warmup_runs=$INFERENCE_WARMUP_RUNS"
  echo "inference_timeout_sec=$INFERENCE_TIMEOUT_SEC"
  echo "baseline_cmd=$INFERENCE_BASELINE_CMD"
  echo "current_cmd=$INFERENCE_CURRENT_CMD"
  echo "current_expected_sha256=${INFERENCE_CURRENT_EXPECTED_SHA256:-NA}"
} >"$LOG_FILE"

LAST_EXIT_CODE=0
LAST_LOAD_MS="NA"
LAST_VM_INIT_MS="NA"
LAST_RUN_MEDIAN_MS="NA"
LAST_RUN_MEAN_MS="NA"
LAST_RUN_MIN_MS="NA"
LAST_RUN_MAX_MS="NA"
LAST_RUN_VARIANCE_MS2="NA"
LAST_RUN_COUNT="0"
LAST_OUTPUT_SHAPE="NA"
LAST_OUTPUT_DTYPE="NA"
LAST_ARTIFACT_PATH="NA"
LAST_ARTIFACT_SHA256="NA"
LAST_ARTIFACT_SHA256_EXPECTED="NA"
LAST_ARTIFACT_SHA256_MATCH="NA"
LAST_ERROR=""

parse_last_json_line() {
  python3 - "$1" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    lines = [line.strip() for line in f if line.strip()]
for line in reversed(lines):
    try:
        obj = json.loads(line)
    except Exception:
        continue
    print(json.dumps(obj, ensure_ascii=False))
    raise SystemExit(0)
raise SystemExit(1)
PY
}

parse_legacy_latency_lines() {
  python3 - "$1" <<'PY'
import json, re, statistics, sys
path = sys.argv[1]
patterns = [
    re.compile(r'批量推理时间.*?:\s*([0-9]+(?:\.[0-9]+)?)\s*秒'),
    re.compile(r'batch\s+infer(?:ence)?\s+time.*?:\s*([0-9]+(?:\.[0-9]+)?)\s*s(?:ec(?:onds?)?)?', re.I),
]
vals = []
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    for raw in f:
        line = raw.strip()
        for pattern in patterns:
            m = pattern.search(line)
            if m:
                vals.append(float(m.group(1)) * 1000.0)
                break
if not vals:
    raise SystemExit(1)
payload = {
    'load_ms': 'NA',
    'vm_init_ms': 'NA',
    'run_median_ms': round(statistics.median(vals), 3),
    'run_mean_ms': round(sum(vals) / len(vals), 3),
    'run_min_ms': round(min(vals), 3),
    'run_max_ms': round(max(vals), 3),
    'run_variance_ms2': round(statistics.pvariance(vals) if len(vals) > 1 else 0.0, 6),
    'run_count': len(vals),
    'output_shape': 'NA',
    'output_dtype': 'NA',
    'parser': 'legacy_latency_lines',
}
print(json.dumps(payload, ensure_ascii=False))
PY
}

json_field() {
  python3 - "$1" "$2" <<'PY'
import json, sys
obj = json.loads(sys.argv[1])
field = sys.argv[2]
val = obj.get(field, 'NA')
if isinstance(val, list):
    print(json.dumps(val, ensure_ascii=False))
elif val is None:
    print('NA')
else:
    print(val)
PY
}

run_once() {
  local mode="$1"
  local cmd="$2"
  local tmp_out start_at end_at payload_json rc

  tmp_out="$(mktemp)"
  start_at="$(date -Iseconds)"
  echo "[$start_at] mode=$mode cmd=$cmd" >>"$LOG_FILE"

  set +e
  if [[ "$INFERENCE_TIMEOUT_SEC" -gt 0 ]]; then
    timeout "$INFERENCE_TIMEOUT_SEC" bash -lc "cd \"$PROJECT_DIR\" && $cmd" >"$tmp_out" 2>&1
  else
    bash -lc "cd \"$PROJECT_DIR\" && $cmd" >"$tmp_out" 2>&1
  fi
  rc=$?
  set -e

  cat "$tmp_out" >>"$LOG_FILE"
  end_at="$(date -Iseconds)"

  LAST_EXIT_CODE="$rc"
  LAST_LOAD_MS="NA"
  LAST_VM_INIT_MS="NA"
  LAST_RUN_MEDIAN_MS="NA"
  LAST_RUN_MEAN_MS="NA"
  LAST_RUN_MIN_MS="NA"
  LAST_RUN_MAX_MS="NA"
  LAST_RUN_VARIANCE_MS2="NA"
  LAST_RUN_COUNT="0"
  LAST_OUTPUT_SHAPE="NA"
  LAST_OUTPUT_DTYPE="NA"
  LAST_ARTIFACT_PATH="NA"
  LAST_ARTIFACT_SHA256="NA"
  LAST_ARTIFACT_SHA256_EXPECTED="NA"
  LAST_ARTIFACT_SHA256_MATCH="NA"
  LAST_ERROR=""

  if [[ "$rc" -eq 0 ]]; then
    if payload_json="$(parse_last_json_line "$tmp_out")"; then
      LAST_ERROR="json_payload"
    elif payload_json="$(parse_legacy_latency_lines "$tmp_out")"; then
      LAST_ERROR="legacy_latency_payload"
    else
      LAST_EXIT_CODE=1
      LAST_ERROR="missing_json_payload"
      payload_json=""
    fi

    if [[ -n "$payload_json" ]]; then
      LAST_LOAD_MS="$(json_field "$payload_json" load_ms)"
      LAST_VM_INIT_MS="$(json_field "$payload_json" vm_init_ms)"
      LAST_RUN_MEDIAN_MS="$(json_field "$payload_json" run_median_ms)"
      LAST_RUN_MEAN_MS="$(json_field "$payload_json" run_mean_ms)"
      LAST_RUN_MIN_MS="$(json_field "$payload_json" run_min_ms)"
      LAST_RUN_MAX_MS="$(json_field "$payload_json" run_max_ms)"
      LAST_RUN_VARIANCE_MS2="$(json_field "$payload_json" run_variance_ms2)"
      LAST_RUN_COUNT="$(json_field "$payload_json" run_count)"
      LAST_OUTPUT_SHAPE="$(json_field "$payload_json" output_shape)"
      LAST_OUTPUT_DTYPE="$(json_field "$payload_json" output_dtype)"
      LAST_ARTIFACT_PATH="$(json_field "$payload_json" artifact_path)"
      LAST_ARTIFACT_SHA256="$(json_field "$payload_json" artifact_sha256)"
      LAST_ARTIFACT_SHA256_EXPECTED="$(json_field "$payload_json" artifact_sha256_expected)"
      LAST_ARTIFACT_SHA256_MATCH="$(json_field "$payload_json" artifact_sha256_match)"
    fi
  else
    LAST_ERROR="command_failed"
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$mode" "$LAST_LOAD_MS" "$LAST_VM_INIT_MS" "$LAST_RUN_MEDIAN_MS" "$LAST_RUN_MEAN_MS" \
    "$LAST_RUN_MIN_MS" "$LAST_RUN_MAX_MS" "$LAST_RUN_VARIANCE_MS2" "$LAST_RUN_COUNT" \
    "$LAST_EXIT_CODE" "$start_at" "$end_at" >>"$RAW_CSV_FILE"

  echo "[$end_at] mode=$mode exit_code=$LAST_EXIT_CODE load_ms=$LAST_LOAD_MS vm_init_ms=$LAST_VM_INIT_MS run_median_ms=$LAST_RUN_MEDIAN_MS run_count=$LAST_RUN_COUNT output_shape=$LAST_OUTPUT_SHAPE output_dtype=$LAST_OUTPUT_DTYPE artifact_path=$LAST_ARTIFACT_PATH artifact_sha256=$LAST_ARTIFACT_SHA256 artifact_sha256_expected=$LAST_ARTIFACT_SHA256_EXPECTED artifact_sha256_match=$LAST_ARTIFACT_SHA256_MATCH error=${LAST_ERROR:-NA}" >>"$LOG_FILE"
  rm -f "$tmp_out"
  return "$LAST_EXIT_CODE"
}

write_report() {
  local status="$1"
  local baseline_load_ms="$2"
  local baseline_vm_init_ms="$3"
  local baseline_run_median_ms="$4"
  local baseline_run_mean_ms="$5"
  local baseline_run_min_ms="$6"
  local baseline_run_max_ms="$7"
  local baseline_run_variance_ms2="$8"
  local baseline_run_count="$9"
  local baseline_exit_code="${10}"
  local baseline_output_shape="${11}"
  local baseline_output_dtype="${12}"
  local current_load_ms="${13}"
  local current_vm_init_ms="${14}"
  local current_run_median_ms="${15}"
  local current_run_mean_ms="${16}"
  local current_run_min_ms="${17}"
  local current_run_max_ms="${18}"
  local current_run_variance_ms2="${19}"
  local current_run_count="${20}"
  local current_exit_code="${21}"
  local current_output_shape="${22}"
  local current_output_dtype="${23}"
  local delta_ms="${24}"
  local improvement_pct="${25}"

  cat >"$REPORT_FILE" <<EOF
# Inference Benchmark Report

- execution_id: $RUN_ID
- mode: inference_benchmark
- status: $status
- timestamp: $(date -Iseconds)
- env_file: $ENV_FILE
- model_name: $MODEL_NAME
- target: $TARGET
- shape_buckets: $SHAPE_BUCKETS
- threads: $THREADS
- input_shape: $TUNE_INPUT_SHAPE
- input_dtype: $TUNE_INPUT_DTYPE
- inference_repeat: $INFERENCE_REPEAT
- inference_warmup_runs: $INFERENCE_WARMUP_RUNS
- inference_timeout_sec: $INFERENCE_TIMEOUT_SEC
- current_expected_sha256_configured: ${INFERENCE_CURRENT_EXPECTED_SHA256:-NA}
- baseline_load_ms: $baseline_load_ms
- baseline_vm_init_ms: $baseline_vm_init_ms
- baseline_run_median_ms: $baseline_run_median_ms
- baseline_run_mean_ms: $baseline_run_mean_ms
- baseline_run_min_ms: $baseline_run_min_ms
- baseline_run_max_ms: $baseline_run_max_ms
- baseline_run_variance_ms2: $baseline_run_variance_ms2
- baseline_run_count: $baseline_run_count
- baseline_exit_code: $baseline_exit_code
- baseline_output_shape: $baseline_output_shape
- baseline_output_dtype: $baseline_output_dtype
- baseline_artifact_path: $baseline_artifact_path
- baseline_artifact_sha256: $baseline_artifact_sha256
- baseline_artifact_sha256_expected: $baseline_artifact_sha256_expected
- baseline_artifact_sha256_match: $baseline_artifact_sha256_match
- current_load_ms: $current_load_ms
- current_vm_init_ms: $current_vm_init_ms
- current_run_median_ms: $current_run_median_ms
- current_run_mean_ms: $current_run_mean_ms
- current_run_min_ms: $current_run_min_ms
- current_run_max_ms: $current_run_max_ms
- current_run_variance_ms2: $current_run_variance_ms2
- current_run_count: $current_run_count
- current_exit_code: $current_exit_code
- current_output_shape: $current_output_shape
- current_output_dtype: $current_output_dtype
- current_artifact_path: $current_artifact_path
- current_artifact_sha256: $current_artifact_sha256
- current_artifact_sha256_expected: $current_artifact_sha256_expected
- current_artifact_sha256_match: $current_artifact_sha256_match
- delta_ms_current_minus_baseline: $delta_ms
- improvement_pct: $improvement_pct

## Commands

- baseline_cmd: $INFERENCE_BASELINE_CMD
- current_cmd: $INFERENCE_CURRENT_CMD

## Artifacts

- log_file: $LOG_FILE
- raw_csv_file: $RAW_CSV_FILE
EOF
}

baseline_load_ms="NA"
baseline_vm_init_ms="NA"
baseline_run_median_ms="NA"
baseline_run_mean_ms="NA"
baseline_run_min_ms="NA"
baseline_run_max_ms="NA"
baseline_run_variance_ms2="NA"
baseline_run_count="0"
baseline_exit_code="NA"
baseline_output_shape="NA"
baseline_output_dtype="NA"
baseline_artifact_path="NA"
baseline_artifact_sha256="NA"
baseline_artifact_sha256_expected="NA"
baseline_artifact_sha256_match="NA"

current_load_ms="NA"
current_vm_init_ms="NA"
current_run_median_ms="NA"
current_run_mean_ms="NA"
current_run_min_ms="NA"
current_run_max_ms="NA"
current_run_variance_ms2="NA"
current_run_count="0"
current_exit_code="NA"
current_output_shape="NA"
current_output_dtype="NA"
current_artifact_path="NA"
current_artifact_sha256="NA"
current_artifact_sha256_expected="NA"
current_artifact_sha256_match="NA"

delta_ms="NA"
improvement_pct="NA"

if run_once baseline "$INFERENCE_BASELINE_CMD"; then
  baseline_load_ms="$LAST_LOAD_MS"
  baseline_vm_init_ms="$LAST_VM_INIT_MS"
  baseline_run_median_ms="$LAST_RUN_MEDIAN_MS"
  baseline_run_mean_ms="$LAST_RUN_MEAN_MS"
  baseline_run_min_ms="$LAST_RUN_MIN_MS"
  baseline_run_max_ms="$LAST_RUN_MAX_MS"
  baseline_run_variance_ms2="$LAST_RUN_VARIANCE_MS2"
  baseline_run_count="$LAST_RUN_COUNT"
  baseline_exit_code="$LAST_EXIT_CODE"
  baseline_output_shape="$LAST_OUTPUT_SHAPE"
  baseline_output_dtype="$LAST_OUTPUT_DTYPE"
  baseline_artifact_path="$LAST_ARTIFACT_PATH"
  baseline_artifact_sha256="$LAST_ARTIFACT_SHA256"
  baseline_artifact_sha256_expected="$LAST_ARTIFACT_SHA256_EXPECTED"
  baseline_artifact_sha256_match="$LAST_ARTIFACT_SHA256_MATCH"
else
  baseline_exit_code="$LAST_EXIT_CODE"
  write_report "failed_baseline" "$baseline_load_ms" "$baseline_vm_init_ms" "$baseline_run_median_ms" "$baseline_run_mean_ms" "$baseline_run_min_ms" "$baseline_run_max_ms" "$baseline_run_variance_ms2" "$baseline_run_count" "$baseline_exit_code" "$baseline_output_shape" "$baseline_output_dtype" "$current_load_ms" "$current_vm_init_ms" "$current_run_median_ms" "$current_run_mean_ms" "$current_run_min_ms" "$current_run_max_ms" "$current_run_variance_ms2" "$current_run_count" "$current_exit_code" "$current_output_shape" "$current_output_dtype" "$delta_ms" "$improvement_pct"
  echo "Inference benchmark failed in baseline stage"
  echo "  report: $REPORT_FILE"
  echo "  log:    $LOG_FILE"
  exit "$baseline_exit_code"
fi

if run_once current "$INFERENCE_CURRENT_CMD"; then
  current_load_ms="$LAST_LOAD_MS"
  current_vm_init_ms="$LAST_VM_INIT_MS"
  current_run_median_ms="$LAST_RUN_MEDIAN_MS"
  current_run_mean_ms="$LAST_RUN_MEAN_MS"
  current_run_min_ms="$LAST_RUN_MIN_MS"
  current_run_max_ms="$LAST_RUN_MAX_MS"
  current_run_variance_ms2="$LAST_RUN_VARIANCE_MS2"
  current_run_count="$LAST_RUN_COUNT"
  current_exit_code="$LAST_EXIT_CODE"
  current_output_shape="$LAST_OUTPUT_SHAPE"
  current_output_dtype="$LAST_OUTPUT_DTYPE"
  current_artifact_path="$LAST_ARTIFACT_PATH"
  current_artifact_sha256="$LAST_ARTIFACT_SHA256"
  current_artifact_sha256_expected="$LAST_ARTIFACT_SHA256_EXPECTED"
  current_artifact_sha256_match="$LAST_ARTIFACT_SHA256_MATCH"
else
  current_exit_code="$LAST_EXIT_CODE"
  write_report "failed_current" "$baseline_load_ms" "$baseline_vm_init_ms" "$baseline_run_median_ms" "$baseline_run_mean_ms" "$baseline_run_min_ms" "$baseline_run_max_ms" "$baseline_run_variance_ms2" "$baseline_run_count" "$baseline_exit_code" "$baseline_output_shape" "$baseline_output_dtype" "$current_load_ms" "$current_vm_init_ms" "$current_run_median_ms" "$current_run_mean_ms" "$current_run_min_ms" "$current_run_max_ms" "$current_run_variance_ms2" "$current_run_count" "$current_exit_code" "$current_output_shape" "$current_output_dtype" "$delta_ms" "$improvement_pct"
  echo "Inference benchmark failed in current stage"
  echo "  report: $REPORT_FILE"
  echo "  log:    $LOG_FILE"
  exit "$current_exit_code"
fi

delta_ms="$(awk -v b="$baseline_run_median_ms" -v c="$current_run_median_ms" 'BEGIN { printf "%.3f", c - b }')"
improvement_pct="$(awk -v b="$baseline_run_median_ms" -v c="$current_run_median_ms" 'BEGIN { if (b == 0) { printf "0.00" } else { printf "%.2f", ((b - c) / b) * 100 } }')"

write_report "success" "$baseline_load_ms" "$baseline_vm_init_ms" "$baseline_run_median_ms" "$baseline_run_mean_ms" "$baseline_run_min_ms" "$baseline_run_max_ms" "$baseline_run_variance_ms2" "$baseline_run_count" "$baseline_exit_code" "$baseline_output_shape" "$baseline_output_dtype" "$current_load_ms" "$current_vm_init_ms" "$current_run_median_ms" "$current_run_mean_ms" "$current_run_min_ms" "$current_run_max_ms" "$current_run_variance_ms2" "$current_run_count" "$current_exit_code" "$current_output_shape" "$current_output_dtype" "$delta_ms" "$improvement_pct"

echo "Inference benchmark completed"
echo "  report: $REPORT_FILE"
echo "  log:    $LOG_FILE"
