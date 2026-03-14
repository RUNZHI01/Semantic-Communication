# release_v1.4.0 STATUS_REQ/RESP patch note

- Patch file: `session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch`
- Target source path: `example/system/amp/openamp_for_linux/src/slaver_00_example.c`
- Target source shape: old `release_v1.4.0` callback flow with `FRpmsgEchoApp(...)`, `SHUTDOWN_MSG`, and direct `temp_data` echo behavior

Structural differences from `phytium_openamp_for_linux_status_req_resp_2026-03-14.patch`:

- This adaptation hooks the old `rpmsg_endpoint_cb(...)` echo path directly instead of the newer `ProtocolData` parser/switch path.
- `FRpmsgEchoApp(...)`, the top-level entry path, and the service name `rpmsg-openamp-demo-channel` stay unchanged.
- `SHUTDOWN_MSG` handling is preserved before control-frame parsing.

Implemented behavior:

- Accept `STATUS_REQ (0x08)` with `payload_len == 0`
- Reply with `STATUS_RESP (0x09)` carrying:
  - `guard_state=1`
  - `active_job_id=0`
  - `last_fault_code=0`
  - `heartbeat_ok=0`
  - `sticky_fault=0`
  - `total_fault_count=0`
- Ignore invalid, non-control, or unsupported control frames conservatively after logging

Local patch check performed on 2026-03-14:

```bash
git apply --check --directory=.codex_tmp/release_v1.4.0_verify \
  session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch
```
