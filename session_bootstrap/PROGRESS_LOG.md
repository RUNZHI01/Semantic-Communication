# Session Progress Log（长期维护）

- 最后更新：2026-03-14 18:34 +0800（补记 2026-03-14 基于 `release_v1.4.0` 的兼容 patch 已在飞腾板上把最小作业授权闭环推进到真实可用：当前 live `/lib/firmware/openamp_core0.elf` 为 size `1640048`、SHA `98ab501c...647e` 的 `JOB_ACK` 版固件；手工 bring-up 后 `remoteproc0=running`、`rpmsg-openamp-demo-channel` 已建立；对 `/dev/rpmsg0` 发出的真实 `JOB_REQ`（`msg_type=1`，`job_id=9001`）已收到真实 `JOB_ACK`（`msg_type=2`，`decision=ALLOW`，`fault_code=0`，`guard_state=2`），紧接着的 follow-up `STATUS_REQ` 又返回了 `guard_state=2`、`active_job_id=9001`。这标志着 OpenAMP 已从最小状态查询进一步推进到最小作业授权闭环可用阶段。）
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
| 2026-03-11 11:20 | baseline-seeded warm-start current incremental rerun 实际成功（失败原因为旧 SHA guard 配置） | 09:45 重启后的 nonzero-budget incremental rerun 已完成 `500 trials + rpc runner + 编译 + 上传`，生成新 current artifact `1946b08e...`；wrapper 最后 `rc=1` 是因为 env 仍固定旧 hotfix SHA `d8e801...`，并非调优或 runtime 本身失败。将 expected SHA 切到新产物后，current-safe 远端验证已成功 | `session_bootstrap/reports/phytium_baseline_seeded_warm_start_current_incremental_20260311_094548_resume.md` / `session_bootstrap/tmp/phytium_baseline_seeded_warm_start_current_incremental_20260311_094548/optimized_model.so` |
| 2026-03-11 12:04 | 新 current incremental 产物正式 benchmark 突破成立 | 使用新 SHA `1946b08e...` 的正式 baseline-vs-current-safe rerun 已成功完成；baseline median `1844.1 ms`，current-safe median `153.778 ms`，delta `-1690.322 ms`，improvement `91.66%`。这说明当前已经从“恢复 current-safe 可运行”进入到“新 incremental 产物显著优于 baseline”的阶段 | `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md` / `session_bootstrap/reports/phytium_current_incremental_breakthrough_20260311.md` |
| 2026-03-11 15:44 | Scheme A 公平 pure-inference compare 在飞腾派真实跑成 | baseline 与 current 已都走同一 payload runner；在公平 `load + VM init + main()` 口径下，baseline median `1829.28 ms`，current median `152.846 ms`，improvement `91.64%`。先前大幅加速结论因此得到强化，但仍需注明 baseline 输出 `249x249`、current 输出 `256x256` 的 output-shape caveat | `session_bootstrap/reports/inference_compare_scheme_a_fair_fixed_20260311_154243.md` / `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_scheme_a_20260311.md` |
| 2026-03-11 17:02 | output-shape caveat 基本定位完成 | 最新调查显示 `249x249` vs `256x256` 最可能不是 payload runner 改写，也不是本地 local fixture 结论能否定的事情；更大的概率是**真实 baseline archive (`85d701...`) 本身就属于不同 legacy artifact/export 线**，而 current 两条已验证产物都稳定给出 `256x256`。因此这个 caveat 目前更像“baseline artifact lineage 差异”，不会推翻 current 在公平 payload 口径下显著更快的主结论 | `session_bootstrap/reports/inference_output_shape_caveat_investigation_20260311.md` |
| 2026-03-11 19:53 | current-only Scheme B compare 首次落盘 | 这次 compare 的语义已明确为**仅 current 内部**的 payload-symmetric compare，不含 baseline；rebuild-only current SHA `2fcf773fa34d6aa69f80740ffedde33faaf265a045cae97b72022ae2c62a8449` median `2479.246 ms`，incremental current SHA `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644` median `152.36 ms`，delta `-2326.886 ms`，improvement `93.85%`，speedup `16.272x` | `session_bootstrap/reports/current_scheme_b_compare_20260311_195303.md` |
| 2026-03-11 21:23 | 飞腾派真实端到端 reconstruction compare 跑成 | 本次 benchmark 语义已明确为真实端到端 reconstruction（read latent -> reconstruct -> write PNGs），不是 payload-only VM timing；baseline / current 输出目录各落 `300` 张 PNG，baseline median `1830.3 ms/image`、mean `1831.471 ms/image`，current median `255.931 ms/image`、mean `255.882 ms/image`，delta `-1574.369 ms/image`，improvement `86.02%` | `session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md` |
| 2026-03-13 00:13 | 新 trusted current 正式 payload 验证完成 | 以新 SHA `65747fb301851f27892666d28daefc856c0ff2f7f85d3702779be32dde4b6377` 跑正式 baseline-vs-current-safe validate 成功；baseline median `1853.7 ms`，current median `131.343 ms`，improvement `92.91%`。相对上一代 trusted current（SHA `1946b08e...c644`，median `153.778 ms`），本代 current 再降 `22.435 ms`，约快 `14.59%` | `session_bootstrap/reports/inference_compare_currentsafe_split_topup15_validate_20260313_0002.md` / `session_bootstrap/reports/trusted_current_speedup_causal_chain_20260313.md` |
| 2026-03-13 00:28 | trusted current 文档入口完成切换 | `README.md`、`runbooks/artifact_registry.md` 与新归因报告已统一切到 SHA `65747fb3...b6377` 和 payload 中位数 `131.343 ms`；同时明确“为什么这轮更快”的因果链来自 hotspot -> warm-start continuation -> `15` trial topup -> 新 artifact，而非 benchmark 路径变化 | `README.md` / `session_bootstrap/runbooks/artifact_registry.md` / `session_bootstrap/reports/trusted_current_speedup_causal_chain_20260313.md` |
| 2026-03-13 01:02 | 新 trusted current 真实端到端 reconstruction 正式复跑完成 | 以新 SHA `65747fb3...b6377` 跑正式 real reconstruction rerun 成功；baseline median `1834.1 ms/image`，current median `234.219 ms/image`，improvement `87.23%`，baseline/current count 均为 `300`。相对上一代 trusted current（`255.931 ms/image`）再降 `21.712 ms/image`，约快 `8.48%` | `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_split_topup15_20260313_003633_retry_20260313_005140.md` / `session_bootstrap/reports/inference_real_reconstruction_compare_run_20260311_212301.md` |
| 2026-03-13 18:11 | `chunk4` 新 current fresh payload 成对验证完成 | 以 `chunk4` 新 SHA `6f236b07...6dc1` 跑 fresh baseline-vs-current payload compare 成功；baseline median `1846.9 ms`，current median `130.219 ms`，improvement `92.95%`，current SHA guard `match=true`。相对上一代 trusted current（SHA `65747fb3...b6377`，median `131.343 ms`）再降 `1.124 ms`，约快 `0.86%` | `session_bootstrap/reports/inference_compare_currentsafe_chunk4_refresh_20260313_1758.md` |
| 2026-03-13 18:22 | `chunk4` 新 current fresh 真实端到端 reconstruction 成对验证完成 | 以 `chunk4` 新 SHA `6f236b07...6dc1` 跑 fresh baseline-vs-current 真实端到端 compare 成功；baseline median `1850.0 ms/image`，current median `230.339 ms/image`，improvement `87.55%`，baseline/current count 均为 `300`，current SHA guard `match=true`。相对上一代 trusted current（SHA `65747fb3...b6377`，median `234.219 ms/image`）再降 `3.880 ms/image`，约快 `1.66%` | `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md` |
| 2026-03-14 16:27 | OpenAMP `release_v1.4.0` 候选冷启动 + 官方 demo 路径门禁通过 | 板上 live `/lib/firmware/openamp_core0.elf` 已确认切到候选（size `1627224`，SHA `685f39b0...5dc8`）；冷启动成功后 `remoteproc0=running`，dmesg 出现 `Booting fw image openamp_core0.elf, size 1627224` / `remote processor homo_rproc is now up` / `creating channel rpmsg-openamp-demo-channel`，`/dev/rpmsg_ctrl0` 与 `/dev/rpmsg0` 均存在，`sudo rpmsg-demo` 已稳定 echo 至 `Hello World! No:100`。因此 `release_v1.4.0` 已通过关键真机门禁：冷启动 + 官方 RPMsg demo 路径；但这仍不等于已证明与板原始官方固件 byte-identical | `session_bootstrap/reports/openamp_phase5_release_v1.4.0_cold_boot_and_demo_success_2026-03-14.md` |
| 2026-03-14 16:57 | OpenAMP 最小 `STATUS_REQ/RESP` 真机闭环打通 | 基于真实 `release_v1.4.0` 老源码结构重做适配 patch 后，patched live firmware 已在板上运行（size `1635728`，SHA `daf889e3...fcb6`）；`remoteproc0=running`，channel 仍为 `rpmsg-openamp-demo-channel`。通过 `/dev/rpmsg0` 发送真实二进制 `STATUS_REQ`（`msg_type=8`）后，已收到 `STATUS_RESP`（`msg_type=9`），payload 解析为 `guard_state=1, active_job_id=0, last_fault_code=0, heartbeat_ok=0, sticky_fault=0, total_fault_count=0`。这说明 OpenAMP 已从 demo echo transport 推进到最小控制协议语义可用 | `session_bootstrap/reports/openamp_phase5_release_v1.4.0_status_req_resp_success_2026-03-14.md` / `session_bootstrap/reports/openamp_status_req_resp_real_probe_20260314_001.json` |
| 2026-03-14 18:34 | OpenAMP 最小 `JOB_REQ/JOB_ACK` 真机闭环打通 | 基于 `release_v1.4.0` 兼容 patch 的 `JOB_ACK` 版固件（size `1640048`，SHA `98ab501c...647e`），在手工 bring-up 后已通过 `/dev/rpmsg0` 收到真实 `JOB_ACK`：`msg_type=0x02`、`decision=ALLOW`、`fault_code=0`、`guard_state=2`。紧接着的 follow-up `STATUS_REQ` 又返回 `guard_state=2`、`active_job_id=9001`，说明从核 admission decision 已能真实改变可观测状态 | `session_bootstrap/reports/openamp_phase5_release_v1.4.0_job_req_job_ack_success_2026-03-14.md` / `session_bootstrap/reports/openamp_job_req_job_ack_real_probe_20260314_001.json` |

