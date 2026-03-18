# Session Progress Log（长期维护）

- 最后更新：2026-03-18 12:44 +0800（本轮工作重心已经从“补文档入口”切回“把 demo 真正跑起来”，随后又进一步转向 **big.LITTLE 异构大小核方向** 的真机收证与文档归一化。现状已经明显前进：**current live 已在最新代码下真实跑通 `300/300`**，并完成 `STATUS_REQ(READY) -> JOB_REQ(ALLOW) -> HEARTBEAT_ACK -> JOB_DONE(success)` 的整条控制面闭环；其间也已修复 current trusted SHA 错配（`bc9d836`）、torch sidecar fallback/runner 导入问题（`f17c665` / `ab01b5f` / `6b9a8a7`）。另一方面，**baseline 已不再停留在归档 reference 面板，而是已接成真实 PyTorch live 执行路径**（`f94fee1`），但最新终验表明板端仍会对其返回 `JOB_ACK(DENY, ARTIFACT_SHA_MISMATCH)`；也就是说，当前剩余主 blocker 已从 demo 接线切到固件/控制面对 PyTorch generator checkpoint 工件语义的接受规则。与此同时，big.LITTLE 这条线已经不只是“首轮真机能跑通”，而是进一步拿到了**健康板态默认 apples-to-apples compare**：`session_bootstrap/reports/big_little_compare_20260318_123300.md` 现给出 serial current median `231.522 ms/image`、pipeline current median `134.617 ms/image`、throughput uplift `56.077%`，配套的 `session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_123421.md` 也确认了 `processed_count=300`、`artifact_sha256_match=true` 和 `big=[2] / little=[0,1]` 的阶段级绑核。与此同时，历史最佳 direct current e2e 参考仍是 `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md` 的 `230.339 ms/image`；同日 direct rerun 又出现了 `347.375 -> 295.255 -> 239.233 ms/image`、CPU online `0-2 -> 0-3` 的恢复序列，因此当前最重要的新口径已经收敛为：**板态 / CPU online set 是这轮 performance drift 的 primary factor，不只是 artifact lineage**。这也意味着 `123300` 现应成为默认 big.LITTLE reference，而 `095615` 应降级为 degraded-board 证据；若从时间线入口接手，优先看 `session_bootstrap/reports/big_little_real_run_summary_20260318.md`、`123300` compare、配套 pipeline wrapper、历史最佳 direct current e2e 报告与板态漂移复盘。）
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
| 2026-03-14 19:24 | OpenAMP wrapper-backed board smoke 成功 | 板上 wrapper 通过 `--transport hook` 调 bridge 发出真实 `JOB_REQ`（`job_id=9205`）后，已收到 `source=firmware_job_ack` 的真实 `JOB_ACK(ALLOW)`，并且 wrapper 真实放行 runner，最终落 `JOB_DONE(success)`、`runner_exit_code=0`。这说明 OpenAMP 已不再只是“底层协议打通”，而是已完成 wrapper × bridge × firmware × board 的 admission gate 串接 | `session_bootstrap/reports/openamp_wrapper_hook_board_smoke_success_2026-03-14.md` / `session_bootstrap/reports/openamp_wrapper_hook_board_smoke_20260314_005.wrapper_summary.json` / `session_bootstrap/reports/openamp_wrapper_hook_board_smoke_20260314_005.control_trace.jsonl` |
| 2026-03-14 21:45 | OpenAMP 最小 `SAFE_STOP` 真机闭环打通 | `SAFE_STOP` 版固件（size `1647272`，SHA `3e7512fe...0424`）在真机上完成了 `JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)`、`SAFE_STOP`、follow-up `STATUS_REQ` 的整条链路；post-stop `STATUS_RESP` 与 follow-up `STATUS_RESP` 均为 `guard_state=READY`、`active_job_id=0`、`last_fault_code=MANUAL_SAFE_STOP(10)`、`heartbeat_ok=0`、`total_fault_count=1`。这说明最小安全停止语义已真实改变并稳定保持从核运行态 | `session_bootstrap/reports/openamp_phase5_safe_stop_success_2026-03-14.md` / `session_bootstrap/reports/openamp_safe_stop_real_probe_20260314_001.json` |
| 2026-03-15 00:18 | OpenAMP 最小 `JOB_DONE` 真机闭环打通 | `JOB_DONE` 版固件（size `1649896`，SHA `afa9679f...3803`）在 fresh boot + bring-up 后完成了 `STATUS_REQ(READY)`、`JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)`、`JOB_DONE(success)`、follow-up `STATUS_REQ` 的整条链路；post-done `STATUS_RESP` 与 follow-up `STATUS_RESP` 均为 `guard_state=READY`、`active_job_id=0`、`last_fault_code=0`、`heartbeat_ok=0`、`total_fault_count=0`。这说明最小作业完成语义已真实改变并稳定保持从核运行态 | `session_bootstrap/reports/openamp_phase5_job_done_success_2026-03-15.md` / `session_bootstrap/reports/openamp_job_done_real_probe_20260315_001.json` |
| 2026-03-15 01:09 | OpenAMP P1 `FIT-01` wrong-SHA 首轮远端探测已结构化落证（当前 blocked） | 已从 Snapdragon workspace 真实尝试对飞腾板执行 `pre STATUS_REQ -> wrapper wrong-SHA JOB_REQ -> post STATUS_REQ`；但首跳 `ssh_with_password.sh` 到 `100.121.87.73:22` 即命中 `socket: Operation not permitted`，因此这轮没有真正触板。不过本轮已新增 `run_openamp_fit_wrong_sha.py` 并生成结构化 FIT 包，明确记录预期语义、SSH blocker、manifest/trace/status snapshot/report/coverage layout，为下一次在有网络权限的执行环境中直接补跑 FIT-01 做好收口 | `session_bootstrap/scripts/run_openamp_fit_wrong_sha.py` / `session_bootstrap/reports/openamp_wrong_sha_fit_20260315_010828/fit_report_FIT-01.md` / `session_bootstrap/reports/openamp_fit_wrong_sha_remote_probe_blocked_2026-03-15.md` |
| 2026-03-15 01:24 | OpenAMP P1 `FIT-01` wrong-SHA 真机验证成功 | 已切回主会话 `exec` 通过仓库内 `ssh_with_password.sh` 直接连上飞腾派，在远端 `/tmp/openamp_wrong_sha_fit/project` 顺序执行 `pre STATUS_REQ -> wrapper wrong-SHA JOB_REQ -> post STATUS_REQ`；真实 `JOB_REQ` 已收到 `JOB_ACK(DENY)`，其中 `fault_code=1 / ARTIFACT_SHA_MISMATCH`、`guard_state=READY`，wrapper 收敛为 `denied_by_control_hook` 且 runner 未启动，follow-up `STATUS_RESP` 仍保持 `READY/active_job_id=0`，并把 `last_fault=ARTIFACT_SHA_MISMATCH`、`total_fault_count=1` 稳定落盘。这说明“错误 SHA 拒绝执行”已具备正式板级证据 | `session_bootstrap/reports/openamp_wrong_sha_fit_20260315_012403/fit_report_FIT-01.md` / `session_bootstrap/reports/openamp_phase5_fit01_wrong_sha_success_2026-03-15.md` / `session_bootstrap/reports/openamp_wrong_sha_fit_20260315_012403/fit_summary.json` |
| 2026-03-15 01:45 | OpenAMP P1 `FIT-02` 输入契约破坏真机验证成功 | 已在 fresh boot 后按单一路径 `set_env.sh -> sudo rpmsg-demo` 恢复 `/dev/rpmsg0`，随后对真实 `JOB_REQ` 注入非法 `expected_outputs=2`。firmware 返回 `JOB_ACK(DENY)`，其中 `fault_code=9 / ILLEGAL_PARAM_RANGE`、`guard_state=READY`；wrapper 收敛为 `denied_by_control_hook` 且 runner 未启动，follow-up `STATUS_RESP` 仍保持 `READY/active_job_id=0`，并把 `last_fault=ILLEGAL_PARAM_RANGE`、`total_fault_count=1` 稳定落盘。这说明“参数范围 / 输入契约非法值拒绝执行”也已具备正式板级证据 | `session_bootstrap/reports/openamp_input_contract_fit_20260315_014542/fit_report_FIT-02.md` / `session_bootstrap/reports/openamp_phase5_fit02_input_contract_success_2026-03-15.md` / `session_bootstrap/reports/openamp_input_contract_fit_20260315_014542/fit_summary.json` |
| 2026-03-15 01:57 | OpenAMP P1 `FIT-03` 心跳超时 / watchdog 真实缺口确认 | 已在 fresh boot 后按干净路径恢复 `/dev/rpmsg0`，并真实执行 `pre STATUS_REQ -> JOB_REQ(ALLOW) -> HEARTBEAT_ACK(heartbeat_ok=1) -> 停发 heartbeat 5s -> STATUS_REQ`。结果显示 `5s` 无 heartbeat 后状态仍为 `JOB_ACTIVE / active_job_id=9303 / last_fault=0 / heartbeat_ok=1 / total_fault_count=0`，没有出现 `HEARTBEAT_TIMEOUT(F003)` 或自动 stop；最后只能通过显式 `SAFE_STOP` 清理回 `READY`。这说明 `FIT-03` 已拿到正式真机结论，但当前 live firmware 仍缺自动 watchdog 语义 | `session_bootstrap/reports/openamp_heartbeat_timeout_fit_20260315_015841/fit_report_FIT-03.md` / `session_bootstrap/reports/openamp_phase5_fit03_timeout_gap_2026-03-15.md` / `session_bootstrap/reports/openamp_heartbeat_timeout_fit_20260315_015841/fit_summary.json` |
| 2026-03-15 02:34 | OpenAMP P1 `FIT-03` 心跳超时 / watchdog 修复后真机验证成功 | 已将 watchdog 修复版 live firmware（SHA `2c4240e0...7878a`，size `893392`）部署到板上并冷启动 bring-up 成功；在同样的 `pre STATUS_REQ -> JOB_REQ(ALLOW) -> HEARTBEAT_ACK(1) -> 停发 heartbeat 5s -> STATUS_REQ` 探针下，follow-up `STATUS_RESP` 已真实返回 `READY / active_job_id=0 / last_fault=HEARTBEAT_TIMEOUT(3) / heartbeat_ok=0 / total_fault_count=1`。这说明 lazy watchdog patch 已经把 `FIT-03` 从真实缺口转成真实 PASS | `session_bootstrap/reports/openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410/fit_report_FIT-03.md` / `session_bootstrap/reports/openamp_phase5_fit03_watchdog_success_2026-03-15.md` / `session_bootstrap/reports/openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410/fit_summary.json` |
| 2026-03-15 02:40 | 新 watchdog live firmware clean baseline 再确认成功 | 在部署 watchdog-fix live firmware（SHA `2c4240e0...7878a`）并完成 `FIT-03` 复验后，再次通过 fresh reboot + `set_env.sh -> sudo rpmsg-demo` bring-up 做 `STATUS_REQ` clean check，结果返回 `READY / active_job_id=0 / last_fault_code=0 / heartbeat_ok=0 / total_fault_count=0`。这说明当前板上 live 固件不仅能触发 `F003`，也能在 fresh boot 后回到干净 READY 基线，适合作为后续 Demo / 讲解起点 | 主会话 final ready probe（`rpmsg_exists=true`，`guard_state=1`，`active_job_id=0`，`last_fault_code=0`，`heartbeat_ok=0`，`total_fault_count=0`） |
| 2026-03-15 02:50 | OpenAMP 控制面总证据包收口完成 | 已新增 `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/{README.md,coverage_matrix.md,summary_report.md}`，并同步更新根 `README.md`、`session_bootstrap/README.md` 与 `runbooks/artifact_registry.md`，形成可直接用于答辩 / 演示的统一入口。至此 OpenAMP 工程推进阶段可判断为：P1 风险/FIT/覆盖分析基本完成，主焦点切换到 Demo / 视频 / PPT / 讲稿与评委高频追问补证 | `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/README.md` / `coverage_matrix.md` / `summary_report.md` |
| 2026-03-16 20:38 | OpenAMP signed-admission 真机成功证据包收口 | session 已确认 live firmware `140e2e8c...12f1` 冷启动可存活，真实 signed sideband `BEGIN/CHUNK/SIGNATURE/COMMIT` 全部 ACK，follow-up `JOB_REQ` 返回 `JOB_ACK(ALLOW)`，并在 `SAFE_STOP` 清理 + fresh `job_id` 后复验成立。本轮新增的 signed-admission 证据包同时固化了 committed fixture 形状、recovered board build/install lineage、minimal-crypto / sha fix helper 线索，以及“matching private key 不在 repo/workspace，因此 baseline signed validation 未执行”的明确边界。 | `session_bootstrap/reports/openamp_signed_admission_real_board_success_20260316/README.md` / `session_bootstrap/reports/openamp_signed_admission_real_board_success_20260316/evidence_summary.json` |
| 2026-03-17 07:50 | OpenAMP dashboard 最新 live 状态本地启动验收通过 | 本轮在本地临时启动 `run_openamp_demo.sh --port 8092` 后，已确认 `GET /api/health -> {"status":"ok"}`，且 `GET /api/snapshot` 正确暴露 `latest_live_status`：`report_date=2026-03-17`、`valid_instance=8115`、`current=300/300`、`baseline=300/300`，并把 3/17 最新状态报告置于 dashboard docs 入口首位。随后收到的 `young-fjord` `SIGTERM` 只是验收完成后主动结束临时本地 demo 进程。 | `session_bootstrap/reports/openamp_demo_dashboard_local_acceptance_20260317.md` / `session_bootstrap/demo/openamp_control_plane_demo/demo_data.py` / `session_bootstrap/demo/openamp_control_plane_demo/static/app.js` |
| 2026-03-17 21:44 | OpenAMP demo `current live` 真机链路恢复并完成 `300/300` | 经 reboot + `set_env.sh -> rpmsg-demo` bring-up、current trusted SHA 对齐（`bc9d836`）以及 torch sidecar / runner 导入链修复（`f17c665` / `ab01b5f` / `6b9a8a7`）后，`current live` 已在最新代码下真实跑通：控制面成功完成 `STATUS_REQ(READY) -> JOB_REQ(ALLOW) -> HEARTBEAT_ACK -> JOB_DONE(success)`，runner summary 报告 `processed_count=300`、`output_count=300`、`artifact_sha256_match=true`，中位推理时间约 `356.438 ms`。这说明最关键的 current demo live 路径已经从 0/300 恢复到真实可运行状态。 | 本地终验 `job_id=2520907865` 的 `/api/inference-progress` 完整 payload / `runner_summary` / `control_trace` / `wrapper_summary`；相关修复提交：`bc9d836`、`f17c665`、`ab01b5f`、`6b9a8a7` |
| 2026-03-17 23:57 | OpenAMP demo baseline 已接入真实 `PyTorch live` 执行路径，但板端 admission 仍拒绝 | baseline 不再只是归档 reference，而是已切到 `run_remote_pytorch_reference_reconstruction.sh` + `pytorch_reference_reconstruction.py` 的真实执行链（提交 `f94fee1`）。板上 `/home/user/Downloads/jscc-test/export/compressed_gan.pt` 的真实 SHA 已确认是 `3afcebc7...e87763`，并且 demo 发起 baseline live 时已经以该 SHA 作为 expected artifact 发出 `JOB_REQ`；但最新终验仍收到 `JOB_ACK(DENY, ARTIFACT_SHA_MISMATCH)`。这说明当前剩余主 blocker 已经收敛为：**固件 / 控制面对 PyTorch generator checkpoint 这类工件的接受语义尚未对齐**。 | `f94fee1` / baseline live 终验 `job_id=2719112481` 的 `event_log`（`JOB_REQ -> trusted_sha=3afcebc74716`，`JOB_ACK(DENY) -> fault=ARTIFACT_SHA_MISMATCH`）/ 板上 `compressed_gan.pt` SHA 实测 |
| 2026-03-18 00:44 | big.LITTLE 异构流水线脚手架已在 repo 内落地，并完成本地/mock compare 验证 | 已新增 `session_bootstrap/scripts/big_little_pipeline.py`、`run_big_little_pipeline.sh`、`run_big_little_compare.sh`、两份 env 模板与专用 runbook（提交 `cb1323f`）；随后又通过 `0650fbb` 修复了 local/mock compare 对本地 Python 候选链的选择，使 dry-run 下的串行 vs pipeline 对比能稳定产出 JSON summary、Markdown 报告与吞吐 uplift（本地 mock 验证达 `throughput_uplift_pct ≈ 17.757%`）。这说明明早真正需要上板做的已经只剩大小核编号确认与真实吞吐数据采集。 | `cb1323f` / `0650fbb` / `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md` / `session_bootstrap/tests/test_big_little_pipeline.py` |
| 2026-03-18 03:47 | big.LITTLE 一键首跑链已在 local/mock 模式完整跑通 | 在补齐 topology helper、env apply helper、runtime env copy 和 local-mode 分支后，`run_big_little_first_real_attempt.sh` 已能在 mock env 下从头跑到 compare 结果：自动复制 runtime env、跳过不适用的 SSH topology probe、完成 pipeline run 与 serial vs pipeline compare，并稳定输出 JSON summary。虽然 mock 下最终 `throughput_uplift_pct ≈ -2.265%` 仅用于验证执行链而非代表飞腾派真实性能，但它证明明早上板时脚本本身不再是主要风险。 | `b56030d` / `b730020` / `367eb70` / `e3ef55e` / `ddf29ec` / `3d8b5c3` / `/tmp/biglittle_first_mock.out` |
| 2026-03-18 04:08 | big.LITTLE 明早短交接页与主入口回链完成 | 已新增 `session_bootstrap/reports/big_little_overnight_handoff_20260318.md`，把默认一键入口、手工展开链路、拓扑建议、预期输出以及唯一剩余 blocker 收拢成一页；同时根 `README.md`、`session_bootstrap/README.md` 与 `session_bootstrap/runbooks/artifact_registry.md` 都已挂上该入口。这样无论是从项目首页、bootstrap 首页还是 artifact registry 进入，明早都能直接接到同一份 operator-focused handoff。 | `6bdaafe` / `session_bootstrap/reports/big_little_overnight_handoff_20260318.md` |
| 2026-03-18 04:27 | big.LITTLE 短交接页与完整 runbook 双向互链完成 | 已在 `session_bootstrap/reports/big_little_overnight_handoff_20260318.md` 顶部补上 full runbook 入口，并在 `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md` 顶部补上“只想明早执行先看短交接页”的 operator note。这样从 concise handoff 或 full runbook 任一页进入，都能一跳切到另一页，不再需要手工翻找。 | `8461fc0` / `session_bootstrap/reports/big_little_overnight_handoff_20260318.md` / `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md` |
| 2026-03-18 05:15 | big.LITTLE 首轮真机 pipeline + compare 闭环完成 | 先后修掉 topology suggestion 文件格式不兼容、wrapper 变量注入过脆、远端 current artifact 漂移、torch sidecar 路径缺失，以及 `safe_join_process()` 5 秒过早终止 worker 等问题后，首轮真机 run 已正式落盘：pipeline 本体 `processed_count=300`、`artifact_sha256_match=true`、绑定 `big=[2] / little=[0,1]`，而 compare 报告给出 serial `2.886 images/s` -> pipeline `3.952 images/s`，吞吐提升 `36.937%`。这意味着 big.LITTLE 这条线已从“可执行脚手架”推进到“已有首轮真机性能证据”的状态。 | `69e7644` / `0c3b548` / `0633789` / `session_bootstrap/reports/big_little_pipeline_current_20260318_051520.md` / `session_bootstrap/reports/big_little_compare_20260318_051326.md` |
| 2026-03-18 05:31 | big.LITTLE 首轮真机 resource profiling 补齐 | 在修掉 resource-profile wrapper 对远端 tool probe 返回码的误判后，同一条真机 pipeline current 路径的 profiling 已成功落盘：wall time `84s`、vmstat 样本 `85`、平均 CPU `user/system/idle/wait = 53.812 / 2.706 / 43.435 / 0.129 %`、平均 runnable `2.165`、最小 free memory `217480 KB`。这样这条线不再只有“快了多少”，还补上了板级资源使用证据。 | `6730224` / `bebc0a0` / `session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md` |
| 2026-03-18 05:39 | big.LITTLE 第二轮真机 compare 复跑完成并确认 uplift 稳定 | 第二轮复跑已再次跑成：serial `2.879 images/s`、pipeline `3.931 images/s`、吞吐提升 `36.54%`。与首轮 `36.937%` 基本一致，说明当前这条异构流水线相对同轮 serial current 基线的 uplift 具备可重复性，而不是一次性偶然值；但它并不等于已经超过历史最佳 current 端到端 `230.339 ms/image`。 | `session_bootstrap/reports/big_little_compare_20260318_053619.md` |
| 2026-03-18 05:45 | big.LITTLE 真机结论摘要页完成 | 已新增 `session_bootstrap/reports/big_little_real_run_summary_20260318.md`，把首轮 compare、第二轮复跑 compare、真机 pipeline 本体与 resource profiling 收拢成一页，供后续引用/汇报时直接使用；根 `README.md`、`session_bootstrap/README.md` 和 `runbooks/artifact_registry.md` 也已补上该入口。 | `session_bootstrap/reports/big_little_real_run_summary_20260318.md` |
| 2026-03-18 06:05 | big.LITTLE 旧入口统一改指向 final summary | 已把 `session_bootstrap/reports/big_little_overnight_handoff_20260318.md` 与 `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md` 顶部都改成先提示 `session_bootstrap/reports/big_little_real_run_summary_20260318.md`，将默认阅读路径从“首跑前交接/长 runbook”切换到“先看最终结论，再按需下钻”。这样后续接手者不容易再先读到已过时的首跑前口径。 | `955d69e` / `session_bootstrap/reports/big_little_real_run_summary_20260318.md` |
| 2026-03-18 06:25 | big.LITTLE 关键真机证据文件正式入库 | 已将首轮真机 compare、第二轮复跑 compare、真机 pipeline 本体、resource profiling 以及首轮 topology capture/suggestion 等关键实证文件提交进 git（`55bf447`），避免仓库只剩入口与摘要、却缺失被引用的原始证据。这样后续任何人拉仓库后，都能直接看到完整 big.LITTLE 结果链，而不是依赖本地临时文件。 | `55bf447` / `session_bootstrap/reports/big_little_compare_20260318_051326.md` / `session_bootstrap/reports/big_little_compare_20260318_053619.md` / `session_bootstrap/reports/big_little_pipeline_current_20260318_051520.md` / `session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md` |
| 2026-03-18 07:15 | big.LITTLE 工作区降噪与 runtime env ignore 完成 | 已删除一批被正式真机证据替代的 mock / 失败中间产物，并新增 `.gitignore` 规则忽略 `session_bootstrap/config/big_little_pipeline.current.runtime_*.env`。这让后续再跑 big.LITTLE 时，runtime env 副本不再刷屏 `git status`，而主证据链保持清晰。 | `332d4cd` / `.gitignore` |
| 2026-03-18 07:55 | big.LITTLE post-run 文案归一化完成 | 已把首页/Bootstrap 首页里仍残留的“明早执行交接”改成“首跑前交接（历史）”，并把 overnight handoff 与 full runbook 内仍偏执行前的表述改写成“历史参考/原始首跑链”。这样文案语气终于与当前事实对齐：默认入口看 final summary，旧交接页只是历史材料。 | `4f56edc` / `README.md` / `session_bootstrap/README.md` / `session_bootstrap/reports/big_little_overnight_handoff_20260318.md` / `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md` |
| 2026-03-18 09:56 | big.LITTLE best-current / `SNR=10` 真机 apples-to-apples compare 完成并成为默认引用 | 已新增更可 defend 的同轮 compare：在 best-current artifact lineage、`SNR=10`、300 张 latent、real-reconstruction 语义下，same-run serial current 为 `344.721 ms/image`，same-run pipeline current 为 `254.791 ms/image`，相对同轮 serial current 吞吐提升 `35.298%`。与此同时，它也把 absolute status 说得更清楚：当前 pipeline 仍比历史最佳 current e2e `230.339 ms/image` 慢约 `10.62%`，因此默认结论应是“relative uplift 成立”，不是“absolute best 已刷新”。 | `session_bootstrap/reports/big_little_compare_20260318_095615.md` / `session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_095811.md` / `session_bootstrap/config/big_little_pipeline.current.bestcurrent_snr10.2026-03-18.phytium_pi.env` |
| 2026-03-18 12:33 | big.LITTLE 健康板态 compare 取代 degraded-board headline，并明确板态漂移为主因 | 在 reboot 后 CPU online 恢复到 `0-3` 的前提下，fresh direct rerun 已从 degraded-board 的 `347.375 ms/image` 恢复到 `239.233 ms/image`，中间还观察到 `295.255 ms/image` 的恢复点；同一恢复后的板态上，新的 apples-to-apples compare 给出 serial current median `231.522 ms/image`、pipeline current median `134.617 ms/image`、throughput uplift `56.077%`。因此当前最新 validated 结论应更新为：板态 / CPU online set 是这轮 drift 的 primary factor，`123300` 成为默认 big.LITTLE reference，而 `095615` 降级为 degraded-board 证据。 | `session_bootstrap/reports/big_little_compare_20260318_123300.md` / `session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_123421.md` / `session_bootstrap/reports/big_little_board_state_drift_20260318.md` |
| 2026-03-14 21:04 | OpenAMP 最小 `HEARTBEAT/HEARTBEAT_ACK` 真机闭环打通且 fresh-boot 状态一致性修复成功 | 修复后的 heartbeat-fix 版固件（size `1646088`，SHA `c1172b7c...4711`）已在真机上验证：fresh boot 后初始 `STATUS_RESP` 为 `guard_state=READY, active_job_id=0, heartbeat_ok=0, total_fault_count=0`；随后真实 `JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)` 与 follow-up `STATUSRESP(guard_state=JOB_ACTIVE, active_job_id=9501, heartbeat_ok=1)` 全部成立，说明先前 deny/heartbeat 状态不一致问题已被 reset/normalize 修复收住 | `session_bootstrap/reports/openamp_heartbeat_fix_validate_20260314/phase3_probe.log` / `session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch` |

