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

Launch the QML shell when `PySide6` is installed:

```bash
python3 -m cockpit_native
```
