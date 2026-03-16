# OpenAMP 控制面证据总报告

- generated_at: `2026-03-15T03:20:00+0800`
- package_id: `openamp_control_plane_evidence_package_20260315`
- scope: `release_v1.4.0` 派生最小控制面在飞腾派真机上的控制闭环与正式 FIT 收证
- primary_matrix: [coverage_matrix.md](coverage_matrix.md)
- latest_live_status: [../openamp_demo_live_dualpath_status_20260317.md](../openamp_demo_live_dualpath_status_20260317.md)
- final_verdict: `P0 已板级闭环；P1 FIT-01 / FIT-02 / FIT-03 最终均为 PASS`

## 执行摘要

当前仓库已经形成一套可直接用于答辩 / 演示的 OpenAMP 控制面证据链。底座方面，`release_v1.4.0` 派生控制固件已经在飞腾派真实板上依次打通 `STATUS_REQ/RESP`、`JOB_REQ/JOB_ACK`、`HEARTBEAT/HEARTBEAT_ACK`、`SAFE_STOP`、`JOB_DONE`，并由 wrapper-backed board smoke 证明 Linux wrapper 会基于真实 firmware `JOB_ACK(ALLOW)` 放行 runner。风险收口方面，`FIT-01` 与 `FIT-02` 已分别证明错误 SHA 和输入契约违规会在 admission gate 被真机拒绝；`FIT-03` 则保留了完整历史链条，即旧 live firmware 先真实暴露 watchdog 缺口，随后在部署基于本地提交 `0503b04 openamp: add lazy firmware heartbeat timeout watchdog` 构建出的修复固件后，以同一探针顺序复跑转为 PASS。

补充到最近一轮 live 事实层：见 [../openamp_demo_live_dualpath_status_20260317.md](../openamp_demo_live_dualpath_status_20260317.md)。该摘要明确确认 **8115 是当前唯一有效 demo 实例**，且最近一轮 live 中 **current 已成功跑通、baseline 也已通过 signed sideband 进入真机执行，两侧 reconstruction 均完成 `300/300`**。

## 最终状态

| Area | Verdict | Primary Evidence |
|---|---|---|
| P0 最小控制闭环 | PASS | [coverage_matrix.md](coverage_matrix.md) |
| P1 正式 FIT | `FIT-01 PASS / FIT-02 PASS / FIT-03 PASS` | [coverage_matrix.md](coverage_matrix.md) |
| FIT-03 历史完整性 | 保留 `pre-fix FAIL -> post-fix PASS`，未擦除旧 live firmware 的真实缺口 | [../openamp_phase5_fit03_timeout_gap_2026-03-15.md](../openamp_phase5_fit03_timeout_gap_2026-03-15.md) / [../openamp_phase5_fit03_watchdog_success_2026-03-15.md](../openamp_phase5_fit03_watchdog_success_2026-03-15.md) |

## 答辩口径

建议按下面的顺序讲解：

1. 先用 [../openamp_phase5_release_v1.4.0_cold_boot_and_demo_success_2026-03-14.md](../openamp_phase5_release_v1.4.0_cold_boot_and_demo_success_2026-03-14.md) 证明板级 cold boot、remoteproc、RPMsg demo 路径已经通过门禁。
2. 再用 [coverage_matrix.md](coverage_matrix.md) 说明 P0 不是 mock，而是板级 `STATUS -> JOB_REQ -> HEARTBEAT -> SAFE_STOP / JOB_DONE` 全链路都有证据。
3. 接着强调 wrapper 不是本地自判： [../openamp_wrapper_hook_board_smoke_success_2026-03-14.md](../openamp_wrapper_hook_board_smoke_success_2026-03-14.md) 已证明真实 `firmware_job_ack` 可以驱动 runner 放行。
4. 最后用三项 FIT 收口风险：`FIT-01` 收口未知 artifact 执行风险，`FIT-02` 收口输入契约违规风险，`FIT-03` 以“先失败、后修复、再通过”的方式收口 heartbeat watchdog 风险。

## FIT-03 历史说明

`FIT-03` 需要按两段历史来表述，不能只报最终 PASS：

- old live firmware 阶段：
  - [../openamp_heartbeat_timeout_fit_20260315_015841/fit_report_FIT-03.md](../openamp_heartbeat_timeout_fit_20260315_015841/fit_report_FIT-03.md)
  - 真实结果是停发 heartbeat `5.0 s` 后板子仍保持 `JOB_ACTIVE`，说明 watchdog 缺口客观存在。
- watchdog-fix firmware 阶段：
  - [../openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410/fit_report_FIT-03.md](../openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410/fit_report_FIT-03.md)
  - 新 live firmware SHA 为 `2c4240e03deedd2cc6bbd1c7c34abee852aa8f7927a5187a5131659c4ce7878a`；同一探针顺序复跑后，follow-up `STATUS_RESP` 已变为 `READY / HEARTBEAT_TIMEOUT(F003)`。

这条历史非常关键，因为它证明团队不是在回避失败，而是在真实板级证据上完成了缺口确认、修复、复验和收口。

## 边界

这份总结包只对当前已经完成并已真机落证的 OpenAMP 控制面能力负责：

- P0 最小控制闭环里已经通过的里程碑
- P1 里已经正式收口的 `FIT-01`、`FIT-02`、`FIT-03`

这份包不主张以下尚未完成或未纳入本轮答辩范围的能力：

- `FIT-04`
- `FIT-05`
- `RESET_REQ/ACK`
- deadline enforcement
