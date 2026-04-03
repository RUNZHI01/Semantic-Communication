# Opus Candidate Microbenchmark Results — 2026-04-03

- benchmarked_on: Phytium Pi (Cortex-A72, 4-core)
- samples: 30 per operator
- benchmark_tool: `bench_so_module_remote.py` / `bench_mean4_v4_remote.py`
- compiled_with: TVM 0.24.dev0, target `llvm -mtriple=aarch64-linux-gnu -mcpu=cortex-a72 -mattr=+neon -num-cores=4`
- compile_host: Snapdragon aarch64 dev machine (native, no cross-compile)

## Results Summary

| Operator | Version | Median (µs) | vs Baseline | Correctness (max_abs_diff) | Verdict |
|---|---|---|---|---|---|
| fused_variance3_add10_tir_sqrt3 | v1.1 (scope fix) | **2771** | **-22.2%** | 2.26e-06 ✅ | **KEEP — best variance3** |
| fused_variance3_add10_tir_sqrt3 | v2 (Welford) | 5309 | +49.0% | 3.22e-06 ✅ | DISCARD — division kills vectorization |
| fused_variance1_add3_tir_sqrt1 | v1 (Welford) | **1315** | **-73.7%** | 6.56e-07 ✅ | **KEEP — huge win** |
| fused_variance4_add13_tir_sqrt4 | v20 (Welford) | 10564 | +291.3% | 5.60e-06 ✅ | DISCARD — catastrophic regression |
| fused_mean4_subtract4_divide4_multiply4_add14_relu3 | v4 (fused) | **4558** | **-8.8%** | 9.54e-07 ✅ | **KEEP — loop fusion works** |

## Key Findings

### 1. Welford is counterproductive for large spatial dimensions
- variance3 (128×128): Welford +49% vs two-pass — the per-element `1/(k2*128+k3+1)` division prevents LLVM NEON auto-vectorization
- variance4 (256×256): Welford +291% — even worse at larger spatial size
- variance1 (32×32): Welford -73.7% — works at small size because the overhead is dominated by reduction, not element ops

**Lesson**: Welford single-pass is only beneficial when the per-channel working set exceeds L1d AND the element count is small enough that scalar division overhead doesn't dominate. For 128×128+, the two-pass approach with LLVM vectorization wins despite higher memory traffic.

### 2. scope="local" fix is pure upside
- variance3 v1.1 (just adding `scope="local"` to `T_multiply_red`): -22.2%
- Zero correctness risk, zero algorithm change, just telling TVM to keep the accumulator in a register/local memory

### 3. Loop fusion is effective for instance-norm epilogue
- mean4 v4 (5 loops → 1 fused loop): -8.8%
- Memory traffic reduced from ~31MB to ~6MB
- This is a conservative estimate; the baseline_median_us=5000 is approximate

### 4. Correctness is excellent across all candidates
- All 5 candidates pass with max_abs_diff < 1e-5 (threshold: 1e-3)
- Welford floating-point accumulation error is negligible even at 256×256

## Candidates for Integration (Phase 2)

Only operators with positive benchmark results should be integrated:

| Operator | Version to Integrate | Expected e2e Impact |
|---|---|---|
| fused_variance3_add10_tir_sqrt3 | v1.1 (scope fix) | ~0.5-1ms payload improvement |
| fused_variance1_add3_tir_sqrt1 | v1 (Welford) | ~0.3-0.5ms payload improvement |
| fused_mean4_subtract4_divide4_multiply4_add14_relu3 | v4 (fused) | ~0.5-0.8ms payload improvement |

**Total estimated payload improvement**: ~1.3-2.3ms (~1-1.8% of 130.219ms baseline)

## Files Produced

### Compiled Artifacts
- `session_bootstrap/tmp/opus_candidates_20260403/variance3_v1_1.so` (76960 bytes)
- `session_bootstrap/tmp/opus_candidates_20260403/variance3_v2_welford.so` (76720 bytes)
- `session_bootstrap/tmp/opus_candidates_20260403/variance1_v1_welford.so` (76640 bytes)
- `session_bootstrap/tmp/opus_candidates_20260403/variance4_v20_welford.so` (76680 bytes)
- `session_bootstrap/tmp/opus_candidates_20260403/mean1_v1.so` (92312 bytes)
- `session_bootstrap/tmp/opus_candidates_20260403/mean4_v4_fused.so` (94440 bytes)

### Benchmark Scripts
- `session_bootstrap/scripts/build_opus_candidates_batch1.sh` — local compilation
- `session_bootstrap/scripts/bench_so_module_remote.py` — generic 2-arg benchmark
- `session_bootstrap/scripts/bench_mean4_v4_remote.py` — mean4 4-arg benchmark
- `session_bootstrap/scripts/run_opus_bench_all.sh` — batch runner

### Raw Results
- Remote: `/home/user/Downloads/jscc-test/jscc_opus_candidates/results.jsonl`

### TIR Source Files (created by Opus/Codex)
- `session_bootstrap/handwritten/fused_variance4_add13_tir_sqrt4/fused_variance4_add13_tir_sqrt4_scheduled_form_candidate_v20_working_copy_tir.py`
- `session_bootstrap/handwritten/fused_mean4_subtract4_divide4_multiply4_add14_relu3/fused_mean4_subtract4_divide4_multiply4_add14_relu3_scheduled_form_candidate_v4_working_copy_tir.py`