## 2) 已完成项 / 阻断项

### 已完成项

- 脚手架闭环：`check/readiness/quick/full/daily/experiment` 全流程脚本已可落盘。
- ARMv8 真机参数模板与 runbook 完整：`config/`、`scripts/`、`runbooks/` 已打通。
- realcmd 级 quick 已跑通：`status=success`，说明远端 Python/TVM/输入目录/输出目录链路可用。
- full realcmd baseline 已成功执行，说明 `tvm_002.py + batch=1` 路径本身可运行。
- current real reconstruction runner 已入库：`session_bootstrap/scripts/current_real_reconstruction.py`、`session_bootstrap/scripts/run_remote_current_real_reconstruction.sh` 与 `session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env` 已落盘；current 真实 reconstruction 入口现统一为 `session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current`。
- `chunk4` 新 current fresh 真实端到端 reconstruction 正式成对验证已完成：`session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md` 已确认 baseline/current run count 均为 `300`，baseline median `1850.0 ms/image`，current median `230.339 ms/image`，improvement `87.55%`；相对上一代 trusted current `234.219 ms/image` 再快约 `1.66%`。
- `chunk4` 新 current fresh payload 正式成对验证已完成：当前正式 trusted current SHA 已推进到 `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`，正式 payload 中位时间为 `130.219 ms`，较上一代 trusted current `65747fb3...b6377` 的 `131.343 ms` 再快约 `0.86%`；对应 fresh payload / e2e 两份正式报告已落盘。
- OpenAMP `release_v1.4.0` 候选真机冷启动 + 官方 RPMsg demo 路径已验证成功：board 当前 live `/lib/firmware/openamp_core0.elf` 为 size `1627224`、SHA `685f39b0bcdd4eee31ad81d196cf8dda4ba6e33e2285b32985727bd1465e5dc8`；安装候选后冷启动成功，`remoteproc0=running`，dmesg 已出现 `size 1627224` / `remote processor homo_rproc is now up` / `creating channel rpmsg-openamp-demo-channel`，`/dev/rpmsg_ctrl0` 与 `/dev/rpmsg0` 均存在，`sudo rpmsg-demo` 已 echo 至 `Hello World! No:100`。这说明候选已通过板级冷启动与官方 userspace demo 门禁，但不代表已证明与板原始官方固件 byte-identical。
- 基于真实 `release_v1.4.0` 老源码结构的适配 patch 已在真机上打通最小 `STATUS_REQ/RESP`：当前 live patched firmware 为 size `1635728`、SHA `daf889e376a2da8165ddcf0444fcf29182110066eeb82b9aebe3b6f6acd3fcb6`；在 `/dev/rpmsg0` 上发出的真实 `STATUS_REQ` 已收到 `STATUS_RESP`，payload 为 `guard_state=1, active_job_id=0, last_fault_code=0, heartbeat_ok=0, sticky_fault=0, total_fault_count=0`。这说明 OpenAMP 现已从 demo echo transport 进入最小控制协议语义可用阶段。
- 基于 `release_v1.4.0` 兼容 patch 的 `JOB_ACK` 版固件已在真机上打通最小 `JOB_REQ/JOB_ACK`：当前 live firmware 为 size `1640048`、SHA `98ab501c1e71f9e1d20013a7ccf7ee83c2289a423d08bdb371dbf0171f48647e`；对 `/dev/rpmsg0` 发出的真实 `JOB_REQ` 已收到 `JOB_ACK(ALLOW)`，并且紧接着的 `STATUS_RESP` 已返回 `guard_state=2`、`active_job_id=9001`。这说明 OpenAMP 已从最小状态查询进一步进入最小作业授权闭环可用阶段。

