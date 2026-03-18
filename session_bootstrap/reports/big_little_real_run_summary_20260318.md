# big.LITTLE 首轮真机结论摘要（2026-03-18）

## 一句话结论

big.LITTLE 异构流水线已经在飞腾派真机上跑通，并且相对当前 trusted serial real-reconstruction 基线拿到了**稳定可复现的吞吐提升**：两轮 compare 分别为 **`+36.937%`** 和 **`+36.54%`**。

## 0. 口径先说明白

这次 `+36.5% ~ +36.9%` 的提升，比较的是：
- **同一份 current artifact**
- **同一批 300 张 latent 输入**
- **同一条 current real-reconstruction 语义**
- **同一组 SNR / batch 配置**
- 只比较 **serial current** vs **big.LITTLE pipeline current**

所以这不是在和更早那份 `230.339 ms/image` 的 historical current 报告直接做横比。
那份报告（`inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md`）是另一套历史 benchmark 记录，SNR 口径也不同；它可以证明 current 本身已经很强，但**不能直接当成这次 big.LITTLE compare 的对照组**。

## 1. 真机 pipeline 本体

核心报告：
- `session_bootstrap/reports/big_little_pipeline_current_20260318_051520.md`

关键结果：
- status: `ok`
- processed_count: `300`
- artifact_sha256_match: `true`
- big_cores: `[2]`
- little_cores: `[0,1]`
- total_wall_ms: `75913.179`
- images_per_sec: `3.952`

说明：
- 当前首轮真机绑定使用 `BIG_LITTLE_BIG_CORES=2`、`BIG_LITTLE_LITTLE_CORES=0,1`
- CPU 3 在 probe 时仍是 offline，因此后续复跑前仍建议先做一次 topology re-check

## 1.1 阶段级绑核关系（不是算子级绑核）

本轮证据支持的是**阶段 / worker 级 affinity**，不是逐个 TVM 算子级别的绑核：

- **preloader** → LITTLE 核 `[0,1]`
  - 负责 latent 读取 / 预处理 / AWGN 注入 / 入队
- **inferencer** → BIG 核 `[2]`
  - 负责 TVM `load_module` 后的 VM `main` 推理主计算路径
- **postprocessor** → LITTLE 核 `[0,1]`
  - 负责输出保存 / 写图像
- **CPU 3** → probe 时 offline，本轮未参与绑定

所以更严谨的说法应该是：
- 这次突破来自**阶段级异构绑核 + 流水线重叠**
- 不是“已经证明每个算子都被单独绑定到了某个核”

## 2. 真机 compare（首轮）

核心报告：
- `session_bootstrap/reports/big_little_compare_20260318_051326.md`

关键结果：
- serial_images_per_sec: `2.886`
- pipeline_images_per_sec: `3.952`
- throughput_uplift_pct: `36.937`

## 3. 真机 compare（第二轮复跑）

核心报告：
- `session_bootstrap/reports/big_little_compare_20260318_053619.md`

关键结果：
- serial_images_per_sec: `2.879`
- pipeline_images_per_sec: `3.931`
- throughput_uplift_pct: `36.54`

## 4. 稳定性判断

两轮真机 compare 的 uplift 很接近：
- first run: `36.937%`
- second run: `36.54%`
- absolute gap: `0.397 pct`

可作为当前阶段的工作结论：
- 这次 big.LITTLE uplift **不是一次性偶然值**
- 当前可以把 **约 `+36.5% ~ +36.9%` 吞吐提升** 视作首轮真机可复现区间

## 5. 资源 profiling

核心报告：
- `session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md`

关键结果：
- wall_time_seconds: `84`
- vmstat interval samples: `85`
- avg cpu user/system/idle/wait: `53.812 / 2.706 / 43.435 / 0.129 %`
- avg/max runnable tasks: `2.165 / 6`
- min free memory seen by vmstat: `217480 KB`

解释边界：
- 这份 profiling 是 system-wide 的 `free/top/vmstat` 证据，不是 per-process / per-core 精细 tracing
- 它足够说明这条真机 pipeline current 路径在板上可稳定跑完，并给出一份轻量级资源侧佐证

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
2. 首轮真机 compare：`session_bootstrap/reports/big_little_compare_20260318_051326.md`
3. 第二轮真机 compare：`session_bootstrap/reports/big_little_compare_20260318_053619.md`
4. 真机 profiling：`session_bootstrap/reports/resource_profile_big_little_current_20260318_052922.md`
5. 详细操作背景：`session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md`