## 2) 已完成项 / 阻断项

### 已完成项

- 脚手架闭环：`check/readiness/quick/full/daily/experiment` 全流程脚本已可落盘。
- ARMv8 真机参数模板与 runbook 完整：`config/`、`scripts/`、`runbooks/` 已打通。
- realcmd 级 quick 已跑通：`status=success`，说明远端 Python/TVM/输入目录/输出目录链路可用。
- full realcmd baseline 已成功执行，说明 `tvm_002.py + batch=1` 路径本身可运行。
- current real reconstruction runner 已入库：`session_bootstrap/scripts/current_real_reconstruction.py`、`session_bootstrap/scripts/run_remote_current_real_reconstruction.sh` 与 `session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env` 已落盘；current 真实 reconstruction 入口现统一为 `session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current`。
- 2026-03-17 夜间 `current live` demo 路径已经恢复到真机可运行状态：在最新代码下，current live 已真实完成 `300/300`，并通过控制面拿到 `STATUS_REQ(READY) -> JOB_REQ(ALLOW) -> HEARTBEAT_ACK -> JOB_DONE(success)` 的整条闭环。当前最关键的 demo 主路径因此不再 blocked。
- baseline 已经从“PyTorch reference 展示卡片”进一步推进成真实 `PyTorch live` 执行路径：demo baseline 现改走 `run_remote_pytorch_reference_reconstruction.sh` / `pytorch_reference_reconstruction.py`，而不再是 legacy TVM compat runner。
- big.LITTLE 异构大小核方向现在默认应引用健康板态 compare `session_bootstrap/reports/big_little_compare_20260318_123300.md`：serial current median `231.522 ms/image`、pipeline current median `134.617 ms/image`、吞吐 uplift `56.077%`；配套 pipeline wrapper 是 `session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_123421.md`。
- 同日 direct rerun 从 degraded-board 的 `347.375 ms/image` 恢复到 post-reboot 的 `239.233 ms/image`，中间还观察到 `295.255 ms/image`，且 CPU online 从 `0-2` 恢复到 `0-3`；因此当前 big.LITTLE / performance-drift 调查必须明确写出：**板态 / CPU online set 是 primary factor，不只是 artifact lineage**，`095615` 应作为 degraded-board 证据保留而不是继续当默认 headline。
- `chunk4` 新 current fresh 真实端到端 reconstruction 正式成对验证已完成：`session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md` 已确认 baseline/current run count 均为 `300`，baseline median `1850.0 ms/image`，current median `230.339 ms/image`，improvement `87.55%`；相对上一代 trusted current `234.219 ms/image` 再快约 `1.66%`。
- `chunk4` 新 current fresh payload 正式成对验证已完成：当前正式 trusted current SHA 已推进到 `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`，正式 payload 中位时间为 `130.219 ms`，较上一代 trusted current `65747fb3...b6377` 的 `131.343 ms` 再快约 `0.86%`；对应 fresh payload / e2e 两份正式报告已落盘。
- OpenAMP `release_v1.4.0` 候选真机冷启动 + 官方 RPMsg demo 路径已验证成功：board 当前 live `/lib/firmware/openamp_core0.elf` 为 size `1627224`、SHA `685f39b0bcdd4eee31ad81d196cf8dda4ba6e33e2285b32985727bd1465e5dc8`；安装候选后冷启动成功，`remoteproc0=running`，dmesg 已出现 `size 1627224` / `remote processor homo_rproc is now up` / `creating channel rpmsg-openamp-demo-channel`，`/dev/rpmsg_ctrl0` 与 `/dev/rpmsg0` 均存在，`sudo rpmsg-demo` 已 echo 至 `Hello World! No:100`。这说明候选已通过板级冷启动与官方 userspace demo 门禁，但不代表已证明与板原始官方固件 byte-identical。
- 基于真实 `release_v1.4.0` 老源码结构的适配 patch 已在真机上打通最小 `STATUS_REQ/RESP`：当前 live patched firmware 为 size `1635728`、SHA `daf889e376a2da8165ddcf0444fcf29182110066eeb82b9aebe3b6f6acd3fcb6`；在 `/dev/rpmsg0` 上发出的真实 `STATUS_REQ` 已收到 `STATUS_RESP`，payload 为 `guard_state=1, active_job_id=0, last_fault_code=0, heartbeat_ok=0, sticky_fault=0, total_fault_count=0`。这说明 OpenAMP 现已从 demo echo transport 进入最小控制协议语义可用阶段。
- 基于 `release_v1.4.0` 兼容 patch 的 `JOB_ACK` 版固件已在真机上打通最小 `JOB_REQ/JOB_ACK`：当前 live firmware 为 size `1640048`、SHA `98ab501c1e71f9e1d20013a7ccf7ee83c2289a423d08bdb371dbf0171f48647e`；对 `/dev/rpmsg0` 发出的真实 `JOB_REQ` 已收到 `JOB_ACK(ALLOW)`，并且紧接着的 `STATUS_RESP` 已返回 `guard_state=2`、`active_job_id=9001`。这说明 OpenAMP 已从最小状态查询进一步进入最小作业授权闭环可用阶段。
- wrapper-backed board smoke 已真实成功：板上 `openamp_control_wrapper.py --transport hook` 通过 bridge 收到 `source=firmware_job_ack` 的 `JOB_ACK(ALLOW)` 后，已实际放行 runner 并收到了 `JOB_DONE(success)`，`runner_exit_code=0`。这说明当前控制面已经完成从 wrapper 到 bridge 到 firmware 再回到 wrapper 的最小 admission gate 串接。
- `HEARTBEAT/HEARTBEAT_ACK` 最小运行中监护已在真机打通：修复后的 heartbeat-fix 版固件（size `1646088`，SHA `c1172b7c...4711`）已确认 fresh boot 初始状态干净（`READY / active_job_id=0 / heartbeat_ok=0 / total_fault_count=0`），随后真实 `JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)` 与 follow-up `STATUS_RESP(guard_state=JOB_ACTIVE, active_job_id=9501, heartbeat_ok=1)` 已全部成立。这说明 OpenAMP 已从最小 admission gate 进一步推进到最小运行中监护可用阶段。
- `SAFE_STOP` 最小真机闭环也已验证成功：当前 `SAFE_STOP` 版固件（size `1647272`，SHA `3e7512fef57b0581afd319aaccd0a3144cf0e08052b30b043c2c87908dfe0424`）已在真机上完成 `JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)`、`SAFE_STOP` 与 follow-up `STATUS_REQ` 的全链路验证；post-stop 与 follow-up 状态均稳定收敛到 `READY / active_job_id=0 / last_fault_code=MANUAL_SAFE_STOP(10) / heartbeat_ok=0 / total_fault_count=1`。这说明控制面已从“允许运行 + 运行中打点”进一步推进到“允许显式安全停止并稳定保持 stop 后状态”。
- `JOB_DONE` 最小真机闭环也已验证成功：当前 `JOB_DONE` 版固件（size `1649896`，SHA `afa9679f24f0d9d4ccd4c35e0c779e72573bfe839799d7f95586706977b23803`）已在 fresh boot + bring-up 后完成 `STATUS_REQ(READY)`、`JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)`、`JOB_DONE(success)` 与 follow-up `STATUS_REQ` 的全链路验证；post-done 与 follow-up 状态均稳定收敛到 `READY / active_job_id=0 / last_fault_code=0 / heartbeat_ok=0 / total_fault_count=0`。这说明控制面已进一步推进到“作业完成后回到干净 READY 状态”也可稳定成立。
- `JOB_DONE` 最小真机闭环也已验证成功：当前 `JOB_DONE` 版固件（size `1649896`，SHA `afa9679f24f0d9d4ccd4c35e0c779e72573bfe839799d7f95586706977b23803`）已在 fresh boot + bring-up 后完成 `STATUS_REQ(READY)`、`JOB_REQ(ALLOW)`、`HEARTBEAT_ACK(heartbeat_ok=1)`、`JOB_DONE(success)` 与 follow-up `STATUS_REQ` 的全链路验证；post-done 与 follow-up 状态均稳定收敛到 `READY / active_job_id=0 / last_fault_code=0 / heartbeat_ok=0 / total_fault_count=0`。这说明控制面已进一步推进到“作业完成后回到干净 READY 状态”也可稳定成立。
- P1 `FIT-01` wrong-SHA 首轮远端探测已产出结构化证据包：`session_bootstrap/scripts/run_openamp_fit_wrong_sha.py` 已把真机命令序列、SSH reachability probe、pre/post status snapshot、wrapper manifest/trace/summary、FIT summary/report 与 coverage scaffold 收口到 `session_bootstrap/reports/openamp_wrong_sha_fit_20260315_010828/`；这次 bundle 的真实结论是 `BLOCKED`，根因是当前 workspace 无法打开到飞腾板 `100.121.87.73:22` 的 socket，而不是 firmware 已经返回了 wrong-SHA 决策。
- P1 `FIT-01` wrong-SHA 真机板级证据现已补齐：主会话通过仓库内 SSH helper 直连飞腾派后，已在远端 `/tmp/openamp_wrong_sha_fit/project` 真实执行 `pre STATUS_REQ -> wrapper wrong-SHA JOB_REQ -> post STATUS_REQ`，并将板侧 evidence 拉回本地 `session_bootstrap/reports/openamp_wrong_sha_fit_20260315_012403/`。正式结论为 `PASS`：`JOB_ACK(DENY, ARTIFACT_SHA_MISMATCH)`、wrapper `denied_by_control_hook`、runner 未启动、follow-up `STATUS_RESP=READY/active_job_id=0/last_fault=ARTIFACT_SHA_MISMATCH/total_fault_count=1`。
- P1 `FIT-02` 输入契约破坏真机板级证据也已补齐：在 fresh boot 后通过单一路径 `set_env.sh -> sudo rpmsg-demo` 恢复 `/dev/rpmsg0`，然后对真实 `JOB_REQ` 注入非法 `expected_outputs=2`，板侧 evidence 已落回本地 `session_bootstrap/reports/openamp_input_contract_fit_20260315_014542/`。正式结论为 `PASS`：`JOB_ACK(DENY, ILLEGAL_PARAM_RANGE)`、wrapper `denied_by_control_hook`、runner 未启动、follow-up `STATUS_RESP=READY/active_job_id=0/last_fault=ILLEGAL_PARAM_RANGE/total_fault_count=1`。
- P1 `FIT-03` 心跳超时 / watchdog 也已拿到真实板级结论：在 fresh boot 后允许一个真实作业、发送一次有效 `HEARTBEAT_ACK(heartbeat_ok=1)`，然后故意停发 heartbeat `5s`，follow-up `STATUS_RESP` 仍保持 `JOB_ACTIVE/active_job_id=9303/last_fault=0/heartbeat_ok=1/total_fault_count=0`。这证明当前 live firmware **尚未实现或接通自动 heartbeat-timeout watchdog**；本轮为了清理板子，额外发送了 `SAFE_STOP`，随后状态回到 `READY/last_fault=MANUAL_SAFE_STOP(10)`。因此 `FIT-03` 的正式结论是：缺口已确认，而非猜测。
- P1 `FIT-03` 的 watchdog 缺口现已在新 live firmware 上被关闭：仓库内 `0503b04 openamp: add lazy firmware heartbeat timeout watchdog` 已被应用到远端 `release_v1.4.0` 源树并成功构建/部署，复跑同一套 `5s` 无 heartbeat 探针后，follow-up `STATUS_RESP` 已真实返回 `HEARTBEAT_TIMEOUT(F003)` 且状态回到 `READY`。因此当前 P1 的最终正式结论已更新为：`FIT-01 PASS / FIT-02 PASS / FIT-03 PASS`。
- OpenAMP 控制面总证据包已正式收口：`session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/` 现已提供统一 `README + coverage_matrix + summary_report` 三件套，并把 P0 里程碑、P1 三项 FIT 最终状态以及 `FIT-03` 的 pre-fix FAIL -> post-fix PASS 历史链都纳入统一答辩入口。
- 新 watchdog live firmware clean baseline 已确认：在部署 SHA `2c4240e0...7878a` 并完成 `FIT-03` PASS 后，再次 fresh reboot + bring-up 的 `STATUS_REQ` 已返回 `READY / active_job_id=0 / last_fault=0 / heartbeat_ok=0 / total_fault_count=0`，说明当前板上 live 基线适合作为后续 Demo / PPT 演示起点。

