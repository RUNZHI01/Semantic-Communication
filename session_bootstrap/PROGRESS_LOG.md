# Session Progress Log（长期维护）

- 最后更新：2026-03-11 08:37 +0800（baseline-vs-current-safe 最终 inference compare 已成功落盘；根因确认为远端 current-safe `optimized_model.so` 漂移；inference 路径已加入 artifact SHA guard，并在飞腾派真实 current-safe smoke 中验证 `artifact_sha256_match=true`）
- 作用：沉淀“当前状态 + 失败经验 + 下一步最小执行方案”，避免重复踩坑。

## 1) 时间线（关键里程碑）

| 时间 | 里程碑 | 结论 | 证据 |
|---|---|---|---|
| 2026-03-01 12:19 | P0/P1 状态盘点 | P0 闭环已具备，P1 仅 warm-start 验证待补 | `session_bootstrap/reports/p0_p1_status_2026-03-01.md` |
| 2026-03-01 13:18 | RPC smoke 首轮 | `quick + full + daily + experiment` 离线闭环成功 | `session_bootstrap/reports/daily_rpc_smoke_first_round.md` |
| 2026-03-01 14:44 | ARMv8 Lenovo round1 | 首轮可执行链路成功（mock payload） | `session_bootstrap/reports/daily_rpc_armv8_lenovo_round1.md` |
| 2026-03-01 16:09 | ARMv8 Phytium readiness | 配置检查 PASS（非 realcmd） | `session_bootstrap/reports/readiness_rpc_armv8_phytium_2026-03-01.md` |
| 2026-03-01 16:50 | ARMv8 Phytium round1 | quick/full 成功（远端工件/DB 校验型 payload） | `session_bootstrap/reports/daily_rpc_armv8_phytium_round1.md` |
| 2026-03-01 17:17 | ARMv8 Phytium realcmd readiness | 真实 TVM 命令 readiness PASS | `session_bootstrap/reports/readiness_rpc_armv8_phytium_realcmd_2026-03-01.md` |
| 2026-03-01 17:20 | quick realcmd round1 | 成功，baseline/current 各 1 个有效样本 | `session_bootstrap/reports/quick_rpc_armv8_phytium_realcmd_round1.md` |
| 2026-03-01 17:54 | full realcmd round1 | `failed_current`，根因为 batch 维度与模型静态 shape 不匹配 | `session_bootstrap/reports/full_rpc_armv8_phytium_realcmd_round1.md` / `session_bootstrap/logs/full_rpc_armv8_phytium_realcmd_round1.log` |
| 2026-03-01 18:12 | full realcmd round2（修复后） | `success`，batch 固定 1，仅改 SNR（10->12） | `session_bootstrap/reports/full_rpc_armv8_phytium_realcmd_round1.md` / `session_bootstrap/reports/daily_rpc_armv8_phytium_realcmd_round2.md` |
| 2026-03-08 00:13 | 飞腾派 TVM 0.24 / Python 3.10 迁移 | `tvm_samegen_20260307` 已可在 `/home/user/anaconda3/envs/tvm310/bin/python` 下正常 `import tvm`；旧 `/home/user/venv/bin/python`（3.9.5）不兼容 | `session_bootstrap/reports/phytium_tvm24_python310_migration_2026-03-08.md` |
| 2026-03-08 02:31 | 飞腾派 target 复核 + artifact 重建 | 采用 `generic + neon + num-cores=4`；修复 warm-start DB sanitize；本地重建 `optimized_model.so` 成功；live SSH/quick 因 sandbox socket 限制未完成 | `session_bootstrap/reports/phytium_target_revalidation_2026-03-08.md` |
| 2026-03-08 02:50 | 旧 JSCC 路径对比 + deploy 逻辑修复 | 旧 compile target 本就为 `generic + neon`；修复 `run_rpc_tune.sh` 在 SSH 失败时仍误报 deploy success；再次本地重建成功，远端 quick 首跳 SSH 失败 | `session_bootstrap/reports/phytium_legacy_path_vs_session_bootstrap_2026-03-08.md` |
| 2026-03-10 01:46 | 飞腾派 safe 0.24dev runtime 路径打通 | 重新编出保守 TVM 主库；定位 `SIGILL` 实际来自 `torch/libc10.so` 被 `tvm_ffi` 可选导入链拖入；在 `tvm310_safe` 中重建 `tvm_ffi.core` 并移开 torch 后，`import tvm` 成功（`0.24.dev0`） | `session_bootstrap/reports/phytium_tvm24_rebuild_plan_and_llvm_matrix_20260309.md` |
| 2026-03-10 02:12 | current target 真机比较收敛 | 在飞腾派 `safe runtime + current artifact` 真正 VM 推理下，`generic + neon` 明显偏保守；推荐默认 target 收敛到 `cortex-a72 + neon`，更激进的 `cortex-a72 + neon + crypto + crc` 有更好 median 但抖动更大 | `session_bootstrap/reports/phytium_current_target_comparison_safe_runtime_20260310.md` |
| 2026-03-10 03:03 | current-safe 一键路径实跑成功 | 一键脚本已完整跑通“本地重编 -> 上传校验 -> safe 真机推理”，但其语义现已明确为“复用历史 DB 的 `total_trials=0` rebuild-only baseline-seeded warm-start current”；`run_median_ms=2485.464` 只能作为该基线的执行证据 | `session_bootstrap/reports/phytium_current_safe_one_shot_smoke_20260310.md` |
| 2026-03-10 03:17 | current-safe 双 target compare 实跑成功（现已重分类） | compare helper 当时已能连跑 stable/experimental 两组，但两次都属于 `total_trials=0` rebuild-only 且产出相同 `optimized_model.so sha256`；因此这次 smoke compare 现应视为**无效 target 对比**，不能继续当作 target 差异证据 | `session_bootstrap/reports/phytium_current_safe_target_compare_smoke_20260310.md` |
| 2026-03-10 03:50 | current-safe compare 补采 raw samples（现已重分类） | 补采样证明 payload 已能落 `run_samples_ms`，但 stable/experimental 依旧产出相同 `optimized_model.so sha256`；因此该次 compare 同样只证明“rebuild-only 路线可重复执行”，**不证明 target 真的编出了不同 artifact** | `session_bootstrap/reports/phytium_current_safe_target_compare_samples_20260310.md` |
| 2026-03-10 18:28 | current compare 有效性修正 + warm-start incremental 入口补齐 | compare 入口新增“不同 target 但相同 artifact hash => invalid”安全阀；新增 baseline-seeded warm-start current incremental 入口与专用 env，默认复用历史 DB 且要求 nonzero budget + `rpc` runner，再走 safe runtime 验证 | `session_bootstrap/scripts/run_phytium_current_safe_target_compare.sh` / `session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh` / `session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env` |
| 2026-03-11 07:16 | baseline-vs-current-safe 最终 inference compare 恢复成功 | 先前 `failed_current` 的直接根因不是 payload runner 本身，而是远端 `jscc/tvm_tune_logs/optimized_model.so` 漂移；将飞腾派 current-safe 产物恢复为 2026-03-11 hotfix `.so` 后，对照 benchmark 成功落盘，baseline median `1832.1 ms`，current-safe median `2480.189 ms` | `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_final_20260311_024434.md` / `session_bootstrap/reports/inference_currentsafe_artifact_guard_handoff_20260311.md` |
| 2026-03-11 07:56 | current-safe artifact SHA guard 真机验证成功 | inference current-safe 路径现会在远端执行前计算并校验 `optimized_model.so` SHA；飞腾派真实 smoke 已验证 `artifact_sha256=d8e801...` 且 `artifact_sha256_match=true`，说明后续远端 artifact 漂移会在 guard 边界直接 fail fast | `session_bootstrap/reports/inference_currentsafe_guard_validation_20260311_0756.md` / `session_bootstrap/scripts/run_remote_tvm_inference_payload.sh` / `session_bootstrap/scripts/run_inference_benchmark.sh` |

