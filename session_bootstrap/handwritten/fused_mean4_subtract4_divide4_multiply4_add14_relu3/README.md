# Checked-in scheduled-form lane: `fused_mean4_subtract4_divide4_multiply4_add14_relu3`

This directory is the smallest repo-native handwritten lane for
`fused_mean4_subtract4_divide4_multiply4_add14_relu3` that keeps the
best-staging MetaSchedule context intact locally.

It intentionally starts at the post-db scheduled reference seed and does not
introduce a separate raw pre-compile hook lane yet.

## Files

- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_post_db_scheduled_reference_seed_tir.py`: checked-in post-db scheduled reference seed recovered from the frozen best-staging DB.
- `post_db_scheduled_reference_seed_manifest.json`: small manifest for that scheduled reference seed.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v1_working_copy_tir.py`: editable scheduled-form working copy cloned from the checked-in reference seed.
- `scheduled_form_candidate_v1_working_copy_manifest.json`: small manifest for the editable working copy.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v1.py`: local-only candidate wrapper that points the existing post-db seam at the working copy.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v2_working_copy_tir.py`: first real handwritten follow-up on top of the checked-in v1 seed clone.
- `scheduled_form_candidate_v2_working_copy_manifest.json`: manifest for the v2 scalar-epilogue-handoff working copy.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v2.py`: local post-db wrapper for the v2 working copy.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v3_working_copy_tir.py`: operator-specific ablation after v2 board regression; keep v1 structure and change only the tiny mean handoff buffer placement (`scope="local"`).
- `scheduled_form_candidate_v3_working_copy_manifest.json`: manifest for the v3 local-mean-handoff-only ablation working copy.
- `fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v3.py`: local post-db wrapper for the v3 working copy.

## Refresh / Build

Refresh the checked-in scheduled reference seed:

```bash
python3 ./session_bootstrap/scripts/refresh_fused_mean4_subtract4_divide4_multiply4_add14_relu3_post_db_scheduled_seed.py \
  --allow-overwrite
```

Refresh the editable working copy from that seed:

```bash
python3 ./session_bootstrap/scripts/refresh_fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_working_copy.py \
  --allow-overwrite
```

Run the local-only post-db scheduled swap build:

```bash
python3 ./session_bootstrap/scripts/run_mean4_post_db_local_build.py \
  --output-dir ./session_bootstrap/tmp/mean4_post_db_swap_local_build
```

Run the first real handwritten v2 follow-up:

```bash
python3 ./session_bootstrap/scripts/run_mean4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_mean4_subtract4_divide4_multiply4_add14_relu3/fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v2.py \
  --output-dir ./session_bootstrap/tmp/mean4_post_db_swap_local_build_v2
```

Run the v3 local ablation follow-up:

```bash
python3 ./session_bootstrap/scripts/run_mean4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_mean4_subtract4_divide4_multiply4_add14_relu3/fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v3.py \
  --output-dir ./session_bootstrap/tmp/mean4_post_db_swap_local_build_v3
```

Prepare a dedicated handwritten env for a board payload attempt:

```bash
./session_bootstrap/scripts/prepare_handwritten_fused_mean4_subtract4_divide4_multiply4_add14_relu3_env.py \
  --expected-sha256 <artifact_sha256>
```

Run the dedicated board payload helper:

```bash
./session_bootstrap/scripts/run_mean4_remote_payload_benchmark.sh \
  --inference-env ./session_bootstrap/tmp/handwritten_fused_mean4_subtract4_divide4_multiply4_add14_relu3_profile.env \
  --local-artifact ./session_bootstrap/tmp/mean4_post_db_swap_local_build_v2/fused_mean4_subtract4_divide4_multiply4_add14_relu3_post_db_swap.so \
  --database-dir ./session_bootstrap/tmp/phytium_runtime_joint_top6_targeted_staging_search_20260330_2315/tuning_logs
```

If the immediate blocker is upload integrity rather than the benchmark itself,
run the helper in upload-only mode first:

```bash
./session_bootstrap/scripts/run_mean4_remote_payload_benchmark.sh \
  --upload-only \
  --inference-env ./session_bootstrap/tmp/handwritten_fused_mean4_subtract4_divide4_multiply4_add14_relu3_profile.env \
  --local-artifact ./session_bootstrap/tmp/mean4_post_db_swap_local_build_v2/fused_mean4_subtract4_divide4_multiply4_add14_relu3_post_db_swap.so \
  --database-dir ./session_bootstrap/tmp/phytium_runtime_joint_top6_targeted_staging_search_20260330_2315/tuning_logs
```

Current best-staging keeps `fused_mean4_subtract4_divide4_multiply4_add14_relu3`
in the task summary, but does not expose a direct `query_schedule` /
`query_ir_module` hit for it. This lane therefore starts from the post-db
applied-module operator form recovered through the same seam.

Important scope note:

- the checked-in `v1` lane remains only a seed-clone edit surface
- `v2` is the first real mean4 handwritten edit and the first one worth a
  board payload attempt
- `v3` is a smallest operator-specific ablation to isolate whether v2's
  regression came from scalar epilogue fusion vs tiny mean-handoff placement
- the remote payload helper now verifies remote `sha256 + size_bytes` before
  it runs the benchmark, and `--upload-only` isolates that gate
- board claims still require a successful remote upload, SHA match, and payload
  benchmark result; helper availability alone is not a performance claim
