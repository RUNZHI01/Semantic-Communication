# release_v1.4.0 signed-admission implementation-boundary patch note

- Patch file:
  `session_bootstrap/patches/phytium_openamp_for_linux_signed_admission_impl_boundary_release_v1.4.0_2026-03-16.patch`
- Patch prerequisite:
  `session_bootstrap/patches/phytium_openamp_for_linux_signed_admission_scaffold_release_v1.4.0_2026-03-16.patch`
- Target source path:
  `example/system/amp/openamp_for_linux/src/slaver_00_example.c`
- Contract fixture:
  `session_bootstrap/examples/openamp_signed_manifest.fixture.firmware_contract.json`

Status:

- Repo-side follow-on patch only.
- Board firmware does not support signed admission yet.
- Legacy `JOB_REQ` SHA allowlist behavior remains intact when no signed stage exists for the `job_id`.

What moved from placeholder to concrete boundary in this follow-on patch:

- `sc_public_key_slots[0]` now carries the exact slot binding triple from the committed fixture:
  - `key_id = fixture-dev-20260316`
  - `channel = openamp-fixture`
  - exact uncompressed P-256 public key bytes derived from:
  `session_bootstrap/examples/openamp_signed_manifest.fixture.public.pem`
- `ScManifestContract` now has explicit C fields for the committed manifest contract:
  - `schema_id`
  - `manifest_version`
  - `artifact_sha256`
  - `deadline_ms`
  - `expected_outputs`
  - `flags`
  - `publisher_key_id`
  - `publisher_channel`
- `sc_ctrl_parse_manifest_contract(...)` is no longer a blank TODO surface.
  It now decomposes the narrow parser path into exact helper calls for:
  - top-level `schema`
  - top-level `manifest_version`
  - `artifact.sha256`
  - `job.deadline_ms`
  - `job.expected_outputs`
  - `job.job_flags`
  - `publisher.key_id`
  - `publisher.channel`
- `sc_ctrl_verify_signed_manifest_for_job_req(...)` now uses the parsed publisher fields for slot binding:
  - `publisher.key_id / publisher.channel` must match the selected firmware key slot before the 44-byte `JOB_REQ` mirror is accepted.
- `sc_ctrl_verify_manifest_signature(...)` now has one exact standalone-SDK integration boundary:
  - `sc_ctrl_crypto_sha256(...)`
  - `sc_ctrl_crypto_verify_ecdsa_p256_sha256_der(...)`
  - request struct `ScEcdsaP256VerifyRequest`
- The crypto wrappers now pin the exact mbedTLS drop-in sequence instead of a generic TODO:
  - `mbedtls_sha256_ret(...)`
  - `mbedtls_ecdsa_init(...)`
  - `mbedtls_ecp_group_load(...)`
  - `mbedtls_ecp_point_read_binary(...)`
  - `mbedtls_ecp_check_pubkey(...)`
  - `mbedtls_ecdsa_read_signature(...)`
  - `mbedtls_ecdsa_free(...)`

What still intentionally does not change runtime behavior:

- The new crypto wrappers still return failure until wired to the accepted standalone-SDK crypto objects.
- Signed admission therefore remains deny-by-default even though the manifest digest path, key bytes, and wrapper interfaces are now concrete.
- No claim is made that board firmware already verifies or admits signed manifests.

Exact committed artifacts that make the next coding step mechanical:

- signed bundle:
  `session_bootstrap/examples/openamp_signed_manifest.fixture.bundle.json`
- transport plan:
  `session_bootstrap/examples/openamp_signed_manifest.fixture.transport.json`
- firmware contract fixture:
  `session_bootstrap/examples/openamp_signed_manifest.fixture.firmware_contract.json`

Exact next firmware coding step:

1. Apply this follow-on patch after the scaffold patch in the firmware tree.
2. Keep the parser helper split and publisher slot binding as-is; the remaining work is inside the two crypto wrappers.
3. Replace `sc_ctrl_crypto_sha256(...)` with the accepted standalone-SDK SHA-256 one-shot call already named in the patch comment.
4. Replace `sc_ctrl_crypto_verify_ecdsa_p256_sha256_der(...)` with the exact `mbedtls_ecdsa_init -> mbedtls_ecp_group_load -> mbedtls_ecp_point_read_binary -> mbedtls_ecp_check_pubkey -> mbedtls_ecdsa_read_signature -> mbedtls_ecdsa_free` sequence against `slot->public_key_uncompressed`.
5. Build the patched firmware and replay the committed fixture transport plan, ending with the unchanged 44-byte `JOB_REQ`.
6. Only after that passes should the signed path be flipped from deny-by-default to allow-on-success.
