# big.LITTLE 真机结论摘要（2026-03-18）

## 一句话结论

当前默认应引用的真机 apples-to-apples compare 是 `session_bootstrap/reports/big_little_compare_20260318_095615.md`：在与历史最佳 current 同 artifact lineage、同 `SNR=10`、同 300 张 latent、同 real-reconstruction 语义的同轮对照下，serial current 为 `344.721 ms/image`，big.LITTLE pipeline current 为 `254.791 ms/image`，相对同轮 serial current 吞吐提升 `35.298%`。但它仍慢于历史最佳 current 端到端 `230.339 ms/image` 约 `10.62%`，所以当前正确结论是“相对 serial 有显著收益”，不是“已经刷新 absolute best current record”。

## 0. 先把口径说清楚

这次默认应引用的 compare，比较的是：
- **同一份 current artifact lineage**（历史最佳 current `230.339 ms/image` 所在的 `6f236b07...6dc1` 这一代）
- **同一组 `SNR=10` / `batch=1` 设置**
- **同一批 300 张 latent 输入**
- **同一条 current real-reconstruction 语义**
- 只比较 **same-run serial current** vs **same-run big.LITTLE pipeline current**

因此，这份 `095615` compare 适合回答两个问题中的第一个：
- **big.LITTLE 在当前最强 current 这套设置上，是否比同轮 serial current 更好？**
  - 是，`35.298%` 吞吐 uplift。
- **big.LITTLE 是否已经超过 current 历史最佳绝对端到端结果？**
  - 还没有；当前 pipeline `254.791 ms/image` 仍慢于历史最佳 `230.339 ms/image` 约 `10.62%`。

## 1. 首选 apples-to-apples compare

核心报告：
- `session_bootstrap/reports/big_little_compare_20260318_095615.md`
- `session_bootstrap/config/big_little_pipeline.current.bestcurrent_snr10.2026-03-18.phytium_pi.env`

关键结果：
- serial_total_wall_ms: `103416.354`
- pipeline_total_wall_ms: `76437.341`
- serial current: `103416.354 / 300 = 344.721 ms/image`
- pipeline current: `76437.341 / 300 = 254.791 ms/image`
- serial_images_per_sec: `2.901`
- pipeline_images_per_sec: `3.925`
- throughput_uplift_pct: `35.298`

为什么它是当前首选引用：
- env 明确固定到历史最佳 current artifact lineage 和 `SNR=10` 设置；
- compare 在同一轮里同时跑 serial current 和 pipeline current；
- 这样“relative-vs-serial improvement”和“absolute-vs-historical-best status”可以分开说，不会混写。

## 2. 绝对速度状态：仍未超过历史最佳 current

历史最佳 current e2e 参考报告：
- `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md`

当前应这样表述：
- historical best current e2e: `230.339 ms/image`
- preferred big.LITTLE pipeline current: `254.791 ms/image`
- absolute gap: `24.452 ms/image`
- slower than historical best by: `10.62%`

因此当前对外更稳妥的说法应固定为：
- **big.LITTLE 相对同轮 serial current 明显有效**
- **big.LITTLE 还没有刷新 current 的绝对最快端到端记录**

## 3. 配套 pipeline 本体证据

匹配这次 apples-to-apples compare 的 pipeline wrapper 报告：
- `session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_095811.md`

关键结果：
- status: `ok`
- processed_count: `300`
- artifact_sha256_match: `true`
- big_cores: `[2]`
- little_cores: `[0,1]`
- total_wall_ms: `76437.341`
- images_per_sec: `3.925`

阶段级 affinity 结论保持不变：
- **preloader** → LITTLE `[0,1]`
- **inferencer** → BIG `[2]`
- **postprocessor** → LITTLE `[0,1]`
- 当前证据支持的是**阶段 / worker 级 affinity + pipeline overlap**，不是逐个 TVM 算子级绑核。

## 4. 更早两轮真机 compare 的地位

更早两轮同日真机 compare 仍有价值，但现在应作为**支持性复现证据**，而不是默认 headline：
- `session_bootstrap/reports/big_little_compare_20260318_051326.md`
  - throughput_uplift_pct: `36.937`
- `session_bootstrap/reports/big_little_compare_20260318_053619.md`
  - throughput_uplift_pct: `36.54`

它们说明：
- 这条异构流水线相对 serial current 的 uplift 不是一次性偶然值；
- 但如果要做最严谨、最容易 defend 的引用，优先用 `095615` 这份 best-current / `SNR=10` apples-to-apples compare。

## 5. 资源 profiling（支持性证据）

核心报告：
- `session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md`

关键结果：
- wall_time_seconds: `84`
- vmstat interval samples: `85`
- avg cpu user/system/idle/wait: `53.812 / 2.706 / 43.435 / 0.129 %`
- avg/max runnable tasks: `2.165 / 6`
- min free memory seen by vmstat: `217480 KB`

解释边界：
- 这份 profiling 是更早同日 current pipeline run 的 system-wide `free/top/vmstat` 证据；
- 它仍然能说明 big.LITTLE current 路径在板上可稳定跑完，但它不是 `095615` apples-to-apples compare 本身的主结论来源。

## 6. 本轮真正修掉的 blocker

为把这条线从“可跑脚手架”推进到“真机闭环”，本轮实际修掉了：
- topology suggestion 文件不是纯 JSON，导致 auto-apply 失败
- wrapper 远端 runner 变量注入过脆，导致无声秒退
- 远端 current artifact 漂移，SHA 与 trusted current 不一致
- 远端读取 `.pt` latent 输入缺少 torch sidecar 路径
- `safe_join_process()` 只等 5 秒，导致 worker 被父进程过早终止
- resource-profile wrapper 对远端 tool probe 返回码误判

相关修复提交：
- `69e7644` — `fix: accept mixed-output topology suggestion files`
- `0c3b548` — `fix: unblock real big.LITTLE first run`
- `0633789` — `fix: avoid early big.LITTLE worker termination`
- `6730224` — `fix: relax resource profile tool probe`
- `bebc0a0` — `fix: tolerate noisy resource probe exit codes`

## 7. 后续默认引用顺序

如果后面只想快速引用这条线，推荐按下面顺序：
1. 结论摘要：`session_bootstrap/reports/big_little_real_run_summary_20260318.md`
2. 首选 apples-to-apples compare：`session_bootstrap/reports/big_little_compare_20260318_095615.md`
3. 匹配 pipeline wrapper 报告：`session_bootstrap/reports/big_little_pipeline_bestcurrent_snr10_current_20260318_095811.md`
4. 历史最佳 current e2e 参考：`session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md`
5. 更早两轮真机 compare：`session_bootstrap/reports/big_little_compare_20260318_051326.md` / `session_bootstrap/reports/big_little_compare_20260318_053619.md`
6. 真机 profiling：`session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md`
7. 详细操作背景：`session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md`
