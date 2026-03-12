# 下一轮性能优化执行清单（飞腾派 / TVM current-safe）

更新时间：`2026-03-12`  
适用范围：飞腾派 current-safe / MetaSchedule 下一轮继续优化；只沿当前 trusted current workflow 推进，不从零换线。

---

## 0. 推荐顺序（按这个跑）

1. **稳定性复跑**
2. **增量调优加到 `1000` trials**
3. **提取热点 task**
4. **做真实端到端分段计时**

不要把这四步打乱。  
先确认 `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644` 这条 trusted current artifact 线还能稳定复现，再讨论更大预算或新的热点定向。

---

## 1. 目标与范围

### 1.1 本轮目标

- 稳住当前 trusted current artifact，避免后续 A/B 基准漂移。
- 在 **baseline-seeded warm-start current incremental** 线上，把 `TUNE_TOTAL_TRIALS` 从 `500` 提到 `1000`，判断是否还有明确边际收益。
- 把“继续盲目堆全局预算”切到“热点 task 定向”。
- 把 payload 优势继续转化为真实端到端优势，先拿到分段计时证据，再决定优化点。

### 1.2 本轮不做什么

- 不切换到新的 runtime 线。
- 不同时改 target、runner、模型结构、输入语义。
- 不在没有 SHA guard 的情况下接受 current-safe benchmark 结论。
- 不把新 `.so` 直接写进 trusted 入口，除非已经完成带新 SHA guard 的复验。

---

## 2. 当前 trusted baseline（本轮固定参照）

| 项目 | 固定值 | 用途 |
|---|---|---|
| trusted current 本地产物 | `session_bootstrap/tmp/phytium_baseline_seeded_warm_start_current_incremental_20260311_094548/optimized_model.so` | 本轮所有 compare 的 current 基线 |
| trusted current SHA256 | `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644` | current 身份保护 |
| trusted current 远端路径 | `/home/user/Downloads/jscc-test/jscc/tvm_tune_logs/optimized_model.so` | 飞腾派 current archive |
| trusted payload 报告 | `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md` | `1844.1 -> 153.778 ms` |
| trusted 真实端到端报告 | `session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md` | `1830.3 -> 255.931 ms/image` |
| trusted 增量突破总结 | `session_bootstrap/reports/phytium_current_incremental_breakthrough_20260311.md` | 当前 trusted artifact 的总结入口 |
| payload 复跑推荐 env 快照 | `session_bootstrap/tmp/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.env` | 已固定 `repeat=10`、`warmup=2`、payload runner |
| 真实端到端推荐 env 快照 | `session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env` | 已固定 current real reconstruction 语义 |
| 增量调优推荐 env | `session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env` | 下一轮 `1000` trial 入口 |
| safe runtime guard 基础 env | `session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env` | current SHA guard 的基础配置 |

本轮判断一律先对齐上表。  
没有绑定到 `session_bootstrap/reports/` 下新报告的结果，不视为可信资产。

---

## 3. 开跑前检查

### 3.1 本地 trusted artifact 与 SHA

命令模板：

```bash
sha256sum \
  session_bootstrap/tmp/phytium_baseline_seeded_warm_start_current_incremental_20260311_094548/optimized_model.so
```

预期输出：

- 第一列必须是 `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644`

通过标准：

- `actual_sha == trusted_sha`

失败判定：

- 文件不存在
- SHA 不等于 trusted SHA

需要记录：

- `artifact_path`
- `actual_sha`
- 文件大小

### 3.2 关键 env 快照仍然对齐 trusted 基线

命令模板：

```bash
rg -n \
  'INFERENCE_CURRENT_EXPECTED_SHA256|INFERENCE_CURRENT_CMD|INFERENCE_REPEAT|INFERENCE_WARMUP_RUNS|INFERENCE_OUTPUT_PREFIX' \
  session_bootstrap/tmp/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.env \
  session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env
```

预期输出：