### 当前阻断项（P0）

- **baseline 与 current 运行时已确认分叉**：
  - baseline 仍依赖旧 compat runtime 路径；
  - current 已验证应走 `tvm310_safe + safe 0.24.dev0 runtime`。
- **remote current-safe artifact 身份现在必须显式受控**：
  - 2026-03-11 的 `failed_current` 已确认由远端 `optimized_model.so` 漂移触发；
  - 当前 inference 路径已支持 `INFERENCE_CURRENT_EXPECTED_SHA256`，safe env 现默认应跟踪最新 trusted current 产物 SHA `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`；
  - 若未来 intentional deploy 新 current-safe artifact，必须先记录新 SHA，再更新 env 后才可跑 benchmark。
- **current compare 的旧结论需要继续收口**：
  - 2026-03-10 的两次 current-safe target compare 都是 `total_trials=0` rebuild-only；
  - stable/experimental 当时生成了相同 `optimized_model.so sha256`，所以这些 compare 现在必须视为 invalid，而不是“实验 target 有轻微快慢差异”的证据。
- **payload-only 与 real reconstruction 结果不可混写**：
  - `session_bootstrap/reports/current_scheme_b_compare_20260311_195303.md` 只比较 current 内部 rebuild-only SHA `2fcf773fa34d6aa69f80740ffedde33faaf265a045cae97b72022ae2c62a8449` 与 incremental SHA `1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644` 的 payload-symmetric 时间，不含 baseline；
  - `session_bootstrap/reports/inference_compare_currentsafe_chunk4_refresh_20260313_1758.md` 是当前 trusted current payload 正式 validate，结论是新 SHA `6f236b07...6dc1` 对应 `130.219 ms`；
  - `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md` 才是当前 trusted current SHA `6f236b07...6dc1` 的 read latent -> reconstruct -> write PNGs 真端到端 benchmark；讨论真实 reconstruction 时，应使用 `1850.0 -> 230.339 ms/image`（improvement `87.55%`）这组最新正式结果，而不是 Scheme B 的 `2479.246 -> 152.36 ms` 或 payload-only `130.219 ms`。
  - `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_split_topup15_20260313_003633_retry_20260313_005140.md` 现保留为上一代 trusted current SHA `65747fb3...b6377` 的历史参照；其 current median 为 `234.219 ms/image`，说明 `chunk4` 新 trusted current 在真实端到端口径下又再快约 `1.66%`。
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
  - safe env 默认 expected SHA：`6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`
  - current-safe 实机 benchmark 已验证：payload / real reconstruction 两条正式链路都已 `artifact_sha256_match=true`
  - 上一代 trusted current SHA `65747fb301851f27892666d28daefc856c0ff2f7f85d3702779be32dde4b6377` 现保留为历史参照，不再作为默认 guard
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

