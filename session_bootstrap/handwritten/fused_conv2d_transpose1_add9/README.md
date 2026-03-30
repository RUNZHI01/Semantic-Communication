# Checked-in seed: `fused_conv2d_transpose1_add9`

This directory is the first repo-native handoff after the local-only
manual seed capture. It keeps the operator-specific editing surface in
the repo without touching trusted current or launching any remote work.

## Files

- `fused_conv2d_transpose1_add9_manual_candidate.py`: repo-native handwritten-hook entrypoint for this operator; it reports the checked-in candidate path without changing compile output yet.
- `fused_conv2d_transpose1_add9_editable_seed_tir.py`: editable operator TIR extracted from the local MetaSchedule task log.
- `seed_manifest.json`: trimmed seed context copied from the captured seed JSON.
- `README.md`: short editing runbook.

## Why this exists

- the captured pre-compile seed JSON at `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_seed.json` is real, but its paired seed snapshot only shows the Relax callsite under `main`
- the local task log at `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_seed_capture/tuning_logs/logs/tvm.s_tir.meta_schedule.logging.task_0_fused_conv2d_transpose1_add9.log` contains the actual `fused_conv2d_transpose1_add9` TIR workload
- this package checks that workload into the repo so the first manual edits are not trapped under `tmp/`

## Refresh from the latest local capture

```bash
python3 ./session_bootstrap/scripts/refresh_fused_conv2d_transpose1_add9_checked_in_seed.py
```

The helper reads:
- `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_seed.json`
- `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_seed_tir.py`
- `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_seed_capture/tuning_logs/logs/tvm.s_tir.meta_schedule.logging.task_0_fused_conv2d_transpose1_add9.log`

It refuses to overwrite this directory unless `--allow-overwrite` is passed.

## Hook-facing candidate path

The existing `rpc_tune.py` handwritten hook can point at `./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_manual_candidate.py`
today. That module is deliberately honest:

- it points engineers at the checked-in editable TIR in this directory
- it lets the manual-hook path prove it loaded the checked-in candidate
- it still reports `manual_override_applied = false`, so compile output stays unchanged until a later override step is implemented

## Edit toward candidate v0

1. Start from `./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_editable_seed_tir.py`.
2. Keep `./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_manual_candidate.py` as the hook-facing module path.
3. Keep the buffer contract stable:
   input `(1, 48, 64, 64)`, weight `(48, 24, 3, 3)`, bias `(1, 24, 1, 1)`, output `(1, 24, 128, 128)`.
4. Treat `data_dilate`, `data_pad`, `kernel_transform`, `compute`, and `T_add` as the honest baseline stages from the captured workload.
5. First manual edits should stay narrow: reduce intermediate traffic, fuse cheap transforms when possible, and only then try tiling/vectorization around `compute`.

## Local-only validation through the existing manual hook

Regenerate the overlay so it points at the checked-in candidate module:

```bash
python3 ./session_bootstrap/scripts/prepare_fused_conv2d_transpose1_add9_manual_hook_overlay.py \
  --scaffold-dir ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold \
  --manual-impl-path ./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_manual_candidate.py \
  --allow-overwrite
```

Then exercise the existing hook with no remote work:

```bash
bash ./session_bootstrap/scripts/capture_fused_conv2d_transpose1_add9_manual_seed.sh \
  --scaffold-dir ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold \
  --allow-existing-output
```

That proves the hook is loading the checked-in candidate path. It does not
yet prove a performance change, because the checked-in candidate module still
reports `manual_override_applied = false`.

## Staging lane after a real override exists

Once `build_manual_impl()` starts applying a real override, reuse the same
`manual_hook_overlay.env` with the existing staging-safe one-shot and profile
commands from the transpose1 handwritten runbooks. Do not overwrite trusted
current while this checked-in candidate is still seed-derived.

## Source reminder

The original captured pre-compile snapshot is still at `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_seed_tir.py` if you need the full Relax callsite context.
