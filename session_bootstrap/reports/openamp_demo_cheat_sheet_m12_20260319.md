# OpenAMP Demo Cheat Sheet M12

Date: 2026-03-19

Mode: `operator-assist only`. If anything looks unstable, stop clicking and switch to evidence wording.

Anchor facts:
- `8115` is the valid demo instance; recent `Current live = 300 / 300`; Scene 3 default baseline is the archived PyTorch reference.
- P0 is a board-backed control loop; `FIT-01`, `FIT-02`, and `FIT-03` final status are `PASS`, and `FIT-03` history stays `FAIL -> fix -> PASS`.

## 4-Scene Flow

- `01 可信状态 / 板卡接入与 gate` Click: `保存并复用本场凭据` -> `探测板卡 / OpenAMP` -> `demo-only 票据预检`. Say: "This first scene shows a real board-backed operator path: session, read-only probe, and gate verdict are visible before any live run." Fallback: "If the board is not cooperative, I stay on evidence mode: `8115` is the valid demo instance and the committed package already records board-online / RPMsg proof."
- `02 语义回传 / Current live` Click: `02 语义回传` -> `启动 Current 数据面 300 张图在线推进`. Say: "Current 300-image reconstruction is the live data plane; OpenAMP here is the control-plane and safety boundary, not the speedup path." Fallback: "If live does not finish cleanly, I say the page is showing archive/fallback state and I do not call it a fresh completion."
- `03 正式对照 / Compare` Click: `03 正式对照`; normally stop on `Compare Viewer`; do not default to `运行 PyTorch 数据面 300 张图`. Say: "This screen keeps the boundary honest: same-sample Current versus PyTorch reference, with 4-core Linux performance quotes kept separate from this 3-core Linux + RTOS live demo." Fallback: "I stay on the archived PyTorch reference and explain that the 2026-03-17 baseline `300 / 300` run is historical evidence, not this scene's default live branch."
- `04 故障注入与恢复 / SAFE_STOP` Click: `04 故障注入与恢复`; default to the FIT cards and `Blackbox Timeline`; only use `注入错误 SHA`, `注入心跳超时`, `注入非法参数`, or `SAFE_STOP 收口` if explicitly needed. Say: "The fault story is evidence-first: FIT-01, FIT-02, and FIT-03 are already board-backed, and SAFE_STOP remains a manual operator recovery path." Fallback: "If we keep the board untouched here, I stay on the FIT evidence and say we avoid turning the defense into a new on-stage experiment."

## Red Lines

- Never call the page automated; probe, gate preview, live launch, fault injection, and `SAFE_STOP` are manual operator actions.
- Never say `demo-only 票据预检` sends a real `JOB_REQ` or starts execution.
- Never say `Link Director` applies real weak-link control; it is `ui_scaffold_only`.
- Never mix `4-core Linux performance mode` headline numbers with the `3-core Linux + RTOS demo mode` live path.
- Never present Scene 3 default as baseline live; the default compare is the archived PyTorch reference.
- Never call archive/fallback material a fresh live result.
- Never claim `FIT-04`, `FIT-05`, `RESET_REQ/ACK`, deadline enforcement, or a complete fault-recovery system.
- Never say Linux owns physical `SAFE_STOP/GPIO`; it mirrors RTOS / Bare Metal.
- Never say the current live firmware is byte-identical to the original official firmware.

Basis: committed `README.md`, committed cockpit UI labels, the committed evidence-package runbook / summary / coverage matrix, and the committed M7 / M8 / M10 / M11 docs in `HEAD`.
