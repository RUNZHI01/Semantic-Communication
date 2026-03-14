# OpenAMP Control Plane Demo

This package ships a real local dashboard for the current repo state. It is not a disconnected mock: the backend reads the existing OpenAMP evidence package, raw probe JSON, FIT summaries, wrapper evidence, and the trusted-current performance reports that already live under `session_bootstrap/reports/`.

## What it shows

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

Optional live board probe wiring:

```bash
bash ./session_bootstrap/scripts/run_openamp_demo.sh \
  --port 8090 \
  --probe-env ./session_bootstrap/config/phytium_pi_login.env
```

The dashboard stays evidence-led either way. The "Refresh live board status" action only runs a read-only SSH probe.
If `session_bootstrap/reports/openamp_demo_live_probe_latest.json` already exists, the dashboard loads that saved successful probe on startup and keeps showing it if a later in-dashboard refresh fails.

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
- HTTP smoke coverage for `GET /api/snapshot`, `POST /api/probe-board`, `GET /docs?path=...`, `GET /api/health`, `GET /`, `GET /app.js`, and `GET /app.css`
- live-probe cache behavior: startup reuse of the last successful probe artifact and preservation of that saved probe when a later refresh fails
- docs endpoint guardrails for missing path, invalid repo-external path, missing file, and JSON pretty-print rendering

Intentional gaps and higher-risk edges:

- `board_probe.run_live_probe()` now has direct unit coverage for success, timeout, non-zero exit, and JSON parse-error payload shaping, but those tests stub `build_probe_command()` so env-file parsing and SSH command selection are still not locked down directly
- the frontend is covered as served assets only; there is no browser-level regression for DOM rendering or the in-page refresh flow
- `main()`, `--probe-startup`, and real socket binding are not exercised; the suite instantiates `DashboardState` and `DemoRequestHandler` directly

If one more test is needed, the highest-value next addition is a `board_probe.build_probe_command()` unit test that writes a temporary env file and locks down the `ssh_with_password.sh` path, `REMOTE_SSH_PORT` override handling, and fallback to `connect_phytium_pi.sh --env ...`.