## 2) 已完成项 / 阻断项

### 已完成项

- 脚手架闭环：`check/readiness/quick/full/daily/experiment` 全流程脚本已可落盘。
- ARMv8 真机参数模板与 runbook 完整：`config/`、`scripts/`、`runbooks/` 已打通。
- realcmd 级 quick 已跑通：`status=success`，说明远端 Python/TVM/输入目录/输出目录链路可用。
- full realcmd baseline 已成功执行，说明 `tvm_002.py + batch=1` 路径本身可运行。

### 当前阻断项（P0）

- **baseline 与 current 运行时已确认分叉**：
  - baseline 仍依赖旧 compat runtime 路径；
  - current 已验证应走 `tvm310_safe + safe 0.24.dev0 runtime`。
- **remote current-safe artifact 身份现在必须显式受控**：
  - 2026-03-11 的 `failed_current` 已确认由远端 `optimized_model.so` 漂移触发；
  - 当前 inference 路径已支持 `INFERENCE_CURRENT_EXPECTED_SHA256`，且 safe env 默认已写入 hotfix SHA `d8e801eeb25a87d340311015fe475f00d0f324dacd88bd5936654d3eedd03cc6`；
  - 若未来 intentional deploy 新 current-safe artifact，必须先记录新 SHA，再更新 env 后才可跑 benchmark。