- payload env 里有：
  - `INFERENCE_CURRENT_EXPECTED_SHA256=1946...c644`
  - `INFERENCE_CURRENT_CMD='bash ./session_bootstrap/scripts/run_remote_tvm_inference_payload.sh --variant current'`
  - `INFERENCE_REPEAT=10`
  - `INFERENCE_WARMUP_RUNS=2`
- real env 里有：
  - `INFERENCE_CURRENT_EXPECTED_SHA256=1946...c644`
  - `INFERENCE_CURRENT_CMD='bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current'`

通过标准：

- 两个 env 都仍然 pin 到 trusted SHA
- payload / real reconstruction runner 没有混写

失败判定：

- SHA guard 被改掉
- payload env 又退回 legacy current runner
- 真实端到端 env 不再走 `run_remote_current_real_reconstruction.sh`

需要记录：

- 本轮实际使用的 env 路径
- 是否是 trusted env 的复制版

### 3.3 RPC readiness

命令模板：

```bash
bash session_bootstrap/scripts/check_rpc_readiness.sh \
  --env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env
```

预期输出：

- checklist 项为“满足”
- 无阻断项
- 脚本退出码为 `0`

通过标准：

- `rc=0`

失败判定：

- 任一 blocker
- tracker / runner / remote 配置缺失

需要记录：

- readiness 输出文件路径（如果单独落盘）
- 是否有 blocker

### 3.4 RPC 服务状态

命令模板：

```bash
bash session_bootstrap/scripts/manage_rpc_services.sh \
  --env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env \
  status
```

如未启动，再执行：

```bash
bash session_bootstrap/scripts/manage_rpc_services.sh \
  --env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env \
  start-all
```

预期输出：

- `Tracker ... LISTENING`
- `Runner ... LISTENING`
- `Tracker query:` 能返回 devices 摘要

通过标准：

- tracker 和 runner 都可达

失败判定：

- `NOT RUNNING`
- `UNREACHABLE`
- tracker query failed

需要记录：

- tracker host/port
- runner 端口范围
- 是否执行了 `start-all`

### 3.5 命名与覆写保护

命令模板：

```bash
date +%Y%m%d_%H%M%S
```

执行规则：

- 每一步都生成新的 `RUN_ID`
- 每一步都复制 trusted env 快照，不直接覆写 trusted env
- 默认保持 `ALLOW_REPORT_OVERWRITE=0`

通过标准：

- 本轮不会覆盖 `20260311` trusted 报告

失败判定：

- 重用旧 `INFERENCE_EXECUTION_ID`
- 直接覆写 trusted env / trusted report

需要记录：

- `RUN_ID`
- 新 env 快照路径

---

## 4. Step 1：稳定性复跑

目标：

- 先确认 trusted SHA 这条线还稳定。
- 本步只允许复跑，不引入新的 target / target flags / 调优 DB 改动。

### 4.1 payload 级稳定性复跑（必做，至少 `2–3` 次）

命令模板：

```bash
for i in 1 2 3; do
  RUN_ID="inference_compare_baseline_vs_currentsafe_stability_${i}_$(date +%Y%m%d_%H%M%S)"
  ENV_COPY="session_bootstrap/tmp/${RUN_ID}.env"
  cp session_bootstrap/tmp/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.env "$ENV_COPY"
  sed -i \
    -e "s#^INFERENCE_EXECUTION_ID=.*#INFERENCE_EXECUTION_ID=${RUN_ID}#" \
    -e "s#^ALLOW_REPORT_OVERWRITE=.*#ALLOW_REPORT_OVERWRITE=0#" \
    "$ENV_COPY"
  bash session_bootstrap/scripts/run_inference_benchmark.sh --env "$ENV_COPY"
done
```

预期输出：

- 每次都生成：
  - `session_bootstrap/logs/<run_id>.log`
  - `session_bootstrap/reports/<run_id>.md`
  - `session_bootstrap/reports/<run_id>_raw.csv`
