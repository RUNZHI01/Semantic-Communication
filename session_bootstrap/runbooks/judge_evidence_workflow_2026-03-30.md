# Judge Evidence Workflow

更新时间：`2026-03-30`
适用范围：评委追问补证 / 技术文档补页 / 答辩附录，不覆盖 demo / admission 交付

这条工作流只做两件事：

- 把仓库里已经存在的 `quality / hotspot / resource / snr` 历史结果统一整理成 judge-facing 材料。
- 对仍然必须上板的步骤，只保留**精确命令**，不在本地自动尝试 SSH / 远端执行。

## 1. 当前推荐入口

已生成的 judge-facing 材料：

- `session_bootstrap/reports/judge_quality_formal_report_20260330.md`
- `session_bootstrap/reports/judge_quality_formal_report_20260330.json`
- `session_bootstrap/reports/judge_quality_formal_report_20260330_lpips_full.md`
- `session_bootstrap/reports/judge_quality_formal_report_20260330_lpips_full.json`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4.md`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4.json`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4_latency.svg`
- `session_bootstrap/reports/judge_snr_robustness_20260330_current_chunk4_quality.svg`
- `session_bootstrap/reports/judge_evidence_pack_20260330_current_chunk4_lpips_full.md`
- `session_bootstrap/reports/judge_evidence_pack_20260330_current_chunk4_lpips_full.json`
- `session_bootstrap/reports/defense_quick_reference_card_20260330_current_chunk4.md`

对应脚本入口：

- `session_bootstrap/scripts/build_quality_matrix_report.py`
- `session_bootstrap/scripts/build_snr_robustness_report.py`
- `session_bootstrap/scripts/build_judge_evidence_pack.py`

## 2. 本地生成顺序

### 2.1 Formal Quality Report

默认会自动抓取仓库里最新的三份质量 JSON：

- `quality_metrics_*pytorch_vs_tvm_baseline.json`
- `quality_metrics_*pytorch_vs_tvm_current.json`
- `quality_metrics_*tvm_baseline_vs_tvm_current.json`

命令：

```bash
python3 ./session_bootstrap/scripts/build_quality_matrix_report.py \
  --report-prefix ./session_bootstrap/reports/judge_quality_formal_report_$(date +%Y%m%d)
```

输出：

- `judge_quality_formal_report_<date>.md`
- `judge_quality_formal_report_<date>.json`

### 2.2 Multi-SNR Robustness Report

默认会读取指定的 `snr_sweep_*.md` 汇总；当前最新推荐入口是 `snr_sweep_current_chunk4_20260330_152054.md`，它已经包含 trusted chunk4 的 `SNR=1/4/7/10/13` 实测 current latency，并可叠加同批质量 JSON 生成 judge-facing md/json/svg。

命令：

```bash
python3 ./session_bootstrap/scripts/build_snr_robustness_report.py \
  --summary-md ./session_bootstrap/reports/snr_sweep_2026-03-01.md \
  --report-prefix ./session_bootstrap/reports/judge_snr_robustness_$(date +%Y%m%d)
```

输出：

- `judge_snr_robustness_<date>.md`
- `judge_snr_robustness_<date>.json`
- `judge_snr_robustness_<date>_latency.svg`

说明：

- 当前仓库里只有历史 `latency vs SNR`，还没有按 SNR 归档的 `quality vs SNR` JSON。
- 该脚本会把这个缺口明确写进报告，并附上手工补采命令。

### 2.3 Unified Judge Evidence Pack

命令：

```bash
python3 ./session_bootstrap/scripts/build_judge_evidence_pack.py \
  --quality-formal-json ./session_bootstrap/reports/judge_quality_formal_report_20260330.json \
  --hotspot-json ./session_bootstrap/reports/profiling_trusted_current_20260312_154323.json \
  --resource-json ./session_bootstrap/reports/resource_profile_trusted_current_20260312_001.json \
  --snr-json ./session_bootstrap/reports/judge_snr_robustness_20260330.json \
  --payload-report-md ./session_bootstrap/reports/inference_compare_currentsafe_chunk4_refresh_20260313_1758.md \
  --e2e-report-md ./session_bootstrap/reports/inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md \
  --big-little-summary-md ./session_bootstrap/reports/big_little_real_run_summary_20260318.md \
  --report-prefix ./session_bootstrap/reports/judge_evidence_pack_$(date +%Y%m%d)