- **current compare 的旧结论需要继续收口**：
  - 2026-03-10 的两次 current-safe target compare 都是 `total_trials=0` rebuild-only；
  - stable/experimental 当时生成了相同 `optimized_model.so sha256`，所以这些 compare 现在必须视为 invalid，而不是“实验 target 有轻微快慢差异”的证据。
- safe 路径已经可用，但如果未来重新把 `torch` 暴露回 safe env import 路径，`tvm_ffi` 可能再次被 `torch/libc10.so` 触发 `SIGILL`；当前应优先复用已落盘的 safe wrapper / one-shot 入口，而不是直接手工调用原始 `tvm310` 环境。

## 3) 失败原因与修复经验（可复用）

### 本次 full current 失败原因（shape[0]=1 vs batch=4）

- 失败发生在 realcmd round1 的 full current：
  - `FULL_CURRENT_CMD` 传入 `--batch_size "$REMOTE_BATCH_CURRENT"`，当时值为 `4`。
  - TVM VM 报错：`annotation=R.Tensor((1, 32, 32, 32), dtype="float32")`，并提示 `input_shape[i] == reg (4 vs. 1)`。
- 结论：模型入口 batch 维度是编译期固定常量 `1`；运行时传 `4` 会在 `match_cast` 阶段直接失败。

### 可复用修复经验

- 经验 1：单变量实验前先确认“变量是否在模型输入契约内可变”。对当前模型，`batch_size` 不是可变维。
- 经验 2：当目标是“单变量对比”，命令模板里 baseline/current 应只差 1 个参数，其他参数显式固定。
- 经验 3：先做低成本 check（变量审计 + readiness），再跑 full，能显著减少长任务失败成本。
- 经验 4：daily 文案中要同步更新 `DAILY_SINGLE_CHANGE`，保证报告结论与实际变量一致。

## 4) 当前推荐配置基线

以下为当前推荐基线（current-safe 路线优先，且必须明确区分“历史 DB / rebuild-only / incremental”三层语义）：

- **current 默认 target**：`{"kind":"llvm","mtriple":"aarch64-linux-gnu","mcpu":"cortex-a72","mattr":["+neon"],"num-cores":4}`
- **current 继续实验 target**：`{"kind":"llvm","mtriple":"aarch64-linux-gnu","mcpu":"cortex-a72","mattr":["+neon","+crypto","+crc"],"num-cores":4}`
- **历史 seed DB**：`./session_bootstrap/tmp/rpc_tune_output_20260306_195752/tuning_logs`
- **baseline-seeded warm-start current（rebuild-only 基线）**：
  - 入口：`bash ./session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh`
  - 语义：复用历史 DB，`total_trials=0`，只验证“当前 artifact + safe runtime”执行路径
- **baseline-seeded warm-start current（incremental 真实增量）**：
  - 入口：`bash ./session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh`
  - 语义：复用同一份历史 DB，但要求 nonzero `total_trials` + `rpc` runner，再通过 safe runtime 做最终执行验证
- **current 远端 Python/runtime**：
  - `REMOTE_TVM_PYTHON='env TVM_FFI_DISABLE_TORCH_C_DLPACK=1 LD_LIBRARY_PATH=/home/user/anaconda3/envs/tvm310_safe/lib/python3.10/site-packages/tvm_ffi/lib:/home/user/tvm_samegen_safe_20260309/build TVM_LIBRARY_PATH=/home/user/tvm_samegen_safe_20260309/build PYTHONPATH=/home/user/tvm_samegen_20260307/python:/home/user/anaconda3/envs/tvm310_safe/lib/python3.10/site-packages /home/user/anaconda3/envs/tvm310_safe/bin/python'`
