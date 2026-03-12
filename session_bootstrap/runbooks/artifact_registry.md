# 产物 / 脚本 / 路径索引（当前可信工程入口）

更新时间：`2026-03-12`
适用范围：飞腾派 current-safe / baseline 对比、增量调优、真实重建复现

这份文档的目的很直接：把**当前最重要的产物、脚本、报告和路径**固定下来，后续要复现、汇报、继续优化时，不用再翻聊天记录。

---

## 1. 当前可信结论（先看这个）

### 1.1 payload 级推理：current 已显著优于 baseline

核心报告：
- `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md`

关键结果：
- baseline median: `1844.1 ms`
- current-safe median: `153.778 ms`
- improvement: `91.66%`
- current artifact SHA256: `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644`

### 1.2 真实端到端重建：current 已显著优于 baseline

核心报告：
- `session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md`

关键结果：
- baseline median: `1830.3 ms/image`
- current median: `255.931 ms/image`
- improvement: `86.02%`
- current artifact SHA256: `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644`

### 1.3 增量调优的工程收益已经被验证

核心报告：
- `session_bootstrap/reports/current_scheme_b_compare_20260311_195303.md`
- `session_bootstrap/reports/phytium_current_incremental_breakthrough_20260311.md`

关键结果：
- rebuild-only current median: `2479.246 ms`
- incremental current median: `152.36 ms`
- incremental vs rebuild-only improvement: `93.85%`
- speedup: `16.272x`

---

## 2. 当前可信 current 产物

### 2.1 本地产物（推荐基准 artifact）

- local optimized model:
  - `session_bootstrap/tmp/phytium_baseline_seeded_warm_start_current_incremental_20260311_094548/optimized_model.so`
- SHA256:
  - `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644`
- 产物说明：
  - 第一条成功打通的 **baseline-seeded warm-start current incremental** 产物
  - 已完成：非零预算 tuning → 本地编译 → 远端上传 → safe runtime 验证 → baseline/current 正式对比

### 2.2 远端部署产物（飞腾派）

- remote archive root:
  - `/home/user/Downloads/jscc-test/jscc`
- remote current `.so`:
  - `/home/user/Downloads/jscc-test/jscc/tvm_tune_logs/optimized_model.so`
- remote tuning logs:
  - `/home/user/Downloads/jscc-test/jscc/tuning_logs`
- remote workload db:
  - `/home/user/Downloads/jscc-test/jscc/tuning_logs/database_workload.json`
- remote tuning record db:
  - `/home/user/Downloads/jscc-test/jscc/tuning_logs/database_tuning_record.json`

### 2.3 current 产物身份保护

用于 current-safe 复现时，优先使用：
- `session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env`

其中应维护：
- `INFERENCE_CURRENT_EXPECTED_SHA256=1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644`

原则：
- 只要远端 `.so` 有更新，就必须同步更新 expected SHA；
- 没有 SHA guard 的 current-safe benchmark，不应当视为最终可信结论。

---

## 3. 关键脚本：按用途找入口

### 3.1 登录 / 基础连接

- 登录飞腾派：
  - `session_bootstrap/scripts/connect_phytium_pi.sh`
- SSH 包装：
  - `session_bootstrap/scripts/ssh_with_password.sh`

### 3.2 current-safe 复现与调优

- baseline-seeded rebuild-only current：
  - `session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh`
- baseline-seeded warm-start current 增量调优：
  - `session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh`
- baseline-style payload-symmetric rebuild-only current：
  - `session_bootstrap/scripts/run_phytium_baseline_style_current_rebuild.sh`
- current-safe 双 target 对比：
  - `session_bootstrap/scripts/run_phytium_current_safe_target_compare.sh`

### 3.3 benchmark / 推理验证

- payload 级对比：
  - `session_bootstrap/scripts/run_inference_benchmark.sh`
- current-safe payload runner：
  - `session_bootstrap/scripts/run_remote_tvm_inference_payload.sh`
- legacy baseline runner：
  - `session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh`
- 真实端到端 current runner：
  - `session_bootstrap/scripts/run_remote_current_real_reconstruction.sh`
- 真实端到端 Python 入口：
  - `session_bootstrap/scripts/current_real_reconstruction.py`

### 3.4 MetaSchedule / RPC 基础设施

- RPC tune 主入口：
  - `session_bootstrap/scripts/rpc_tune.py`
- 一键编排 tune + deploy + validate：
  - `session_bootstrap/scripts/run_rpc_tune.sh`
- RPC 服务管理：
  - `session_bootstrap/scripts/manage_rpc_services.sh`
- readiness 检查：
  - `session_bootstrap/scripts/check_rpc_readiness.sh`
- 热点 task 提取：
  - `session_bootstrap/scripts/extract_hotspot_tasks.py`
- hotspot 微基准：
  - `session_bootstrap/scripts/run_hotspot_micro_benchmark.sh`

---

## 4. 关键 env / 配置文件

### 4.1 当前推荐 current-safe 推理 env

- `session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env`

用途：
- safe runtime current 推理
- current SHA guard
- one-shot / incremental 产物验证

### 4.2 当前推荐 rebuild-only env

- `session_bootstrap/config/rpc_tune_rebuild_current_safe.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env`

