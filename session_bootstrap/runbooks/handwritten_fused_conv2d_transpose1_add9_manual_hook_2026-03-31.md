# Handwritten `fused_conv2d_transpose1_add9` Manual Hook

Updated: `2026-03-31`

## Purpose

Add the smallest missing handoff between the existing handwritten transpose1
scaffold and a first engineer-owned manual implementation.

This remains staging-only:

- trusted current stays untouched
- current best staging stays pinned at `5bd14b9f97d1d06f04a484cd8b1b3f57a955d65711ed65a22f9925dcec44698d`
- no new remote job is introduced here

## The Missing Piece

The existing scaffold already produces:

- `manual_rebuild.env`
- `manual_validate_inference.env`
- `manual_profile.env`
- `bookkeeping.json`

What it does not yet materialize is the first concrete local handoff:

1. one editable manual implementation file for `fused_conv2d_transpose1_add9`
2. one rebuild overlay env that points at that file

That is the narrowest useful next step because the rebuild wrappers already
`source "$REBUILD_ENV"` before they assemble the local compile command. The
remaining engineer patch is therefore local-only: teach the rebuild-side code to
consume `TVM_HANDWRITTEN_IMPL_PATH` after the env is sourced and before compile.

## Generate The Hook Overlay

Starting from the existing scaffold directory:

```bash
python3 ./session_bootstrap/scripts/prepare_fused_conv2d_transpose1_add9_manual_hook_overlay.py \
  --scaffold-dir ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold
```

This creates:

- `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/fused_conv2d_transpose1_add9_manual_impl.py`
- `./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/manual_hook_overlay.env`

## What The Overlay Means

`manual_hook_overlay.env` sources the existing `manual_rebuild.env` and adds only
these handoff variables:

- `TVM_HANDWRITTEN_OP=fused_conv2d_transpose1_add9`
- `TVM_HANDWRITTEN_IMPL_PATH=<repo-native path to the placeholder file>`
- `TVM_HANDWRITTEN_IMPL_ENTRYPOINT=build_manual_impl`
- `TVM_HANDWRITTEN_IMPL_METADATA_FN=describe_placeholder`
- `TVM_HANDWRITTEN_BOOKKEEPING_JSON=<repo-native path to bookkeeping.json>`

No stock wrapper behavior changes yet. The overlay is a contract for the first
local rebuild-side patch.

## Intended Rebuild Wiring

When the engineer is ready to plug in the first manual implementation, keep the
rebuild path narrow:

1. source `manual_hook_overlay.env` instead of `manual_rebuild.env`
2. after the rebuild env is sourced, check `TVM_HANDWRITTEN_OP`
3. import `TVM_HANDWRITTEN_IMPL_PATH`
4. call `build_manual_impl()`
5. continue the normal rebuild flow to `optimized_model.so`

This keeps the handwritten lane staging-only because the only difference is the
local rebuild overlay and the resulting staging archive upload.

## Placeholder File Contract

The generated placeholder module is bookkeeping plus a stub:

- `describe_placeholder()` returns the fixed operator name, reference staging SHA,
  shapes, and bookkeeping path
- `build_manual_impl()` raises `NotImplementedError` until the engineer replaces
  it with the first real manual implementation

Edit that generated file, not the checked-in template.

## First Rebuild Command After Local Wiring Exists

Once the local build-side patch knows how to honor `TVM_HANDWRITTEN_IMPL_PATH`,
switch only the rebuild env argument:

```bash
bash ./session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh \
  --rebuild-env ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/manual_hook_overlay.env \
  --inference-env ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_scaffold/manual_validate_inference.env \
  --remote-archive-dir /home/user/Downloads/jscc-test/jscc_staging_handwritten_fused_conv2d_transpose1_add9 \
  --report-id phytium_handwritten_fused_conv2d_transpose1_add9_$(date +%Y%m%d_%H%M%S)
```

Nothing else in the staging flow changes.