- 报告内关键字段应出现：
  - `current_artifact_sha256_match: True`
  - `current_artifact_sha256: 1946...c644`
  - `current_run_median_ms`
  - `current_run_variance_ms2`
  - `delta_ms_current_minus_baseline`

通过标准：

- 每次 `current_artifact_sha256_match=True`
- 至少 `2/3` 次 `current_run_median_ms` 仍在 `~154 ms` 邻域
- `current_run_variance_ms2` 仍处于低方差量级，不明显失控

建议采用的硬门槛：

- `current_run_median_ms <= 160`
- `current_run_variance_ms2 <= 5`

失败判定：

- 任一次 SHA mismatch
- 任一次脚本失败
- 连续两次 median 明显高于 trusted 报告 `153.778 ms`

需要记录：

- 每次 `run_id`
- `current_run_median_ms`
- `current_run_max_ms`
- `current_run_variance_ms2`
- `current_artifact_sha256`
- 板子状态备注：是否有后台负载 / 温度 / 频率干扰

### 4.2 真实端到端稳定性复跑（选做，保持代码零改动）

如果只是补 1 次无代码改动复跑，可直接执行：

```bash
RUN_ID="inference_real_reconstruction_stability_$(date +%Y%m%d_%H%M%S)"
ENV_COPY="session_bootstrap/tmp/${RUN_ID}.env"
cp session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env "$ENV_COPY"
sed -i \
  -e "s#^INFERENCE_EXECUTION_ID=.*#INFERENCE_EXECUTION_ID=${RUN_ID}#" \
  -e "s#^INFERENCE_OUTPUT_PREFIX=.*#INFERENCE_OUTPUT_PREFIX=${RUN_ID}#" \
  -e "s#^INFERENCE_LEGACY_OUTPUT_PREFIX=.*#INFERENCE_LEGACY_OUTPUT_PREFIX=${RUN_ID}#" \
  "$ENV_COPY"
bash session_bootstrap/scripts/run_inference_benchmark.sh --env "$ENV_COPY"
```

预期输出：

- 报告中仍能看到：
  - `current_artifact_sha256_match: True`
  - `current_run_median_ms`
  - `current_run_max_ms`
  - `current_run_variance_ms2`

通过标准：

- `current_artifact_sha256_match=True`
- `current_run_median_ms` 仍显著低于 baseline `1830.3 ms/image`

失败判定：

- current 端 SHA mismatch
- `processed_count` 或输出数量异常

需要记录：

- `current_run_median_ms`
- `current_run_max_ms`
- `current_run_variance_ms2`
- 输出目录与文件数

---

## 5. Step 2：增量调优加到 `1000` trials

目标：

- 沿 **baseline-seeded warm-start current incremental** 线继续推进。
- 先拿到可验证的新 `.so`，再决定是否晋升 trusted。

### 5.1 先跑 `1000` trials

命令模板：

```bash
RUN_ID="phytium_baseline_seeded_warm_start_current_incremental_1000_$(date +%Y%m%d_%H%M%S)"

bash session_bootstrap/scripts/manage_rpc_services.sh \
  --env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env \
  start-all

bash session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh \
  --rebuild-env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env \
  --inference-env session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env \
  --total-trials 1000 \
  --report-id "$RUN_ID" \
  --repeat 10 \
  --warmup-runs 2
```

预期输出：

- wrapper log：
  - `session_bootstrap/logs/${RUN_ID}_wrapper.log`
- 本地产物目录：
  - `session_bootstrap/tmp/${RUN_ID}/`
- 新 `.so`：
  - `session_bootstrap/tmp/${RUN_ID}/optimized_model.so`
- 可能的两类脚本结局：
  1. 直接成功，说明新产物 SHA 恰好仍满足当前 inference env 的 guard；
  2. 因 `artifact sha256 mismatch expected=<old> actual=<new>` 退出，这通常表示**新产物已经生成，但 inference env 仍 pin 在旧 SHA**。