用途：
- baseline-seeded rebuild-only current 基线
- 推荐 target：`cortex-a72 + neon`

### 4.3 当前推荐 incremental env

- `session_bootstrap/config/rpc_tune_current_safe.baseline_seeded_warm_start.recommended_cortex_a72_neon.2026-03-10.phytium_pi.env`

用途：
- 非零预算 current 增量调优
- warm-start 复用已有 tuning DB

### 4.4 payload-symmetric fair compare env

- `session_bootstrap/config/inference_compare_scheme_a_fair.2026-03-11.phytium_pi.env`

用途：
- 避免 legacy/current mixed 路径
- 用更公平的 payload runner 比较 current rebuild-only / incremental

### 4.5 第一轮真实 RPC tune 拓扑参考 env

- `session_bootstrap/config/rpc_tune_real.2026-03-09.phytium_pi.env`

用途：
- 远端 tracker + 远端 runner + 本地 builder/orchestrator

---

## 5. 关键报告：按问题找证据

| 你想回答的问题 | 看哪个报告 |
|---|---|
| current 是否真的快过 baseline？ | `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md` |
| current 的真实端到端重建是否也更快？ | `session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md` |
| incremental 是否真的比 rebuild-only 更强？ | `session_bootstrap/reports/current_scheme_b_compare_20260311_195303.md` |
| 本轮突破的总结版结论是什么？ | `session_bootstrap/reports/phytium_current_incremental_breakthrough_20260311.md` |
| 当前 target 选择为什么倾向 cortex-a72 + neon？ | `session_bootstrap/reports/phytium_current_target_comparison_safe_runtime_20260310.md` |
| Python 入口为什么切到 tvm310_safe / Python 3.10？ | `session_bootstrap/reports/phytium_tvm24_python310_migration_2026-03-08.md` |
| baseline/current artifact 路径和 guard 语义怎么演化的？ | `session_bootstrap/reports/inference_currentsafe_artifact_guard_handoff_20260311.md` |

---

## 6. 典型复现路径（最常用）

### 6.1 只验证当前 trusted current artifact 是否还稳定

```bash
bash session_bootstrap/scripts/run_inference_benchmark.sh \
  --env session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env
```

你应该重点检查：
- `current_artifact_sha256_match`
- `current_run_median_ms`
- `current_run_variance_ms2`

### 6.2 从 rebuild-only 重新建立 current 基线

```bash
bash session_bootstrap/scripts/run_phytium_current_safe_one_shot.sh
```

### 6.3 继续做 current 增量调优

```bash
bash session_bootstrap/scripts/run_phytium_baseline_seeded_warm_start_current_incremental.sh
```

### 6.4 跑真实端到端重建对比

```bash
bash session_bootstrap/scripts/run_inference_benchmark.sh \
  --env session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env
```

---

## 7. 路径管理约定

### 7.1 本地

- 脚本：`session_bootstrap/scripts/`
- 配置：`session_bootstrap/config/`
- 报告：`session_bootstrap/reports/`
- 日志：`session_bootstrap/logs/`
- 临时编译产物：`session_bootstrap/tmp/<report_id>/`

### 7.2 远端飞腾派

- 项目根：`/home/user/Downloads/jscc-test/jscc`
- current archive：`/home/user/Downloads/jscc-test/jscc/tvm_tune_logs`
- baseline/legacy 路径：沿 `tvm_002.py` / compat runner 既有目录约定，不与 current-safe archive 混写

### 7.3 命名规则建议

- 新报告：`<主题>_<YYYYMMDD_HHMMSS>.md`
- 新 env 快照：`session_bootstrap/tmp/<run_id>.env`
- 新 current 产物目录：`session_bootstrap/tmp/<report_id>/`
- 新 trusted artifact：必须同步记录 `.so path + SHA256 + 对应报告`

---

## 8. 下一步优化该从哪里继续

最值得继续投入的顺序：

1. **先稳住当前 trusted SHA**
   - 对 `1946...c644` 再做 2–3 次 payload benchmark 复跑
   - 确认 `~154 ms` 延迟带稳定，不是偶然波动
2. **继续做 warm-start incremental**
   - 在同一条 DB 链上把预算从 `500 -> 1000 -> 2000`
   - 观察边际收益是否还显著
3. **做热点 task 定位和定向预算投放**
   - 用 `extract_hotspot_tasks.py` 导出 task 权重
   - 如果总提升趋缓，就把预算从“全局均摊”转向“热点集中”
4. **分离 payload 优化与端到端优化**
   - payload 已经到 `152 ms` 量级
   - 端到端是 `255 ms`，中间仍有前后处理、I/O、图片读写和 pipeline 开销可挖
5. **若 MetaSchedule 边际收益变平，再转 INT8 / 模型级优化**
   - 量化、算子融合、结构裁剪会比继续硬堆搜索预算更划算

更详细的优化计划见：
- `session_bootstrap/runbooks/optimization_roadmap.md`

---

## 9. 维护规则

每当出现以下任一情况，必须同步更新这份索引：
- trusted current artifact SHA 变了；
- 推荐 env 变了；
- 复现主入口脚本变了；
- 新结论取代了旧 benchmark；
- 远端 archive 路径变了。
