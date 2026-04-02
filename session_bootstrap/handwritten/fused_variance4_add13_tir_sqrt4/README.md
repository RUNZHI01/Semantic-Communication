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
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v2_working_copy_tir.py`: first handwritten edit candidate that removes the standalone `T_add_intermediate` epilogue stage by folding the epsilon add into the final `sqrt` consumer.
- `scheduled_form_candidate_v2_working_copy_manifest.json`: manifest for the versioned `v2` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v2.py`: local-only candidate wrapper for the `v2` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v3_working_copy_tir.py`: narrow follow-up candidate that removes the standalone `T_divide_intermediate` epilogue stage by folding the `/65536.0` directly into the final `sqrt` consumer.
- `scheduled_form_candidate_v3_working_copy_manifest.json`: manifest for the versioned `v3` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v3.py`: local-only candidate wrapper for the `v3` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v4_working_copy_tir.py`: narrow follow-up candidate that removes the standalone `T_divide` mean stage by folding the mean `/65536.0` directly into the `T_subtract` consumer while keeping the `v3` simplifications intact.
- `scheduled_form_candidate_v4_working_copy_manifest.json`: manifest for the versioned `v4` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v4.py`: local-only candidate wrapper for the `v4` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v5_working_copy_tir.py`: narrow follow-up candidate that removes the standalone full-size `T_subtract` stage by folding the subtraction directly into the `T_multiply` consumer while keeping the `v4` simplifications intact.
- `scheduled_form_candidate_v5_working_copy_manifest.json`: manifest for the versioned `v5` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v5.py`: local-only candidate wrapper for the `v5` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6_working_copy_tir.py`: narrow follow-up candidate that removes the standalone full-size `T_multiply` stage by folding the squared subtract expression directly into the `T_multiply_red` consumer while keeping the `v5` simplifications intact.
- `scheduled_form_candidate_v6_working_copy_manifest.json`: manifest for the versioned `v6` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6.py`: local-only candidate wrapper for the `v6` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6a_working_copy_tir.py`: exactness-recovery follow-up that keeps the `v6` full-size `T_multiply` removal but adds a one-element volatile local round-trip before `T_multiply_red` accumulation to block backend `fmadd` contraction.
- `scheduled_form_candidate_v6a_working_copy_manifest.json`: manifest for the versioned `v6a` working copy.
- `fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6a.py`: local-only candidate wrapper for the `v6a` working copy.

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

Run the local-only post-db scheduled swap build for the first handwritten `v2`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v2.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v2
```

Run the local correctness compare for the current `v2` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v2_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v2_correctness_check.json
```

Run the local-only post-db scheduled swap build for the follow-up `v3`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v3.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v3
```

Run the local correctness compare for the current `v3` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v3_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v3_correctness_check.json
```

Run the local-only post-db scheduled swap build for the follow-up `v4`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v4.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v4
```

Run the local correctness compare for the current `v4` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v4_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v4_correctness_check.json
```

Run the local-only post-db scheduled swap build for the follow-up `v5`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v5.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v5
```

Run the local correctness compare for the current `v5` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v5_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v5_correctness_check.json
```

Run the local-only post-db scheduled swap build for the follow-up `v6`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v6
```

Run the local correctness compare for the current `v6` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v6_correctness_check.json
```

Run the local-only post-db scheduled swap build for the exactness-recovery `v6a`
candidate:

```bash
python3 ./session_bootstrap/scripts/run_variance4_post_db_local_build.py \
  --candidate-impl ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6a.py \
  --output-dir ./session_bootstrap/tmp/variance4_post_db_swap_local_build_v6a
```

Run the local correctness compare for the current `v6a` working copy:

```bash
python3 ./session_bootstrap/scripts/check_fused_variance4_add13_tir_sqrt4_scheduled_reference_vs_working_copy.py \
  --candidate-tir ./session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v6a_working_copy_tir.py \
  --output-json ./session_bootstrap/tmp/variance4_v6a_correctness_check.json
```

Current best-staging keeps `fused_variance4_add13_tir_sqrt4` in the task
summary, but does not expose a direct `query_schedule` / `query_ir_module` /
`query_tuning_record` hit for it. This lane therefore starts from the post-db
applied-module operator form recovered through the existing seam.

This lane is still local-only and diagnostic-only. Do not use it for SSH or
remote benchmark claims until a real variance4 handwritten edit exists.
