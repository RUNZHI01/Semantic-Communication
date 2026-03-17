# big.LITTLE 明早执行交接（2026-03-18 夜间）

> 背景与完整细节见 `session_bootstrap/runbooks/big_little_pipeline_runbook_2026-03-18.md`。

## 1. repo 侧已完成

- 一键入口已就位：`session_bootstrap/scripts/run_big_little_first_real_attempt.sh`
- 固定真机 env 已就位：`session_bootstrap/config/big_little_pipeline.current.2026-03-18.phytium_pi.env`
- 只读拓扑探测与自动回填已就位：
  - `session_bootstrap/scripts/big_little_topology_probe.py`
  - `session_bootstrap/scripts/apply_big_little_topology_suggestion.py`
- pipeline 包装器与 serial-vs-pipeline compare 包装器已就位：
  - `session_bootstrap/scripts/run_big_little_pipeline.sh`
  - `session_bootstrap/scripts/run_big_little_compare.sh`
- repo 侧本地/mock 路径已跑通，说明命令编排、runtime env 复制、报告落盘都正常：
  - `session_bootstrap/reports/big_little_pipeline_mock_current_20260318_034742.md`
  - `session_bootstrap/reports/big_little_compare_20260318_034743.md`
- compare 的 serial 基线仍是现有可信 current 重建入口：`bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current`

## 2. 默认一键入口

```bash
bash ./session_bootstrap/scripts/run_big_little_first_real_attempt.sh
```

默认读取：

`./session_bootstrap/config/big_little_pipeline.current.2026-03-18.phytium_pi.env`

## 3. 手工展开链路（与默认入口一致）

```bash
SOURCE_ENV=./session_bootstrap/config/big_little_pipeline.current.2026-03-18.phytium_pi.env
STAMP="$(date +%Y%m%d_%H%M%S)"
RUNTIME_ENV="./session_bootstrap/config/big_little_pipeline.current.runtime_${STAMP}.env"

cp "$SOURCE_ENV" "$RUNTIME_ENV"

python3 ./session_bootstrap/scripts/big_little_topology_probe.py ssh \
  --env "$RUNTIME_ENV" \
  --timeout-sec 180 \
  --write-raw ./session_bootstrap/reports/big_little_topology_capture_latest.txt \
  > ./session_bootstrap/reports/big_little_topology_suggestion_latest.json

python3 ./session_bootstrap/scripts/apply_big_little_topology_suggestion.py \
  --env "$RUNTIME_ENV" \
  --suggestion ./session_bootstrap/reports/big_little_topology_suggestion_latest.json

bash ./session_bootstrap/scripts/run_big_little_pipeline.sh \
  --env "$RUNTIME_ENV" \
  --variant current

bash ./session_bootstrap/scripts/run_big_little_compare.sh \
  --env "$RUNTIME_ENV"
```

## 4. 当前 topology 建议与 caveat

- 当前最新的非空探测建议文件：`session_bootstrap/reports/big_little_topology_suggestion_20260318_0136.json`
- 建议值：
  - `BIG_LITTLE_BIG_CORES=2`
  - `BIG_LITTLE_LITTLE_CORES=0,1`
- 依据：在线 CPU 为 `0,1,2`，其中 CPU `2` 的 `MAXMHZ=1800`，CPU `0,1` 为 `1500`
- caveat：CPU `3` 在首轮探测时 offline，所以这只是明早首跑前的工作建议，不是最终硬编码结论；明早先重新跑一次只读 probe，再让脚本自动回填
- 额外提醒：`session_bootstrap/reports/big_little_topology_suggestion_latest.json` 当前是零字节临时文件，不要拿它当现成结论；明早重新 probe 后它会被覆盖成新的 latest

## 5. 预期输出

- runtime env 副本：`session_bootstrap/config/big_little_pipeline.current.runtime_<timestamp>.env`
- 最新 probe 产物：
  - `session_bootstrap/reports/big_little_topology_capture_latest.txt`
  - `session_bootstrap/reports/big_little_topology_suggestion_latest.json`
- pipeline 包装器产物：
  - `session_bootstrap/logs/big_little_pipeline_current_<timestamp>.log`
  - `session_bootstrap/reports/big_little_pipeline_current_<timestamp>.json`
  - `session_bootstrap/reports/big_little_pipeline_current_<timestamp>.md`
  - `session_bootstrap/reports/big_little_pipeline_current_<timestamp>.raw.log`
- compare 包装器产物：
  - `session_bootstrap/logs/big_little_compare_<timestamp>.log`
  - `session_bootstrap/reports/big_little_compare_<timestamp>.json`
  - `session_bootstrap/reports/big_little_compare_<timestamp>.md`
  - `session_bootstrap/reports/big_little_compare_<timestamp>.serial.raw.log`
  - `session_bootstrap/reports/big_little_compare_<timestamp>.pipeline.raw.log`
- 真机 pipeline 成功时，远端输出目录默认落在：`/home/user/Downloads/jscc-test/big_little_runs/big_little_pipeline_current`

## 6. 剩余真实 blocker

- 现在剩下的真实 blocker 只有一件事：明早在真实飞腾派上跑一次
- repo 侧脚本、env、runbook、拓扑探测、自动回填、报告落盘都已就位；本地/mock 结果只能证明链路可执行，不能替代真机结论