1. 对外汇报与后续文档统一采用新 trusted current SHA `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1` 的两组正式口径：payload `130.219 ms`、真实端到端 reconstruction `230.339 ms/image`；不要再引用 `65747fb3...b6377` 作为当前默认 trusted current。
2. 后续任何 baseline-vs-current-safe inference / smoke / compare 执行前，都保留并核对 `INFERENCE_CURRENT_EXPECTED_SHA256`；若 intentional deploy 新 current-safe artifact，先记新 SHA，再更新 env。
3. 继续以 `cortex-a72 + neon` 作为默认 current target；更激进的 `+crypto,+crc` 只保留为受控实验分支，并且 compare 必须通过 artifact hash 差异校验才算有效。
4. 如果后续需要把 safe 路线重新产品化，先把 `torch` 对 `tvm_ffi` 的污染隔离策略（或 `TVM_FFI_DISABLE_TORCH_C_DLPACK=1` 的强制入口）固化到更上层的统一运行封装里。

### P1（稳定性与扩展）

1. 在后续 compare 中继续保留 `run_samples_ms`，但只有在 artifact hash 不同的前提下，才讨论 `cortex-a72 + neon + crypto + crc` 的优势/抖动是否能**稳定复现**。
2. 把 rebuild-only one-shot、incremental current、compare 输出分别纳入 daily/experiment 汇总，避免三种语义在文案里混淆成同一条“current 结果”。
3. 如需最终替换长期默认配置，再评估是否把旧 `generic + neon` 文档/模板整体退役，避免误用。
4. 将本文件作为每次 round 后唯一“进度真相源”持续更新（含失败栈摘要、artifact hash 结论与 compare 有效性状态）。