- **current artifact identity guard**：
  - safe env 默认 expected SHA：`d8e801eeb25a87d340311015fe475f00d0f324dacd88bd5936654d3eedd03cc6`
  - current-safe 实机 smoke 已验证：`artifact_sha256_match=true`
- **baseline runtime**：仍走 compat 路径，不要和 current-safe 混用
- **current target compare 有效性规则**：
  - 只有在不同 target 产出不同 `optimized_model.so` hash 时，compare 才有效；
  - 2026-03-10 的 smoke/sample compare 因 hash 相同已被正式重分类为 invalid。
- 输入目录：`/home/user/Downloads/jscc-test/简化版latent`

当前最推荐的直接入口（rebuild-only 基线）：

```bash
bash ./session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh
```

如需真正推进下一阶段的 nonzero-budget current 增量调优：

```bash
bash ./session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh
```

如果要一次比较 stable/experimental 两组 current-safe target（且在 artifact hash 相同时应直接视为 invalid）：

```bash
bash ./session_bootstrap/scripts/run_phytium_current_safe_target_compare.sh
```

## 5) 最小可执行命令集（check/readiness/full/daily）

默认环境文件：

```bash
ENV=./session_bootstrap/config/rpc_armv8.phytium_pi.2026-03-01.env
```

### check（先做单变量配置审计）

```bash
rg -n 'REMOTE_SNR_BASELINE|REMOTE_SNR_CURRENT|REMOTE_BATCH_BASELINE|REMOTE_BATCH_CURRENT|FULL_BASELINE_CMD|FULL_CURRENT_CMD|DAILY_SINGLE_CHANGE|DAILY_NEXT_CHANGE' "$ENV"
```

### readiness（执行前门禁）

```bash
bash ./session_bootstrap/scripts/check_rpc_readiness.sh --env "$ENV"
```

### full（夜间热点主执行）

```bash
bash ./session_bootstrap/scripts/run_full_placeholder.sh --env "$ENV"
```

### daily（汇总当日结论）

```bash
bash ./session_bootstrap/scripts/summarize_to_daily.sh \
  --env "$ENV" \
  --date "$(date +%F)" \
  --output ./session_bootstrap/reports/daily_rpc_armv8_phytium_realcmd_round2.md
```

可选：若希望先做运行态 check，再跑 full，可先补一条 quick：

```bash
bash ./session_bootstrap/scripts/run_quick.sh --env "$ENV"
```

## 6) 下一步行动清单

### P0（必须先完成）

1. 在飞腾派上用 `run_phytium_baseline_seeded_warm_start_current_incremental.sh` 跑第一轮真实 nonzero-budget current 增量调优，并保留输出 DB，不要再把 `run_phytium_current_safe_one_shot.sh` 误写成“独立 fresh current 结果”。
2. 后续任何 baseline-vs-current-safe inference / smoke / compare 执行前，都保留并核对 `INFERENCE_CURRENT_EXPECTED_SHA256`；若 intentional deploy 新 current-safe artifact，先记新 SHA，再更新 env。
3. 继续以 `cortex-a72 + neon` 作为默认 current target；更激进的 `+crypto,+crc` 只保留为受控实验分支，并且 compare 必须通过 artifact hash 差异校验才算有效。
4. 如果后续需要把 safe 路线重新产品化，先把 `torch` 对 `tvm_ffi` 的污染隔离策略（或 `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` 的强制入口）固化到更上层的统一运行封装里。

### P1（稳定性与扩展）

1. 在后续 compare 中继续保留 `run_samples_ms`，但只有在 artifact hash 不同的前提下，才讨论 `cortex-a72 + neon + crypto + crc` 的优势/抖动是否能**稳定复现**。
2. 把 rebuild-only one-shot、incremental current、compare 输出分别纳入 daily/experiment 汇总，避免三种语义在文案里混淆成同一条“current 结果”。
3. 如需最终替换长期默认配置，再评估是否把旧 `generic + neon` 文档/模板整体退役，避免误用。
4. 将本文件作为每次 round 后唯一“进度真相源”持续更新（含失败栈摘要、artifact hash 结论与 compare 有效性状态）。