通过标准：

- tuning / build / upload 完成
- `optimized_model.so` 存在
- 有新 report / log / output dir

失败判定：

- tuning 失败
- 本地编译失败
- 远端上传失败
- 没有新 `.so`

需要记录：

- `RUN_ID`
- `TUNE_TOTAL_TRIALS=1000`
- 新本地产物目录
- 新 `.so` SHA256
- wrapper 最终状态：成功 / guard hit / 真失败

### 5.2 如果命中了旧 SHA guard，立刻做新 SHA 复验

命令模板：

```bash
NEW_ARTIFACT="session_bootstrap/tmp/${RUN_ID}/optimized_model.so"
NEW_SHA="$(sha256sum "$NEW_ARTIFACT" | awk '{print $1}')"
VALIDATE_ID="inference_compare_currentsafe_1000_validate_$(date +%Y%m%d_%H%M%S)"
ENV_COPY="session_bootstrap/tmp/${VALIDATE_ID}.env"

cp session_bootstrap/tmp/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.env "$ENV_COPY"
sed -i \
  -e "s#^INFERENCE_EXECUTION_ID=.*#INFERENCE_EXECUTION_ID=${VALIDATE_ID}#" \
  -e "s#^INFERENCE_CURRENT_EXPECTED_SHA256=.*#INFERENCE_CURRENT_EXPECTED_SHA256=${NEW_SHA}#" \
  -e "s#^ALLOW_REPORT_OVERWRITE=.*#ALLOW_REPORT_OVERWRITE=0#" \
  "$ENV_COPY"

bash session_bootstrap/scripts/run_inference_benchmark.sh --env "$ENV_COPY"
```

预期输出：

- 新验证报告写入 `session_bootstrap/reports/${VALIDATE_ID}.md`
- 关键字段：
  - `current_artifact_sha256=${NEW_SHA}`
  - `current_artifact_sha256_match=True`
  - `current_run_median_ms`

通过标准：

- `current_artifact_sha256_match=True`
- 新产物至少不回退

推荐晋升 trusted 的门槛：

- 相比 trusted payload `153.778 ms`，稳定收益 **大于 `3%`**
- 或至少同等性能，但方差更低、tail 更短

失败判定：

- 改成新 SHA 后仍 mismatch
- median 明显回退
- 输出 shape / dtype 异常

需要记录：

- `NEW_SHA`
- 验证报告路径
- `current_run_median_ms`
- `current_run_variance_ms2`
- 相比 trusted `153.778 ms` 的 delta / improvement

本步结束规则：

- 只有完成“新 SHA 复验”后，才允许讨论是否更新 `artifact_registry.md`。

---

## 6. Step 3：提取热点 task

目标：

- 不再只凭总时延猜测，把预算集中到最值钱的 task。
- 这一步是 **task 权重提取**，不是直接读取 tuning record 做 trace 对比。

命令模板：

```bash
RUN_ID="hotspot_tasks_next_round_$(date +%Y%m%d_%H%M%S)"

python session_bootstrap/scripts/extract_hotspot_tasks.py \
  --env session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env \
  --top-k 8 \
  --output "session_bootstrap/reports/${RUN_ID}.md" \
  --json-output "session_bootstrap/reports/${RUN_ID}.json"
```

预期输出：

- stdout 会打印：
  - `task_stage_used_for_recommendation=...`
  - `recommended_full_hotspot_tasks=...`
  - `markdown_report=...`
  - `json_report=...`
- 报告文件生成：
  - `session_bootstrap/reports/${RUN_ID}.md`
  - `session_bootstrap/reports/${RUN_ID}.json`

通过标准：

- 输出文件存在
- `recommended_full_hotspot_tasks` 非空
- 至少能明确前 `3–8` 个 task

失败判定：

- 生成失败
- `tasks` 为空
- target / onnx / input shape 未对齐 current-safe 推荐 env

需要记录：

