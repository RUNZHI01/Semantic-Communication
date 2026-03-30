# Checked-in seed: `fused_conv2d_transpose1_add9`

This directory is the first repo-native handoff after the local-only
manual seed capture. It keeps the operator-specific editing surface in
the repo without touching trusted current or launching any remote work.

## Files

- `fused_conv2d_transpose1_add9_manual_candidate.py`: repo-native handwritten-hook entrypoint for this operator; it exposes the checked-in candidate v0 through the local/staging pre-compile override contract.
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

- it keeps the checked-in editable seed and checked-in candidate v0 side by side in this directory
- it returns a local/staging-only override descriptor for candidate v0
- `rpc_tune.py` now consumes that descriptor before `compile_relax()`, so the handwritten hook can replace the selected PrimFunc without touching trusted current
- the current contract is explicitly diagnostic-only: it is a raw pre-compile replacement path with `schedule_context_guarantee=not_guaranteed`
- runtime or reprobe numbers from this seam are `non_comparable_diagnostic_only`, not candidate-performance evidence
- a future `schedule_context_preserving_evaluation` path is still required before another handwritten candidate can be judged on performance

## Edit toward candidate v0

1. Start from `./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_editable_seed_tir.py`.
2. Keep `./session_bootstrap/handwritten/fused_conv2d_transpose1_add9/fused_conv2d_transpose1_add9_manual_candidate.py` as the hook-facing module path.
3. Keep the buffer contract stable:
   input `(1, 48, 64, 64)`, weight `(48, 24, 3, 3)`, bias `(1, 24, 1, 1)`, output `(1, 24, 128, 128)`.
4. Treat `data_dilate`, `data_pad`, `kernel_transform`, `compute`, and `T_add` as the honest baseline stages from the captured workload.
5. First manual edits should stay narrow: reduce intermediate traffic, fuse cheap transforms when possible, and only then try tiling/vectorization around `compute`.

## Hook wiring diagnostic through the existing manual hook

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
yet prove a performance change. It proves the local handwritten path reaches
the checked-in candidate v0 and applies it at the pre-compile integration point.
Treat any payload/runtime number from this path as diagnostic-only until a
schedule-context-preserving evaluation contract exists.

## Preferred local schedule-preserving build path

Once hook wiring is confirmed, prefer this local-only path before any future
remote/staging validation:

```bash
python3 ./session_bootstrap/scripts/run_transpose1_post_db_local_build.py
```

This wrapper drives the checked-in best-staging task-summary / DB defaults,
performs the post-DB scheduled `fused_conv2d_transpose1_add9` swap, and exports a
local artifact plus adjacent JSON report under:

```text
./session_bootstrap/tmp/transpose1_post_db_swap_local_build
```

This is still build-level diagnostic evidence only, but it preserves the best
staging schedule context much more honestly than the older raw pre-compile hook
lane.

## Staging lane after a real override exists

Reuse the same `manual_hook_overlay.env` with the existing staging-safe
one-shot and profile commands from the transpose1 handwritten runbooks. Do not
overwrite trusted current while this checked-in candidate is still seed-derived.
Until a `schedule_context_preserving_evaluation` path exists, treat those
one-shot / reprobe outputs as contract-side diagnostics rather than
performance-comparable evidence.

## Source reminder

The original captured pre-compile snapshot is still at `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_seed_tir.py` if you need the full Relax callsite context.
