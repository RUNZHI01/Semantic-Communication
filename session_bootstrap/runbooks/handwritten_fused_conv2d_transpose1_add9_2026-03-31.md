# Handwritten Candidate: fused_conv2d_transpose1_add9（2026-03-31）

## 目的

为 wave-1 priority-1 的手写热点候选 `fused_conv2d_transpose1_add9` 提供一个最小但可执行的 staging-safe 脚手架。

这个 runbook 不负责直接写出手写 TIR kernel；它负责把“候选 artifact 如何落 staging、如何做 payload / reprobe、如何避免污染 trusted current”固化下来。

## 为什么先做它

根据当前 best staging candidate 的 runtime reprobe：

- `session_bootstrap/reports/profiling_runtime_joint_top6_staging_artifact_reprobe_20260331_0010.md`
- `fused_conv2d_transpose1_add9` 仍是 runtime top-1
  - `24275.261 us`
  - `14.60%`

而且它已经跨越多轮 retarget：

- runtime-top2
- runtime-shifted-top3
- runtime-joint-top5
- runtime-joint-top6

都没有从关键热点列表中退出，所以它是当前最合理的第一个手写 TIR / NEON 候选。

## 固定基线

- trusted current mainline SHA：`6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`
- current best staging candidate SHA：`5bd14b9f97d1d06f04a484cd8b1b3f57a955d65711ed65a22f9925dcec44698d`
- 当前最佳 staging 冻结记录：
  - `session_bootstrap/reports/current_best_staging_candidate_20260331.md`

## 推荐 staging 归档

手写候选不要进入 `jscc` 或 `jscc_staging`，而是使用单独归档：

```text
/home/user/Downloads/jscc-test/jscc_staging_handwritten
```

## 最小工作流

### 1) 为手写候选生成 profile env

先从现有 joint-top6 reprobe 的 trusted env snapshot 派生一个手写候选 env：

```bash
python3 ./session_bootstrap/scripts/prepare_handwritten_fused_conv2d_transpose1_add9_env.py \
  --expected-sha256 <candidate_sha256>
```

默认输出：

```text
session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_profile.env
```

它会自动：

- 把 `INFERENCE_CURRENT_ARCHIVE` 指到 `jscc_staging_handwritten`
- 把 `REMOTE_CURRENT_ARTIFACT` 指到 handwritten staging 的 `optimized_model.so`
- 把 `INFERENCE_CURRENT_EXPECTED_SHA256` 固定成你传入的候选 SHA

### 2) 用 staging validate 跑 payload 验证

当你已经有了手写候选 artifact 所用的 rebuild env / overlay env 时：

```bash
bash ./session_bootstrap/scripts/run_phytium_current_safe_staging_validate.sh \
  --rebuild-env <manual_overlay.env> \
  --remote-archive-dir /home/user/Downloads/jscc-test/jscc_staging_handwritten \
  --report-id phytium_handwritten_fused_conv2d_transpose1_add9_$(date +%Y%m%d_%H%M%S)
```

### 3) 再做 runtime reprobe

```bash
python3 ./session_bootstrap/scripts/run_task_5_1_operator_profile.py \
  --run-id profiling_handwritten_fused_conv2d_transpose1_add9_$(date +%Y%m%d_%H%M%S) \
  --hotspot-mode reuse \
  --runtime-mode attempt \
  --trusted-env ./session_bootstrap/tmp/handwritten_fused_conv2d_transpose1_add9_profile.env \
  --trusted-variant current \
  --max-inputs 1 \
  --profile-samples 1
```

## 必须同时满足的保留条件

这个手写候选只有在下面条件都满足时，才值得保留：

1. `artifact_sha256_match = true`
2. safe runtime payload 不劣于当前 best staging candidate（`5bd14b9f...`）
3. reprobe 中 `fused_conv2d_transpose1_add9` 的时间 / 占比显著下降
4. 没有制造新的 dominating hotspot snapback

如果任何一项不满足：

- 保留报告
- 终止这版候选
- 不覆盖 trusted current
- 也不覆盖 current best staging candidate

## Scope Guard

这个 runbook 是 `fused_conv2d_transpose1_add9` 的 operator-specific 脚手架：

- 它只服务于这个 op 的手写验证路径；
- 不引入新 tuning subsystem；
- 不自动生成手写 TIR；
- 不会改写 trusted current 主线。
