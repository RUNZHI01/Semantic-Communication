#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COCKPIT_ROOT="$PROJECT_ROOT/cockpit_native"
VENV_PYTHON="$COCKPIT_ROOT/.venv/bin/python"
RUNTIME_CACHE_ROOT="$COCKPIT_ROOT/runtime/xdg_cache"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Missing native cockpit venv interpreter: $VENV_PYTHON" >&2
    echo "Expected repo-local launcher path: $PROJECT_ROOT/session_bootstrap/scripts/run_cockpit_native.sh" >&2
    exit 1
fi

mkdir -p "$RUNTIME_CACHE_ROOT"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$RUNTIME_CACHE_ROOT}"
export QT_QUICK_BACKEND="${QT_QUICK_BACKEND:-software}"
export QSG_RHI_BACKEND="${QSG_RHI_BACKEND:-software}"
export QT_OPENGL="${QT_OPENGL:-software}"

cd "$PROJECT_ROOT"
exec "$VENV_PYTHON" -m cockpit_native --software-render "$@"