### 当前阻断项（P0）

- **baseline 与 current 运行时已确认继续分叉，但语义已更新**：
  - current 已在 latest demo 代码下真实跑通 `300/300`，当前主线已不再是 blocker；
  - baseline 不再优先走旧 TVM compat live，而是已切成真实 `PyTorch live` 路径；
  - baseline 当前剩余 blocker 不是 demo 接线，而是板端 admission 仍会对 PyTorch generator checkpoint 返回 `ARTIFACT_SHA_MISMATCH`。
- **remote current-safe artifact 身份现在必须显式受控**：
  - 2026-03-11 的 `failed_current` 已确认由远端 `optimized_model.so` 漂移触发；
  - 当前 inference 路径已支持 `INFERENCE_CURRENT_EXPECTED_SHA256`，safe env 现默认应跟踪最新 trusted current 产物 SHA `6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`；
  - 若未来 intentional deploy 新 current-safe artifact，必须先记录新 SHA，再更新 env 后才可跑 benchmark。
- **current compare 的旧结论需要继续收口**：
  - 2026-03-10 的两次 current-safe target compare 都是 `total_trials=0` rebuild-only；
  - stable/experimental 当时生成了相同 `optimized_model.so sha256`，所以这些 compare 现在必须视为 invalid，而不是“实验 target 有轻微快慢差异”的证据。
