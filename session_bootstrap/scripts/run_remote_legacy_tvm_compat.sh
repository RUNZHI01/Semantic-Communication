#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  run_remote_legacy_tvm_compat.sh --variant <baseline|current> [--script <path>]

Notes:
  - Runs the legacy remote JSCC realcmd entry (default: tvm_002.py)
    with a small TVM API compatibility shim for TVM 0.24dev-style runtimes.
  - The main interpreter must be the remote tvm310-style TVM Python.
  - Optional torch dependencies can still be injected through
    REMOTE_TORCH_PYTHONPATH without switching the main interpreter.
  - Emits the original legacy log lines so run_inference_benchmark.sh can
    parse `批量推理时间（1 个样本）: ... 秒` output directly.

Required env:
  REMOTE_MODE=ssh|local
  REMOTE_TVM_PYTHON (or REMOTE_TVM310_PYTHON)
  REMOTE_JSCC_DIR
  REMOTE_INPUT_DIR
  REMOTE_OUTPUT_BASE
  REMOTE_SNR_BASELINE / REMOTE_SNR_CURRENT
  REMOTE_BATCH_BASELINE / REMOTE_BATCH_CURRENT

Optional env:
  REMOTE_TORCH_PYTHONPATH
  REMOTE_LEGACY_EXTRA_PYTHONPATH
  REMOTE_LEGACY_TVM_SCRIPT=tvm_002.py
  REMOTE_BASELINE_ARTIFACT
  REMOTE_CURRENT_ARTIFACT
  INFERENCE_LEGACY_OUTPUT_PREFIX=inference_benchmark
EOF
}

VARIANT=""
LEGACY_SCRIPT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant)
      VARIANT="${2:-}"
      shift 2
      ;;
    --script)
      LEGACY_SCRIPT="${2:-}"
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

if [[ "$VARIANT" != "baseline" && "$VARIANT" != "current" ]]; then
  echo "ERROR: --variant must be baseline or current." >&2
  exit 1
fi

require_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "ERROR: Missing required variable: $var_name" >&2
    exit 1
  fi
}

REMOTE_MODE_RAW="${REMOTE_MODE:-ssh}"
REMOTE_MODE="$(printf '%s' "$REMOTE_MODE_RAW" | tr '[:upper:]' '[:lower:]')"
if [[ "$REMOTE_MODE" != "ssh" && "$REMOTE_MODE" != "local" ]]; then
  echo "ERROR: REMOTE_MODE must be ssh or local (got: $REMOTE_MODE_RAW)" >&2
  exit 1
fi

LEGACY_TVM_PYTHON="${REMOTE_TVM310_PYTHON:-${REMOTE_TVM_PYTHON:-}}"
if [[ -z "$LEGACY_TVM_PYTHON" ]]; then
  echo "ERROR: Missing REMOTE_TVM_PYTHON (or REMOTE_TVM310_PYTHON)." >&2
  exit 1
fi
if [[ "$LEGACY_TVM_PYTHON" == *"/myenv/"* ]]; then
  echo "ERROR: Legacy compat path must use the tvm310-style interpreter as main python, not myenv: $LEGACY_TVM_PYTHON" >&2
  exit 1
fi

for req in REMOTE_JSCC_DIR REMOTE_INPUT_DIR REMOTE_OUTPUT_BASE; do
  require_var "$req"
done

if [[ "$REMOTE_MODE" == "ssh" ]]; then
  for req in REMOTE_HOST REMOTE_USER REMOTE_PASS; do
    require_var "$req"
  done
fi

if [[ "$VARIANT" == "baseline" ]]; then
  require_var REMOTE_SNR_BASELINE
  require_var REMOTE_BATCH_BASELINE
  LEGACY_SNR="$REMOTE_SNR_BASELINE"
  LEGACY_BATCH="$REMOTE_BATCH_BASELINE"
  LEGACY_ARTIFACT="${REMOTE_BASELINE_ARTIFACT:-}"
else
  require_var REMOTE_SNR_CURRENT
  require_var REMOTE_BATCH_CURRENT
  LEGACY_SNR="$REMOTE_SNR_CURRENT"
  LEGACY_BATCH="$REMOTE_BATCH_CURRENT"
  LEGACY_ARTIFACT="${REMOTE_CURRENT_ARTIFACT:-}"
fi

if ! [[ "$LEGACY_BATCH" =~ ^[0-9]+$ ]]; then
  echo "ERROR: batch_size must be a non-negative integer (got: $LEGACY_BATCH)." >&2
  exit 1
fi

LEGACY_SCRIPT="${LEGACY_SCRIPT:-${REMOTE_LEGACY_TVM_SCRIPT:-tvm_002.py}}"
OUTPUT_PREFIX="${INFERENCE_LEGACY_OUTPUT_PREFIX:-inference_benchmark}"
LEGACY_OUTPUT_DIR="$REMOTE_OUTPUT_BASE/${OUTPUT_PREFIX}_${VARIANT}"
LEGACY_EXTRA_PYTHONPATH="${REMOTE_LEGACY_EXTRA_PYTHONPATH:-${REMOTE_TORCH_PYTHONPATH:-}}"

