# TVM MetaSchedule Execution Project

基于 TVM、MNN 框架优化的 cGAN 模型轻量级图像语义通信系统 —— 飞腾派端侧部署与调优工程。

- **参赛赛事：** 第九届全国大学生集成电路创新创业大赛（飞腾杯）
- **队伍编号：** CICC0903540
- **团队名称：** 逃离荒岛队

## 当前最佳成绩

| 路线 | 指标 | 数值 |
|---|---|---|
| TVM 真实端到端重建 | baseline → current | 1834.1 → 234.219 ms/image（**87.23% 提升**） |
| TVM payload 级推理 | 中位时间 | 131.343 ms（较上一 trusted current 再快 14.59%） |
| TVM 增量调优加速比 | rebuild-only → incremental | **16.272x** |
| MNN 动态形状推理 | 加速比 | 1.85x（300 张不同尺寸图片） |

## 目录结构

```
.
├── paper/                          # 参赛文档
│   ├── CICC0903540初赛技术文档.md      # 初赛技术文档（正式提交）
│   └── 集创赛冲奖调优方案_2026-03-12.md  # 内部调优方案与执行计划
├── session_bootstrap/              # 执行脚手架（脚本、配置、日志、报告）
│   ├── scripts/                       # 执行脚本（调优、推理、部署、benchmark）
│   ├── config/                        # 环境配置（.env 文件）
│   ├── reports/                       # 实验报告与 benchmark 结果
│   ├── logs/                          # 运行日志
│   ├── runbooks/                      # 操作手册
│   ├── templates/                     # 日报与实验记录模板
│   ├── tasks/                         # 待办与优先级
│   ├── state/                         # 运行状态
│   ├── tmp/                           # 临时产物（调优输出、编译中间件）
│   ├── README.md                      # 执行命令说明
│   └── PROGRESS_LOG.md                # 进度日志（里程碑时间线）
├── TVM_LAST_understanding/         # TVM 工程结构理解文档
├── cicc_tech_doc/                  # LaTeX 版技术文档（PDF 生成）
└── README.md                      # 本文件
```

## 关键入口

| 用途 | 入口 |
|---|---|
| 了解项目全貌 | `paper/CICC0903540初赛技术文档.md` |
| 查看调优方案与执行计划 | `paper/集创赛冲奖调优方案_2026-03-12.md` |
| 查看进度与里程碑 | `session_bootstrap/PROGRESS_LOG.md` |
| 执行命令与脚本说明 | `session_bootstrap/README.md` |
| 当前成果 / 脚本 / 路径索引 | `session_bootstrap/runbooks/artifact_registry.md` |
| OpenAMP 控制面答辩证据包 | `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/README.md` |
| OpenAMP demo / 答辩材料索引 | `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/demo_materials_index.md` |
| OpenAMP demo 最新 live 双路径状态（2026-03-17） | `session_bootstrap/reports/openamp_demo_live_dualpath_status_20260317.md` |
| OpenAMP demo dashboard 本地启动验收（2026-03-17） | `session_bootstrap/reports/openamp_demo_dashboard_local_acceptance_20260317.md` |
| 启动集成 OpenAMP demo 软件 | `bash session_bootstrap/scripts/run_openamp_demo.sh` |
| OpenAMP demo 软件说明 | `session_bootstrap/demo/openamp_control_plane_demo/README.md` |
| 下一轮性能优化执行清单 | `session_bootstrap/runbooks/next_round_optimization_checklist.md` |
| 后续性能优化路线 | `session_bootstrap/runbooks/optimization_roadmap.md` |
| 飞腾派 RPC 调优 | `session_bootstrap/scripts/rpc_tune.py` |
| 真实端到端重建 benchmark | `session_bootstrap/scripts/current_real_reconstruction.py` |
| baseline vs current 推理对比 | `session_bootstrap/scripts/run_inference_benchmark.sh` |

## 当前可信产物（2026-03-13）

| 类别 | 当前可信入口 |
|---|---|
| trusted current 本地产物 | `session_bootstrap/tmp/phytium_baseline_seeded_warm_start_current_incremental_split_topup15_20260312_2000/optimized_model.so` |
| trusted current SHA256 | `65747fb301851f27892666d28daefc856c0ff2f7f85d3702779be32dde4b6377` |
| payload 基准结论 | `session_bootstrap/reports/inference_compare_currentsafe_split_topup15_validate_20260313_0002.md` |
| 速度原因说明 | `session_bootstrap/reports/trusted_current_speedup_causal_chain_20260313.md` |
| 最新真实端到端重建结论 | `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_split_topup15_20260313_003633_retry_20260313_005140.md`（`1834.1 → 234.219 ms/image`，`87.23%` 提升；相较上一 trusted current `255.931 ms/image` 再快约 `8.48%`） |
| 详细产物 / 脚本 / 路径说明 | `session_bootstrap/runbooks/artifact_registry.md` |

## 技术架构

```
上位机（笔记本）                          飞腾派（端侧设备）
┌─────────────────────┐               ┌──────────────────────────┐
│ Encoder 推理         │               │ Decoder 推理（TVM/MNN）   │
│ ONNX 导出 + 简化     │    SSH/SCP    │ safe runtime (TVM 0.24)  │
│ MetaSchedule 调优    │ ←──────────→  │ Cortex-A72 × 2 (big)     │
│ (builder 侧)        │    RPC        │ Cortex-A55 × 2 (LITTLE)  │
│                     │               │ NEON 128-bit SIMD         │
└─────────────────────┘               └──────────────────────────┘
```

## 环境要求

- **上位机：** Python 3.10+, TVM 0.24dev, ONNX, onnxsim
- **飞腾派：** Anaconda `tvm310_safe` 环境, TVM 0.24.dev0 (safe runtime), MNN
- **连接：** SSH（密码或密钥认证），RPC tracker/runner（调优时）

## 快速开始

```bash
# 0. 启动集成 OpenAMP dashboard（默认离线证据模式）
bash session_bootstrap/scripts/run_openamp_demo.sh

# 1. 连接飞腾派
bash session_bootstrap/scripts/connect_phytium_pi.sh

# 2. 运行 baseline vs current 推理对比
bash session_bootstrap/scripts/run_inference_benchmark.sh \
  --env session_bootstrap/config/rpc_tune_local.2026-03-08.phytium_pi.env

# 3. 运行真实端到端重建对比
bash session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current

# 4. 启动 RPC 调优（笔记本 builder + 飞腾派 runner）
python session_bootstrap/scripts/rpc_tune.py \
  --onnx-path <model.onnx> \
  --output-dir ./tune_output \
  --target '{"kind":"llvm","mtriple":"aarch64-linux-gnu","mcpu":"cortex-a72","mattr":["+neon"],"num-cores":4}' \
  --total-trials 2000 \
  --input-shape 1,32,32,32 \
  --runner rpc
```
