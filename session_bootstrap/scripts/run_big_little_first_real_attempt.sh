#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$SESSION_DIR/.." && pwd)"

ENV_FILE="${1:-$PROJECT_DIR/session_bootstrap/config/big_little_pipeline.current.2026-03-18.phytium_pi.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

cd "$PROJECT_DIR"

echo "=== [1/3] read-only topology probe ==="
python3 ./session_bootstrap/scripts/big_little_topology_probe.py ssh \
  --env "$ENV_FILE" \
  --write-raw ./session_bootstrap/reports/big_little_topology_capture_latest.txt

echo
echo "=== [2/3] current big.LITTLE pipeline run ==="
bash ./session_bootstrap/scripts/run_big_little_pipeline.sh \
  --env "$ENV_FILE" \
  --variant current

echo
echo "=== [3/3] serial vs pipeline compare ==="
bash ./session_bootstrap/scripts/run_big_little_compare.sh \
  --env "$ENV_FILE"

echo
echo "Done. Check session_bootstrap/reports/big_little_pipeline_* and big_little_compare_*"
