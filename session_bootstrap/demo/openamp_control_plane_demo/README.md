# OpenAMP Control Plane Demo

This package ships a real local dashboard for the current repo state. It is not a disconnected mock: the backend reads the existing OpenAMP evidence package, raw probe JSON, FIT summaries, wrapper evidence, and the trusted-current performance reports that already live under `session_bootstrap/reports/`.

## What it shows

- four-act Chinese-first demo flow: trusted boot -> one-click reconstruction -> formal baseline comparison -> fault injection / recovery
- web-side board credential entry for `host / user / password / port / env_file`, stored only in the current demo-server process and reused for later actions
- board/control-plane status with explicit evidence-backed vs live-probe mode
- key OpenAMP milestones across cold boot, `STATUS_REQ/RESP`, `JOB_REQ/JOB_ACK`, heartbeat, wrapper-backed board smoke, `SAFE_STOP`, and `JOB_DONE`
- final `FIT-01`, `FIT-02`, `FIT-03` state, including `FIT-03` pre-fix FAIL -> post-fix PASS history
- performance positioning for the trusted current SHA aligned to the OpenAMP FIT package
- operator launch commands and source-of-truth document links

## Launch

Default local dashboard:

```bash
bash ./session_bootstrap/scripts/run_openamp_demo.sh
```

Open it at `http://127.0.0.1:8079`.
If that port is still held by an older instance of this same OpenAMP demo server, the launcher will stop it and restart cleanly. If some other service owns the port, the launcher exits with a targeted error instead of killing it.

Optional live board probe wiring:

```bash
bash ./session_bootstrap/scripts/run_openamp_demo.sh \
  --port 8090 \
  --probe-env ./session_bootstrap/config/phytium_pi_login.env
```

The dashboard stays evidence-led either way. The "探测板卡 / OpenAMP" action only runs a read-only SSH probe plus an optional cached RPMsg status query.
If `session_bootstrap/reports/openamp_demo_live_probe_latest.json` already exists, the dashboard loads that saved successful probe on startup and keeps showing it if a later in-dashboard refresh fails.

On startup, the demo now also preloads practical repo-backed defaults when they exist:

- SSH defaults: `session_bootstrap/config/phytium_pi_login.env`, else `session_bootstrap/config/phytium_pi_login.example.env`
- inference defaults for the demo line: `session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env`

Repo-side password fields are ignored intentionally. The operator still enters the password once in the web UI, and the current demo-server process reuses it for later probe / inference / fault actions.

## Web-side credential flow

Open the dashboard and fill the "会话接入" card:

- `主机 / IP`
- `用户名`
- `密码`
- `SSH 端口`
- optional `env 文件`

The password is kept only in memory inside the current demo server process. It is not written back to the repo.
If the startup defaults above were found, the UI prelabels which fields were preloaded and which one is still missing. In the normal repo state, `host / user / port / env_file` are already filled, so only the password must be entered before Current / Baseline attempt live execution.
Later board-facing actions reuse the same in-process session automatically:

- Act 1 board probe
- Act 2 remote reconstruction timing attempt
- Act 3 baseline/current run attempt
- Act 4 RPMsg fault injection / SAFE_STOP recovery

If the board is unreachable or the env file is incomplete for inference, the UI falls back to prerecorded evidence and labels that downgrade explicitly.

## Read-only board probe

Standalone CLI:

```bash
python3 ./session_bootstrap/scripts/probe_openamp_board_status.py \
  --env ./session_bootstrap/config/phytium_pi_login.env
```

Default output:

- `session_bootstrap/reports/openamp_demo_live_probe_latest.json`

The probe only reads:

- hostname / user
- `/sys/class/remoteproc/remoteproc*/state`
- `/dev/rpmsg*`
- RPMsg channel names under `/sys/bus/rpmsg/devices/*/name`
- `/lib/firmware/openamp_core0.elf` size and SHA256

It does not reboot the board, does not send `JOB_REQ`, and does not modify firmware/runtime state.

## Host and slave side scope

Host side inputs:

- `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/`
- raw board probes such as `openamp_job_done_real_probe_20260315_001.json`
- FIT bundles under `openamp_*_fit_*`
- `session_bootstrap/scripts/openamp_control_wrapper.py`
- `session_bootstrap/scripts/openamp_rpmsg_bridge.py`
- trusted-current performance reports for SHA `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`

Slave/OpenAMP side assumptions:

- the board remains on the already prepared OpenAMP path
- RPMsg transport and remoteproc state are the ones validated in the existing evidence package
- the final post-fix firmware SHA in the dashboard comes from the board-backed `FIT-03` PASS bundle

## Local verification

Recommended checks:

```bash
python3 -m unittest discover -s ./session_bootstrap/demo/openamp_control_plane_demo/tests -p 'test_*.py'
bash ./session_bootstrap/scripts/run_openamp_demo.sh --port 8079
```

## Regression coverage snapshot

The current demo regression suite covers these public/operator-facing surfaces:

- snapshot construction in `demo_data.build_snapshot()`, including final FIT verdicts, trusted-current performance alignment, live-probe mode switching, and saved-probe labeling
- HTTP smoke coverage for `GET /api/snapshot`, `GET /api/system-status`, `POST /api/session/board-access`, `POST /api/probe-board`, `POST /api/run-inference`, `POST /api/inject-fault`, `GET /docs?path=...`, `GET /api/health`, `GET /`, `GET /app.js`, and `GET /app.css`
- localhost socket smoke coverage for `GET /api/health` that boots `DemoHTTPServer` on an ephemeral port, hits the real bound endpoint once, and shuts down cleanly when the runtime permits local socket creation
- live-probe cache behavior: startup reuse of the last successful probe artifact and preservation of that saved probe when a later refresh fails
- session credential behavior: redacted public payloads, probe reuse of saved credentials, and fallback/live inference API payload shaping
- docs endpoint guardrails for missing path, invalid repo-external path, missing file, and JSON pretty-print rendering
- direct `board_probe` unit coverage for command construction, cache helpers, and execution outcomes: password-auth SSH selection, `REMOTE_SSH_PORT` override handling, `connect_phytium_pi.sh --env ...` fallback, dedicated `load_probe_output()` checks for missing, malformed, and valid-non-dict JSON, `write_probe_output()` success-and-write-failure paths, and `run_live_probe()` success, timeout, launch/configuration failure, non-zero exit, and JSON parse-error payload shaping
- `server.main()` bootstrap coverage for both normal startup and `--probe-startup`, including `DashboardState` construction, startup probe ordering, `DemoHTTPServer` wiring, and the printed launch banner without binding a real socket

Intentional gaps and next-optional coverage:

- optional extra `board_probe` unit coverage would now be limited to rarer platform-specific shell/permission anomalies beyond the current command-construction, cache-helper, launch-failure, and result-shaping paths
- the frontend is covered as served assets only; there is no browser-level regression for DOM rendering or the in-page refresh flow
- the localhost socket smoke skips explicitly when the runtime forbids socket creation, so heavily sandboxed environments still will not exercise bind/listen despite the test existing
