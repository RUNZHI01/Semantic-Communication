#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  run_transpose_add6_remote_payload_benchmark.sh \
    --inference-env <env_file> \
    --local-artifact <path/to/fused_conv2d_transpose_add6_post_db_swap.so> \
    [--database-dir <tuning_logs_dir>] \
    [--remote-archive-dir <remote archive>] \
    [--report-id <id>]

This helper stays narrow and operator-specific:
- it stages a local transpose_add6 handwritten artifact into a dedicated remote archive
- it optionally mirrors the frozen DB JSON files into that archive
- it then runs the existing run_remote_tvm_inference_payload.sh current-path benchmark
- all remote actions go through the repository ssh_with_password.sh helper
EOF
}

INFERENCE_ENV=""
LOCAL_ARTIFACT=""
DATABASE_DIR=""
REMOTE_ARCHIVE_DIR="/home/user/Downloads/jscc-test/jscc_staging_handwritten_fused_conv2d_transpose_add6"
REPORT_ID="transpose_add6_remote_payload_$(date +%Y%m%d_%H%M%S)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --inference-env)
      INFERENCE_ENV="${2:-}"
      shift 2
      ;;
    --local-artifact)
      LOCAL_ARTIFACT="${2:-}"
      shift 2
      ;;
    --database-dir)
      DATABASE_DIR="${2:-}"
      shift 2
      ;;
    --remote-archive-dir)
      REMOTE_ARCHIVE_DIR="${2:-}"
      shift 2
      ;;
    --report-id)
      REPORT_ID="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$INFERENCE_ENV" || -z "$LOCAL_ARTIFACT" ]]; then
  echo "ERROR: --inference-env and --local-artifact are required." >&2
  usage >&2
  exit 1
fi

# shellcheck source=/dev/null
set -a
source "$INFERENCE_ENV"
set +a

for req in REMOTE_HOST REMOTE_USER REMOTE_PASS; do
  if [[ -z "${!req:-}" ]]; then
    echo "ERROR: missing required variable from env: $req" >&2
    exit 1
  fi
done

if [[ ! -f "$LOCAL_ARTIFACT" ]]; then
  echo "ERROR: local artifact not found: $LOCAL_ARTIFACT" >&2
  exit 1
fi

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\''/g")"
}

remote_exec() {
  bash "$SCRIPT_DIR/ssh_with_password.sh" \
    --host "$REMOTE_HOST" \
    --user "$REMOTE_USER" \
    --pass "$REMOTE_PASS" \
    -- "$1"
}

copy_remote_file() {
  local src="$1"
  local dst="$2"
  remote_exec "mkdir -p $(shell_quote "$(dirname "$dst")")"
  bash "$SCRIPT_DIR/ssh_with_password.sh" \
    --host "$REMOTE_HOST" \
    --user "$REMOTE_USER" \
    --pass "$REMOTE_PASS" \
    -- "cat > $(shell_quote "$dst")" <"$src"
}

REMOTE_SO="$REMOTE_ARCHIVE_DIR/tvm_tune_logs/optimized_model.so"
copy_remote_file "$LOCAL_ARTIFACT" "$REMOTE_SO"

if [[ -n "$DATABASE_DIR" ]]; then
  if [[ ! -f "$DATABASE_DIR/database_workload.json" || ! -f "$DATABASE_DIR/database_tuning_record.json" ]]; then
    echo "ERROR: database dir missing required JSON files: $DATABASE_DIR" >&2
    exit 1
  fi
  copy_remote_file "$DATABASE_DIR/database_workload.json" "$REMOTE_ARCHIVE_DIR/tuning_logs/database_workload.json"
  copy_remote_file "$DATABASE_DIR/database_tuning_record.json" "$REMOTE_ARCHIVE_DIR/tuning_logs/database_tuning_record.json"
fi

LOCAL_SHA="$(sha256sum "$LOCAL_ARTIFACT" | awk '{print $1}')"
REMOTE_SHA="$(remote_exec "sha256sum $(shell_quote "$REMOTE_SO") | awk '{print \$1}'")"

if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: local/remote sha mismatch: local=$LOCAL_SHA remote=$REMOTE_SHA" >&2
  exit 1
fi

export INFERENCE_CURRENT_ARCHIVE="$REMOTE_ARCHIVE_DIR"
export REMOTE_TVM_JSCC_BASE_DIR="$REMOTE_ARCHIVE_DIR"
export INFERENCE_CURRENT_EXPECTED_SHA256="$LOCAL_SHA"
export INFERENCE_EXECUTION_ID="$REPORT_ID"

BENCH_JSON="$(bash "$SCRIPT_DIR/run_remote_tvm_inference_payload.sh" --variant current)"

printf '%s\n' "$BENCH_JSON"
