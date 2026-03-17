# big.LITTLE Pipeline Runbook

## Goal

Produce a low-risk heterogeneous-core result tomorrow without changing board firmware or rebooting:

1. keep the trusted serial reconstruction path as the baseline;
2. run the new pipeline path with explicit CPU-role binding;
3. optionally wrap the pipeline path with the existing resource profiler.

## Shortest Credible Path

Use the repo-side wrappers added tonight:

- pipeline run:

```bash
bash ./session_bootstrap/scripts/run_big_little_pipeline.sh \
  --env session_bootstrap/config/<your-big-little-env>.env \
  --variant current
```

- serial vs pipeline comparison:

```bash
bash ./session_bootstrap/scripts/run_big_little_compare.sh \
  --env session_bootstrap/config/<your-big-little-env>.env
```

This preserves the trusted serial command as the baseline while giving the pipeline path its own isolated wrapper and report files.

## Env Files

Start from one of:

- `session_bootstrap/config/big_little_pipeline.current.example.env`
- `session_bootstrap/config/big_little_pipeline.mock.local.example.env`

Critical fields to fill before the first board run:

- `BIG_LITTLE_BIG_CORES`
- `BIG_LITTLE_LITTLE_CORES`
- `REMOTE_INPUT_DIR`
- `REMOTE_OUTPUT_BASE`
- `REMOTE_TVM_PYTHON`
- `REMOTE_CURRENT_ARTIFACT` or `INFERENCE_CURRENT_ARCHIVE`

## Read-Only Board Inspection

Run the repo-side topology helper once tomorrow, before the first real run:

```bash
python3 ./session_bootstrap/scripts/big_little_topology_probe.py ssh \
  --env session_bootstrap/config/<your-big-little-env>.env
```

The helper performs a read-only SSH probe, runs only `lscpu` / `lscpu -e`, and prints:

- a structured JSON summary
- a suggested `BIG_LITTLE_BIG_CORES=...`
- a suggested `BIG_LITTLE_LITTLE_CORES=...`

If you want a local reparseable capture file as well:

```bash
python3 ./session_bootstrap/scripts/big_little_topology_probe.py ssh \
  --env session_bootstrap/config/<your-big-little-env>.env \
  --write-raw session_bootstrap/reports/big_little_topology_capture_latest.txt
```

Fallback raw commands, if you need to inspect the board output yourself:

```bash
lscpu
lscpu -e=CPU,CORE,SOCKET,NODE,MAXMHZ,MINMHZ
```

Use the helper suggestion, or those raw outputs if needed, only to confirm the CPU numbering for:

- `BIG_LITTLE_BIG_CORES`
- `BIG_LITTLE_LITTLE_CORES`

Keep `BIG_LITTLE_ALLOW_MISSING_AFFINITY=0` for the first real run so any affinity failure surfaces immediately.

## Expected Outputs

Pipeline wrapper artifacts:

- `session_bootstrap/logs/big_little_pipeline_<variant>_<timestamp>.log`
- `session_bootstrap/reports/big_little_pipeline_<variant>_<timestamp>.json`
- `session_bootstrap/reports/big_little_pipeline_<variant>_<timestamp>.md`

Compare wrapper artifacts:

- `session_bootstrap/logs/big_little_compare_<timestamp>.log`
- `session_bootstrap/reports/big_little_compare_<timestamp>.json`
- `session_bootstrap/reports/big_little_compare_<timestamp>.md`

## Optional Resource Profiling

Because the env template pins `INFERENCE_CURRENT_CMD` to the new pipeline wrapper, the existing profiler can capture free/top/vmstat around the pipeline run with no new board-side script:

```bash
bash ./session_bootstrap/scripts/run_remote_resource_profile.sh \
  --env session_bootstrap/config/<your-big-little-env>.env \
  --trusted-variant current
```

## Local Dry-Run

Tonight's repo-only validation path:

1. create a placeholder artifact file locally;
2. create a handful of `.npy` latent inputs in the mock input directory;
3. run the local mock env with `BIG_LITTLE_DRY_RUN=1`.

This validates:

- argument shaping
- worker orchestration
- queue handoff
- affinity handling in permissive mode
- local JSON/Markdown report generation
