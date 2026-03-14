#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVER="$PROJECT_ROOT/session_bootstrap/demo/openamp_control_plane_demo/server.py"

exec python3 "$SERVER" "$@"
