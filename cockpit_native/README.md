# cockpit_native

PySide6-first native cockpit prototype for the existing TVM/OpenAMP demo contracts.

Smoke/import check without PySide6:

```bash
python3 -m cockpit_native --smoke-import-check
```

Dump the normalized UI state:

```bash
python3 -m cockpit_native --dump-ui-state
```

Launch the adaptive QML shell when `PySide6` is installed:

```bash
python3 -m cockpit_native
```

Project-local operator launcher:

```bash
bash ./session_bootstrap/scripts/run_cockpit_native.sh
```

The launcher now supervises the Qt process and retries once with software rendering if the first GPU-backed launch exits early.

Force software rendering from the start:

```bash
python3 -m cockpit_native --software-render
```
