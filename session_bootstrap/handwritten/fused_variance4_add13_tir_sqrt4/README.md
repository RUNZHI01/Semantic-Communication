# Checked-in scheduled-form lane: `fused_variance4_add13_tir_sqrt4`

This directory is the smallest repo-native handwritten lane for
`fused_variance4_add13_tir_sqrt4` that keeps the frozen best-staging
MetaSchedule context intact locally.

It intentionally starts at the post-db scheduled reference seed and does not
introduce a separate raw pre-compile hook lane yet.

## Files

- `fused_variance4_add13_tir_sqrt4_post_db_scheduled_reference_seed_tir.py`: checked-in post-db scheduled reference seed recovered from the frozen best-staging DB.
- `post_db_scheduled_reference_seed_manifest.json`: small manifest for that scheduled reference seed.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v1_working_copy_tir.py`: editable scheduled-form working copy cloned from the checked-in reference seed.
- `scheduled_form_candidate_v1_working_copy_manifest.json`: small manifest for the editable working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v1.py`: local-only candidate wrapper that points the existing post-db seam at the working copy.

## Refresh / Build

Refresh the checked-in scheduled reference seed:

```bash
python3 ./session_bootstrap/scripts/refresh_fused_variance4_add13_tir_sqrt4_post_db_scheduled_seed.py \
  --allow-overwrite
```

Refresh the editable working copy from that seed:

```bash
python3 ./session_bootstrap/scripts/refresh_fused_variance4_add13_tir_sqrt4_scheduled_form_working_copy.py \
  --allow-overwrite
```

Run the local-only post-db scheduled swap build:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build
```

Current best-staging keeps `fused_variance4_add13_tir_sqrt4` in the task
summary, but does not expose a direct `query_schedule` / `query_ir_module` /
`query_tuning_record` hit for it. This lane therefore starts from the post-db
applied-module operator form recovered through the existing seam.

This lane is still local-only and diagnostic-only. Do not use it for SSH or
remote benchmark claims until a real variance4 handwritten edit exists.