run_legacy_compat() {
  local runner_script
  local rc=0
  runner_script="$(mktemp)"
  {
    cat <<'SH'
#!/usr/bin/env bash
set -euo pipefail
SH
    declare -p REMOTE_JSCC_DIR LEGACY_TVM_PYTHON LEGACY_SCRIPT REMOTE_INPUT_DIR LEGACY_OUTPUT_DIR LEGACY_SNR LEGACY_BATCH LEGACY_EXTRA_PYTHONPATH VARIANT LEGACY_ARTIFACT
    cat <<'SH'

remote_jscc_dir="$REMOTE_JSCC_DIR"
remote_python="$LEGACY_TVM_PYTHON"
legacy_script="$LEGACY_SCRIPT"
input_dir="$REMOTE_INPUT_DIR"
output_dir="$LEGACY_OUTPUT_DIR"
snr="$LEGACY_SNR"
batch_size="$LEGACY_BATCH"
extra_pythonpath="$LEGACY_EXTRA_PYTHONPATH"
variant="$VARIANT"
legacy_artifact="$LEGACY_ARTIFACT"

cd "$remote_jscc_dir"
mkdir -p "$output_dir"

if [[ -n "$extra_pythonpath" ]]; then
  export PYTHONPATH="$extra_pythonpath"
fi
export PYTHONNOUSERSITE=1

run_remote_python() {
  local stdin_payload cmd arg rc=0
  stdin_payload="$(mktemp)"
  cat >"$stdin_payload"
  cmd="$remote_python"
  for arg in "$@"; do
    cmd+=" $(printf '%q' "$arg")"
  done
  set +e
  bash -c "$cmd" <"$stdin_payload"
  rc=$?
  set -e
  rm -f "$stdin_payload"
  return "$rc"
}

artifact_dir="$remote_jscc_dir/tvm_tune_logs"
artifact_target="$artifact_dir/optimized_model.so"
artifact_backup="$artifact_dir/optimized_model.so.__legacy_compat_backup__"
restore_original=0

if [[ -n "$legacy_artifact" ]]; then
  if [[ ! -f "$legacy_artifact" ]]; then
    echo "ERROR: requested artifact for variant=$variant does not exist: $legacy_artifact" >&2
    exit 1
  fi
  mkdir -p "$artifact_dir"
  if [[ "$legacy_artifact" != "$artifact_target" ]]; then
    if [[ -f "$artifact_target" ]]; then
      cp -f "$artifact_target" "$artifact_backup"
      restore_original=1
    fi
    cp -f "$legacy_artifact" "$artifact_target"
  fi
fi

cleanup() {
  if [[ "$restore_original" == "1" && -f "$artifact_backup" ]]; then
    cp -f "$artifact_backup" "$artifact_target"
    rm -f "$artifact_backup"
  fi
}
trap cleanup EXIT

echo "[legacy-compat] variant=$variant script=$legacy_script output_dir=$output_dir snr=$snr batch_size=$batch_size python=$remote_python artifact=${legacy_artifact:-$artifact_target}"

run_remote_python - "$legacy_artifact" <<'PY'
import sys
import traceback

artifact_path = sys.argv[1] if len(sys.argv) > 1 else ""

try:
    import tvm
    from tvm import relax
    runtime = getattr(tvm, "runtime", None)
    runtime_ndarray = getattr(runtime, "ndarray", None)
    if runtime_ndarray is not None and not hasattr(tvm, "nd"):
        tvm.nd = runtime_ndarray
    if runtime is not None and not hasattr(runtime, "tensor") and runtime_ndarray is not None:
        runtime.tensor = lambda arr, dev: runtime_ndarray.array(arr, dev)
    if artifact_path:
        lib = tvm.runtime.load_module(artifact_path)
        dev = tvm.cpu(0)
        relax.VirtualMachine(lib, dev)
        print(f"[legacy-compat] probe_ok artifact={artifact_path} type_key={getattr(lib, 'type_key', 'NA')}")
except Exception:
    print(f"[legacy-compat] probe_failed artifact={artifact_path}", file=sys.stderr)
    traceback.print_exc()
    raise
PY

run_remote_python - "$legacy_script" --input_dir "$input_dir" --output_dir "$output_dir" --snr "$snr" --batch_size "$batch_size" <<'PY'
import runpy
import sys

script_name = sys.argv[1]
script_args = sys.argv[2:]

try:
    import tvm
    runtime = getattr(tvm, "runtime", None)
    runtime_ndarray = getattr(runtime, "ndarray", None)
    if runtime_ndarray is not None and not hasattr(tvm, "nd"):
        tvm.nd = runtime_ndarray
    if runtime is not None and not hasattr(runtime, "tensor") and runtime_ndarray is not None:
        runtime.tensor = lambda arr, dev: runtime_ndarray.array(arr, dev)
except Exception as exc:
    print(f"[compat] warning: failed to expose tvm.nd: {exc}", file=sys.stderr)

sys.argv = [script_name] + script_args
runpy.run_path(script_name, run_name="__main__")
PY
SH
  } >"$runner_script"
  chmod 700 "$runner_script"

  if [[ "$REMOTE_MODE" == "ssh" ]]; then
    set +e
    bash "$SCRIPT_DIR/ssh_with_password.sh" \
      --host "$REMOTE_HOST" \
      --user "$REMOTE_USER" \
      --pass "$REMOTE_PASS" \
      --port "${REMOTE_SSH_PORT:-22}" \
      -- \
      bash -s \
      <"$runner_script"
    rc=$?
    set -e
    rm -f "$runner_script"
    return "$rc"
  fi

  set +e
  bash "$runner_script"
  rc=$?
  set -e
  rm -f "$runner_script"
  return "$rc"
}

run_legacy_compat
