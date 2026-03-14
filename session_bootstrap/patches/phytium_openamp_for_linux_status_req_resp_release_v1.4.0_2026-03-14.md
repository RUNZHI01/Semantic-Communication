# release_v1.4.0 STATUS_REQ/RESP + JOB_REQ/JOB_ACK patch note

- Patch file: `session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch`
- Target source path: `example/system/amp/openamp_for_linux/src/slaver_00_example.c`
- Target source shape: old `release_v1.4.0` callback flow with `FRpmsgEchoApp(...)`, `SHUTDOWN_MSG`, and direct `temp_data` echo behavior

Structural differences from `phytium_openamp_for_linux_status_req_resp_2026-03-14.patch`:

- This adaptation still hooks the old `rpmsg_endpoint_cb(...)` echo path directly instead of the newer `ProtocolData` parser/switch path.
- `FRpmsgEchoApp(...)`, the top-level entry path, and the service name `rpmsg-openamp-demo-channel` stay unchanged.
- `SHUTDOWN_MSG` handling is still preserved before control-frame parsing.

Implemented behavior:

- Keep the existing control header shape: `magic/version/msg_type/seq/job_id/payload_len/header_crc32`.
- Accept `STATUS_REQ (0x08)` with `payload_len == 0` and reply with a stateful `STATUS_RESP (0x09)` carrying:
  - `guard_state`
  - `active_job_id`
  - `last_fault_code`
  - `heartbeat_ok`
  - `sticky_fault=0`
  - `total_fault_count`
- Accept `JOB_REQ (0x01)` with a fixed 44-byte payload:
  - `expected_sha256[32]`
  - `deadline_ms`
  - `expected_outputs`
  - `flags`
- Reply with `JOB_ACK (0x02)` carrying:
  - `decision`
  - `fault_code`
  - `guard_state`

Minimal admission checks in the patch:

- Guard must be `READY` and `active_job_id` must be `0`.
- `expected_sha256` must match the built-in trusted-current SHA constant
  - `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`
- `deadline_ms > 0`
- `expected_outputs` must be `1` or `300`
- `flags` must be one of the known wire values `1/2/3`

State behavior:

- On `ALLOW`, the patch sets:
  - `active_job_id = <request job_id>`
  - `guard_state = JOB_ACTIVE`
  - `last_fault_code = 0`
- On `DENY`, the patch keeps the current runtime state, updates `last_fault_code`, increments `total_fault_count`, and sends a real `JOB_ACK(DENY, ...)`.
- Unsupported control messages are still ignored conservatively after logging.

Local patch check performed on 2026-03-14:

```bash
git apply --check --directory=.codex_tmp/release_v1.4.0_verify \
  session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch
```