- `RUN_ID`
- `task_stage_used_for_recommendation`
- top `3–8` task 名称、weight、prim_funcs
- 是否仍与 `session_bootstrap/reports/hotspot_tasks_20260311_0008.md` 同步

建议优先盯住：

- `reshape2`
- `fused_variance1_add3_tir_sqrt1`
- `reshape1`
- `fused_mean1_subtract1_divide1_multiply1_add4`
- `fused_conv2d1_add2`
- `fused_conv2d2_add2`
- `mirror_pad1`

---

## 7. Step 4：真实端到端分段计时

目标：

- 把“payload 已经很快，但端到端仍在 `255 ms` 左右”的差距拆开。
- 先拿证据，再做端到端优化。

### 7.1 先补最小计时代码

在 `session_bootstrap/scripts/current_real_reconstruction.py` 中，至少拆出下面几段：

- `preprocess_ms`：`load_latent` + `awgn_channel`
- `model_run_ms`：`fn(runtime_tensor(...))`
- `postprocess_ms`：`output.numpy()` + 图像归一化等
- `save_ms`：`save_reconstruction`

约束：

- 最后一行仍然输出 JSON summary
- 继续保留 `artifact_sha256` / `artifact_sha256_expected` / `artifact_sha256_match`
- 不改 artifact 选择逻辑，不改 current-safe runner 语义

### 7.2 跑 current-only 分段计时

命令模板：

```bash
RUN_ID="current_real_stage_timing_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="session_bootstrap/logs/${RUN_ID}.log"

set -a
source session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env
set +a

bash session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current \
  | tee "$LOG_FILE"
```

预期输出：

- stdout 最后一行是 JSON
- JSON 至少包含：
  - `artifact_sha256`
  - `artifact_sha256_match`
  - `load_ms`
  - `vm_init_ms`
  - `run_median_ms`
- 分段计时改完后，JSON 还应新增：
  - `preprocess_*`
  - `model_run_*`
  - `postprocess_*`
  - `save_*`

通过标准：

- `artifact_sha256_match=True`
- `processed_count == input_count`
- 分段字段全部存在
- 分段之和与总 `run_median_ms` / `run_mean_ms` 在可解释范围内

失败判定：

- 只有总时间，没有分段字段
- `processed_count` 少于输入数
- 保存图像数量异常
- SHA mismatch

需要记录：

- `RUN_ID`
- `artifact_sha256`
- `processed_count`
- `run_median_ms`
- 每个 stage 的 median / max / variance
- 最大瓶颈 stage
- 最大抖动 stage

本步完成后才决定端到端优化优先级：

- 如果 `model_run_ms` 仍主导，总预算继续往 TVM / 热点 task 打。
- 如果 `preprocess_ms` / `save_ms` 很大，下一轮优先做 I/O、内存复用、少落盘。

---

## 8. 本轮实验记录模板（紧凑版）

```md
# Next Round Experiment Log

- 日期：
- 操作人：
- step：稳定性复跑 / 1000 trials / hotspot / stage timing
- run_id：
- script：
- env：
- local_artifact：
- remote_artifact：
- expected_sha256：
- actual_sha256：
- sha_guard_result：pass / mismatch / not_applicable
- trusted_baseline_ref：
  - session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md
  - session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md
- 关键结果：
  - payload_median_ms：
  - payload_variance_ms2：
  - end_to_end_median_ms：
  - end_to_end_max_ms：
  - hotspot_topk：
  - stage_bottleneck：
- 结论：更快 / 持平 / 更慢 / 不可信
- 下一动作：
```

出发前勾选：

- [ ] 本轮只改一个主变量
- [ ] 仍以 trusted SHA `1946...c644` 为基线
- [ ] 使用的是 trusted env 快照或其复制版
- [ ] 新 `RUN_ID` 不会覆盖旧报告
- [ ] current-safe benchmark 带 SHA guard
- [ ] 跑完后把报告落到 `session_bootstrap/reports/`

