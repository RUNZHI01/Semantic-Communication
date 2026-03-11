# Fair Scheme A Pure-Inference Compare Status

- generated_at: 2026-03-11T13:38:00+08:00
- scope: Phytium Pi baseline vs current pure-inference comparison

## Scheme A implementation

- No new runner was required.
- The smallest clean implementation is to drive both variants through `session_bootstrap/scripts/run_remote_tvm_inference_payload.sh`, which already measures:
  - `load_module()` once
  - `relax.VirtualMachine(...)` once
  - warmup runs
  - repeated `main()` calls
- Dedicated remote env for this fair path:
  - `session_bootstrap/config/inference_compare_scheme_a_fair.2026-03-11.phytium_pi.env`
- Benchmark harness now reports configured baseline/current SHA guards symmetrically.

## Validation

### 1. Local end-to-end Scheme A validation

Local validation was run with both baseline and current on the payload path using the existing local fixture archives.

- report: `session_bootstrap/reports/inference_local_scheme_a_payload_20260311_133729.md`
- baseline median: `701.551 ms`
- current median: `702.862 ms`
- delta (`current - baseline`): `+1.311 ms`
- result: the payload-vs-payload path itself does **not** create a large synthetic speed gap

### 2. Real Phytium Pi attempt from this session

Attempted command:

```bash
bash ./session_bootstrap/scripts/run_inference_benchmark.sh \
  --env ./session_bootstrap/config/inference_compare_scheme_a_fair.2026-03-11.phytium_pi.env
```

Artifacts:

- report: `session_bootstrap/reports/inference_20260311_133750.md`
- log: `session_bootstrap/logs/inference_20260311_133750.log`

Observed blocker:

```text
socket: Operation not permitted
ssh: connect to host 100.121.87.73 port 22: failure
```

This is a sandbox/network restriction in the current session, so the fair Pi medians were not collected here.

## Conclusion

- The previous report at `session_bootstrap/reports/inference_compare_baseline_vs_currentsafe_rerun_20260311_114828.md` showed a very large gain, but that result mixed legacy baseline semantics with payload current semantics.
- Under the fairer Scheme A design, that previous conclusion is **not yet confirmed** from this session because the real Pi run was blocked before baseline execution started.
- The local apples-to-apples validation materially **weakens confidence** that the earlier `~91.66%` gain was a pure kernel-time effect of the current artifact alone.

## Remaining step on an unrestricted host

Run:

```bash
bash ./session_bootstrap/scripts/run_inference_benchmark.sh \
  --env ./session_bootstrap/config/inference_compare_scheme_a_fair.2026-03-11.phytium_pi.env
```

Then use the resulting report/raw csv as the authoritative fair Scheme A Pi comparison.