- **Codex 子沙箱与主会话 `exec` 的板级网络权限不同，后续 FIT 要固定走主会话 SSH**：
  - 2026-03-15 01:09 +0800 的 `socket: Operation not permitted` 只证明当时的 Codex 子沙箱不能直接打开到飞腾板 `100.121.87.73:22` 的 socket；
  - 随后切回主会话 `exec(host=node,lenovo)` 后，仓库内 `ssh_with_password.sh` 已成功连板并真实跑通 `FIT-01`；
  - 因此这个问题不再是系统级 blocker，但它是一个执行策略约束：后续 `FIT-02/FIT-03` 的 board run 应继续由主会话直接发起，或先显式把所需脚本同步到远端再执行，不要默认交给 Codex 子沙箱。
- **fresh boot 后恢复 `/dev/rpmsg0` 的干净路径应固定为 `set_env.sh -> sudo rpmsg-demo`，不要手工多次 `echo start/stop`**：
  - 2026-03-15 01:33~01:40 的一次 `FIT-02` 前置操作中，手工 `stop/start remoteproc0` 触发了 `被中断的系统调用` 与一次 `Boot failed: -4`，虽然最终可恢复，但会把板侧状态搞脏；
  - 重新整板启动后，只跑一次 `sudo /home/user/open-amp/set_env.sh` 仍然只会拿到 `/dev/rpmsg_ctrl0`；
  - 随后再跑一次 `sudo timeout 15s /home/user/open-amp/rpmsg-demo`，`/dev/rpmsg0` 才稳定出现；
  - 因此后续 `FIT-03` 的 fresh-boot bring-up 应沿用这条单一路径，而不是再次手工多次操纵 `remoteproc0/state`。
- **当前 OpenAMP 主缺口已经从控制面工程实现切换到答辩材料与非核心扩展能力**：
  - 控制面最小闭环与三类正式 FIT 都已经完成真机收证，并且统一 evidence package 也已经生成；
  - 当前最值钱的下一步不再是继续补 `FIT-01/02/03`，而是把这套证据转成四幕 Demo、视频脚本、PPT 页结构和讲稿；
  - 仍未纳入当前正式口径的 OpenAMP 扩展项包括：`FIT-04/05`、`RESET_REQ/ACK`、deadline enforcement、sticky fault reset。
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
5. 以 `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/` 作为当前默认 OpenAMP 对外入口，不要再分散引用零散 report。
6. 下一步优先把 OpenAMP 证据包翻译成四幕 Demo、视频脚本、PPT 页结构与讲稿。
7. 在答辩材料阶段，明确保留 `FIT-03` 的 pre-fix FAIL -> post-fix PASS 两阶段历史，不要只展示最终 PASS。
8. 若时间允许，再补 `FIT-04/05`、`RESET_REQ/ACK`、deadline enforcement、sticky fault reset 等非当前主口径扩展项。
