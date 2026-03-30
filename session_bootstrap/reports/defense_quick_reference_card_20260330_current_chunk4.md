# Defense Quick Reference Card（current chunk4）

更新时间：`2026-03-30`
用途：答辩前 30 秒快速过一遍；只保留最该说的结论与证据入口。

---

## 1. 一句话定位

这不是 generic TVM benchmark，而是一个**飞腾多核弱网安全语义视觉回传系统**：

- `4-core Linux performance mode` 负责性能 headline
- `3-core Linux + RTOS demo mode` 负责 OpenAMP 安全控制面

主讲页：
- `session_bootstrap/reports/defense_ppt_pages_1_8_cn_20260319.md`

---

## 2. 一句话性能 headline

在 `4-core Linux performance mode` 下：

- PyTorch default reference：`484.183 ms/image`
- TVM serial current：`231.522 ms/image`
- TVM big.LITTLE pipeline current：`134.617 ms/image`
- 同轮吞吐 uplift：`56.077%`

证据：
- `session_bootstrap/reports/big_little_real_run_summary_20260318.md`
- `session_bootstrap/reports/big_little_compare_20260318_123300.md`

---

## 3. 一句话 current 正式结论

trusted current `chunk4` 正式口径：

- trusted SHA：`6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1`
- payload：`1846.9 -> 130.219 ms`（`92.95%`）
- real reconstruction：`1850.0 -> 230.339 ms/image`（`87.55%`）

证据：
- `session_bootstrap/reports/inference_compare_currentsafe_chunk4_refresh_20260313_1758.md`
- `session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md`

---

## 4. 一句话质量结论

在同一 PyTorch reference 下，current **不是靠牺牲质量换速度**：

- `PyTorch vs TVM baseline`：
  - `PSNR 34.4244`
  - `SSIM 0.970454`
  - `LPIPS 0.025883`
- `PyTorch vs TVM current`：
  - `PSNR 35.6633`
  - `SSIM 0.972751`
  - `LPIPS 0.025124`
- current 相比 baseline：
  - `+1.2389 dB PSNR`
  - `+0.002297 SSIM`
  - `LPIPS 也略优`

证据：
- `session_bootstrap/reports/judge_quality_formal_report_20260330_lpips_full.md`

口头提醒：
- baseline 相关 LPIPS 采用 `crop249` 对齐口径，因为历史 baseline 输出是 `249×249`

---

## 5. 一句话多 SNR 结论

current trusted chunk4 在 `SNR=1/4/7/10/13` 下：

- 延迟基本稳定在 `228~234 ms/image`
- PSNR 随 SNR 提升单调改善：
  - `29.1452 -> 31.8047 -> 34.0185 -> 35.6644 -> 36.8695 dB`

证据：
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4.md`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4_latency.svg`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4_quality.svg`

---

## 6. 一句话资源画像

current trusted chunk4 的部署 footprint 是可解释、可控的：

- `run_median_ms = 230.466 ms/image`
- avg CPU `32.283 / 9.065 / 58.348 / 0.250 %`
- `min_free_kb = 88340`
- artifact size `1651136 bytes`（`1.575 MiB`）
- `artifact_sha256_match = true`

证据：
- `session_bootstrap/reports/resource_profile_trusted_current_chunk4_20260330_151728.md`

---

## 7. 一句话 profiling 边界

我们**已经做了 fresh probe**，不是没做：

- 当前 still = `stage_level_hotspot_only`
- fresh probe 仍报：`AttributeError: Module has no function 'profile'`
- 所以当前有可信 hotspot evidence，但**没有 remote runtime per-op trace**

证据：
- `session_bootstrap/reports/profiling_judge_refresh_20260330_170808.md`
- `session_bootstrap/reports/profiling_runtime_support_blocker_20260330.md`

---

## 8. 一句话安全控制面

OpenAMP 这条线的价值是“可控可治理”，不是“让 TVM 更快”：

- 已有：`STATUS_REQ/RESP`、`JOB_REQ/JOB_ACK`、`HEARTBEAT_ACK`、`SAFE_STOP`、`JOB_DONE`
- 已有：`FIT-01 / FIT-02 / FIT-03`

证据：
- `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/summary_report.md`
- `session_bootstrap/reports/openamp_control_plane_evidence_package_20260315/coverage_matrix.md`

---

## 9. 被追问时切哪页

- 问“是不是拿质量换速度” → 附录 Page 9
- 问“资源占用、部署代价” → 附录 Page 10
- 问“不同 SNR 下稳不稳” → 附录 Page 11
- 问“有没有真正 per-op profile” → 附录 Page 12

附录入口：
- `session_bootstrap/reports/defense_appendix_pages_9_12_judge_evidence_20260330.md`

---

## 10. 当前默认总入口

如果只开一个文件，默认开：

- `session_bootstrap/reports/judge_evidence_pack_20260330_current_chunk4_lpips_full.md`