```

输出：

- `judge_evidence_pack_<date>.md`
- `judge_evidence_pack_<date>.json`

内容包括：

- trusted payload / e2e headline
- PSNR / SSIM / LPIPS formal quality摘要
- operator hotspot / profiling fallback status
- CPU / memory / artifact-size 资源画像
- multi-SNR robustness 摘要
- “slide -> claim -> evidence” defense map

## 3. 仅文档保留的手工命令

下面这些步骤需要上板或远端环境，本工作流**不自动执行**，只保留命令给主操作人手动跑。

### 3.1 补齐 quality-vs-SNR

当前正式入口已经写进：

- `session_bootstrap/reports/judge_snr_robustness_20260330.md`
- `session_bootstrap/reports/judge_evidence_pack_20260330.md`

命令：

```bash
for snr in 1 4 7 10 13; do
  RUN_TAG="judge_snr_${snr}_$(date +%Y%m%d_%H%M%S)"
  ENV_COPY="session_bootstrap/tmp/${RUN_TAG}.env"
  cp session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env "$ENV_COPY"
  sed -i \
    -e "s#^INFERENCE_OUTPUT_PREFIX=.*#INFERENCE_OUTPUT_PREFIX=${RUN_TAG}#" \
    -e "s#^INFERENCE_REAL_OUTPUT_PREFIX=.*#INFERENCE_REAL_OUTPUT_PREFIX=${RUN_TAG}#" \
    -e "s#^REMOTE_SNR_CURRENT=.*#REMOTE_SNR_CURRENT=${snr}#" \
    "$ENV_COPY"

  bash ./session_bootstrap/scripts/run_remote_pytorch_reference_reconstruction.sh \
    --env-file "$ENV_COPY" \
    --output-prefix "${RUN_TAG}_pytorch_ref" \
    --snr "$snr"

  set -a
  source "$ENV_COPY"
  set +a
  bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current

  REF_DIR="${REMOTE_OUTPUT_BASE}/${RUN_TAG}_pytorch_ref"
  CUR_DIR="${REMOTE_OUTPUT_BASE}/${RUN_TAG}_current"
  python3 ./session_bootstrap/scripts/compute_image_quality_metrics.py \
    --ref-dir "${REF_DIR}/reconstructions" \
    --test-dir "${CUR_DIR}/reconstructions" \
    --comparison-label "pytorch_vs_tvm_current_snr${snr}" \
    --report-prefix "session_bootstrap/reports/${RUN_TAG}_quality"
done
```

补采完成后，把每个 `snr -> quality json` 重新喂给：

```bash
python3 ./session_bootstrap/scripts/build_snr_robustness_report.py \
  --summary-md ./session_bootstrap/reports/snr_sweep_2026-03-01.md \
  --quality-json 1:./session_bootstrap/reports/<snr1_quality>.json \
  --quality-json 4:./session_bootstrap/reports/<snr4_quality>.json \
  --quality-json 7:./session_bootstrap/reports/<snr7_quality>.json \
  --quality-json 10:./session_bootstrap/reports/<snr10_quality>.json \
  --quality-json 13:./session_bootstrap/reports/<snr13_quality>.json \
  --report-prefix ./session_bootstrap/reports/judge_snr_robustness_<date>
```

### 3.2 手工刷新 task-5.1 operator profiling

当前默认 judge-facing 口径是：

- 已有 stage-weight hotspot evidence
- trusted runtime per-op profiling 仍 fallback，因为远端 runtime 缺少稳定的 `vm.profile` 能力

如已准备好 profiler-capable runtime，再手工执行：

```bash
python3 ./session_bootstrap/scripts/run_task_5_1_operator_profile.py \
  --run-id profiling_judge_refresh_$(date +%Y%m%d_%H%M%S) \
  --hotspot-mode reuse \
  --hotspot-existing-json ./session_bootstrap/reports/hotspot_tasks_20260310_2329.json \
  --hotspot-existing-md ./session_bootstrap/reports/hotspot_tasks_20260310_2329.md \
  --runtime-mode attempt \
  --trusted-env ./session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env \
  --profile-samples 1 \
  --max-inputs 1
```

### 3.3 手工刷新资源画像

如需新的 board-side CPU / memory 画像，手工执行：

```bash
bash ./session_bootstrap/scripts/run_remote_resource_profile.sh \
  --env ./session_bootstrap/tmp/inference_real_reconstruction_compare_run_20260311_212301.env \
  --trusted-variant current \
  --run-id resource_profile_judge_refresh_$(date +%Y%m%d_%H%M%S)
```

## 4. Judge-Facing 最终引用顺序

推荐评委材料引用顺序：

1. `judge_evidence_pack_20260330_current_chunk4_lpips_full.md`
2. `judge_quality_formal_report_20260330_lpips_full.md`
3. `judge_snr_robustness_20260330_current_chunk4.md`
4. `inference_compare_currentsafe_chunk4_refresh_20260313_1758.md`
5. `inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md`
6. `profiling_judge_refresh_20260330_170808.md`
7. `resource_profile_trusted_current_chunk4_20260330_151728.md`

## 5. 结论

到 `2026-03-30` 为止：

- judge-facing 本地整理工作流已经具备。
- 历史质量 / hotspot / resource / snr 结果已经被统一串成正式材料。
- 真正还缺的不是“文档结构”，而是 `quality-vs-SNR` 与 profiler-enabled runtime 这两条需要上板手工补采的数据。
