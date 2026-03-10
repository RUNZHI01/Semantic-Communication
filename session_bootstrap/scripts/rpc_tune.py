#!/usr/bin/env python3
"""RPC-based MetaSchedule tuning script.

Runs on the laptop (builder/orchestrator). Searches and compiles locally,
measures on a remote ARMv8 device via TVM RPC.

Usage:
    python rpc_tune.py \
        --onnx-path /path/to/model.onnx \
        --output-dir ./tune_output \
        --target 'llvm -mtriple=aarch64-linux-gnu -mcpu=generic -mattr=+neon' \
        --tracker-host 127.0.0.1 \
        --tracker-port 9190 \
        --device-key armv8 \
        --total-trials 500 \
        --input-shape 1,32,32,32

    Set --runner local to skip RPC and measure locally (for smoke testing).
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time

from relax_ms_utils import (
    RAW_STAGE_NAME,
    TUNED_STAGE_NAME,
    load_onnx_to_relax as load_onnx_to_relax_module,
    summarize_task_stages,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rpc_tune")


def parse_args():
    p = argparse.ArgumentParser(description="RPC MetaSchedule tuning")
    p.add_argument("--onnx-path", required=True, help="Path to ONNX model")
    p.add_argument("--output-dir", required=True, help="Directory for tune artifacts")
    p.add_argument("--target", required=True, help="TVM target string")
    p.add_argument("--tracker-host", default="127.0.0.1")
    p.add_argument("--tracker-port", type=int, default=9190)
    p.add_argument("--device-key", default="armv8")
    p.add_argument("--total-trials", type=int, default=500)
    p.add_argument("--max-trials-per-task", type=int, default=None)
    p.add_argument("--num-trials-per-iter", type=int, default=64)
    p.add_argument(
        "--input-shape",
        required=True,
        help="Comma-separated input shape, e.g. 1,32,32,32",
    )
    p.add_argument("--input-name", default="input", help="ONNX input tensor name")
    p.add_argument("--input-dtype", default="float32")
    p.add_argument(
        "--op-names",
        default="",
        help="Optional comma-separated task names/substrings to tune",
    )
    p.add_argument(
        "--existing-db",
        default="",
        help="Path to existing tuning_logs dir for warm-start",
    )
    p.add_argument(
        "--runner",
        choices=["rpc", "local"],
        default="rpc",
        help="Runner type: rpc (real device) or local (smoke test)",
    )
    p.add_argument("--session-timeout", type=int, default=120)
    return p.parse_args()


def load_onnx_to_relax(onnx_path, input_name, input_shape, input_dtype):
    """Load ONNX model and convert to Relax IR."""
    logger.info("Loading ONNX model: %s", onnx_path)
    mod = load_onnx_to_relax_module(
        onnx_path=onnx_path,
        input_name=input_name,
        input_shape=list(input_shape),
        input_dtype=input_dtype,
    )
    logger.info("ONNX -> Relax IR conversion complete")
    return mod


def sanitize_tuning_records(work_dir):
    """Remove unsupported target feature keys from tuning records for compatibility."""
    record_path = os.path.join(work_dir, "database_tuning_record.json")
    if not os.path.isfile(record_path):
        return 0

    changed = 0
    out_lines = []
    with open(record_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                out_lines.append(raw.rstrip("\n"))
                continue

            target = None
            if (
                isinstance(rec, list)
                and len(rec) >= 2
                and isinstance(rec[1], list)
                and len(rec[1]) >= 3
                and isinstance(rec[1][2], dict)
            ):
                target = rec[1][2]

            if target is not None:
                keys = [k for k in list(target.keys()) if k.startswith("feature.")]
                if keys:
                    for k in keys:
                        target.pop(k, None)
                    changed += 1

            out_lines.append(json.dumps(rec, ensure_ascii=False))

    if changed > 0:
        with open(record_path, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines) + "\n")
        logger.info(
            "Sanitized tuning records: removed unsupported feature.* keys from %d record(s)",
            changed,
        )

    return changed


def prepare_warm_start(existing_db, work_dir):
    """Copy existing tuning database for warm-start."""
    if not existing_db or not os.path.isdir(existing_db):
        return

    for fname in ("database_workload.json", "database_tuning_record.json"):
        src = os.path.join(existing_db, fname)
        dst = os.path.join(work_dir, fname)
        if os.path.isfile(src) and not os.path.isfile(dst):
            shutil.copy2(src, dst)
            logger.info("Warm-start: copied %s -> %s", src, dst)

    sanitize_tuning_records(work_dir)


def build_rpc_runner(tracker_host, tracker_port, device_key, session_timeout):
    """Create an RPCRunner that measures on the remote device."""
    from tvm.s_tir.meta_schedule.runner import (  # pylint: disable=import-outside-toplevel
        RPCConfig,
        RPCRunner,
    )

    rpc_config = RPCConfig(
        tracker_host=tracker_host,
        tracker_port=tracker_port,
        tracker_key=device_key,
        session_timeout_sec=session_timeout,
    )
    runner = RPCRunner(rpc_config=rpc_config, max_workers=1)
    logger.info(
        "RPCRunner configured: %s:%d key=%s",
        tracker_host,
        tracker_port,
        device_key,
    )
    return runner


def parse_op_names(raw_value):
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def write_task_summary(output_dir, task_stages, args):
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "onnx_path": args.onnx_path,
        "target": args.target,
        "input_shape": args.input_shape,
        "task_stage_used_for_tuning": TUNED_STAGE_NAME,
        "raw_import_total_tasks": task_stages[RAW_STAGE_NAME]["total_tasks"],
        "tuned_stage_total_tasks": task_stages[TUNED_STAGE_NAME]["total_tasks"],
        "selected_op_names": parse_op_names(args.op_names),
        "stages": task_stages,
    }
    path = os.path.join(output_dir, "task_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info("Task summary written: %s", path)
    return path


def log_task_stage_summary(task_stages):
    logger.info(
        "Task visibility: raw_import=%d tuned_stage=%d (stage=%s)",
        task_stages[RAW_STAGE_NAME]["total_tasks"],
        task_stages[TUNED_STAGE_NAME]["total_tasks"],
        TUNED_STAGE_NAME,
    )
    for row in task_stages[TUNED_STAGE_NAME]["tasks"][:10]:
        logger.info(
            "Tuned-stage task: rank=%d name=%s weight=%d prim_funcs=%s",
            row["rank"],
            row["task_name"],
            row["weight"],
            ",".join(row["prim_funcs"]) if row["prim_funcs"] else "-",
        )


def warn_on_task_filter(task_stages, op_names):
    if not op_names:
        return

    raw_names = {row["task_name"] for row in task_stages[RAW_STAGE_NAME]["tasks"]}
    tuned_names = {row["task_name"] for row in task_stages[TUNED_STAGE_NAME]["tasks"]}
    missing = [name for name in op_names if name not in tuned_names]
    if missing:
        logger.warning(
            "Selected op/task names are absent from the tuned stage: %s",
            ",".join(missing),
        )

    if all(name in raw_names for name in op_names) and task_stages[TUNED_STAGE_NAME]["total_tasks"] > len(raw_names):
        logger.warning(
            "Selected op/task filter matches only the raw-import stage (%s). "
            "Regenerate FULL_HOTSPOT_TASKS with extract_hotspot_tasks.py before the next real run.",
            ",".join(op_names),
        )


def run_tune(mod, target, work_dir, runner, args):
    """Run MetaSchedule tuning via tune_relax."""
    from tvm.s_tir.meta_schedule.relax_integration import (  # pylint: disable=import-outside-toplevel
        tune_relax,
    )

    op_names = parse_op_names(args.op_names)
    logger.info(
        "Starting tune_relax: total_trials=%d, work_dir=%s",
        args.total_trials,
        work_dir,
    )
    if op_names:
        logger.info("Selected op/task filter: %s", ",".join(op_names))
    t0 = time.time()
    db = tune_relax(
        mod=mod,
        params={},
        target=target,
        work_dir=work_dir,
        max_trials_global=args.total_trials,
        max_trials_per_task=args.max_trials_per_task,
        op_names=op_names or None,
        num_trials_per_iter=args.num_trials_per_iter,
        runner=runner,
    )
    elapsed = time.time() - t0
    logger.info("tune_relax completed in %.1f seconds", elapsed)
    return db, elapsed


def compile_and_export(mod, target, database, output_dir):
    """Apply tuning database, compile, and export .so."""
    from tvm.s_tir.meta_schedule.relax_integration import (  # pylint: disable=import-outside-toplevel
        compile_relax,
    )

    logger.info("Applying tuning database and compiling...")
    ex = compile_relax(
        database=database,
        mod=mod,
        target=target,
        params={},
        enable_warning=False,
    )
    os.makedirs(output_dir, exist_ok=True)
    lib_path = os.path.join(output_dir, "optimized_model.so")
    ex.export_library(lib_path)
    logger.info("Compiled model exported: %s", lib_path)
    return lib_path


def write_tune_report(output_dir, args, elapsed_sec, lib_path, work_dir, task_summary_path, task_stages):
    """Write a JSON summary of the tuning run."""
    report = {
        "onnx_path": args.onnx_path,
        "target": args.target,
        "input_shape": args.input_shape,
        "total_trials": args.total_trials,
        "runner": args.runner,
        "tracker_host": args.tracker_host,
        "tracker_port": args.tracker_port,
        "device_key": args.device_key,
        "elapsed_sec": round(elapsed_sec, 1),
        "output_so": lib_path,
        "tuning_logs_dir": work_dir,
        "existing_db": args.existing_db or None,
        "task_stage_used_for_tuning": TUNED_STAGE_NAME,
        "raw_import_total_tasks": task_stages[RAW_STAGE_NAME]["total_tasks"],
        "tuned_stage_total_tasks": task_stages[TUNED_STAGE_NAME]["total_tasks"],
        "selected_op_names": parse_op_names(args.op_names),
        "task_summary_json": task_summary_path,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    report_path = os.path.join(output_dir, "tune_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Tune report written: %s", report_path)
    return report_path


def main():
    args = parse_args()

    input_shape = [int(x) for x in args.input_shape.split(",")]
    if len(input_shape) < 2:
        logger.error("Invalid --input-shape: %s", args.input_shape)
        sys.exit(1)

    if not os.path.isfile(args.onnx_path):
        logger.error("ONNX file not found: %s", args.onnx_path)
        sys.exit(1)

    import tvm  # pylint: disable=import-outside-toplevel

    target = tvm.target.Target(args.target)

    output_dir = os.path.abspath(args.output_dir)
    work_dir = os.path.join(output_dir, "tuning_logs")
    os.makedirs(work_dir, exist_ok=True)

    prepare_warm_start(args.existing_db, work_dir)

    raw_mod = load_onnx_to_relax(args.onnx_path, args.input_name, input_shape, args.input_dtype)
    mod, task_stages = summarize_task_stages(raw_mod, target)
    log_task_stage_summary(task_stages)
    warn_on_task_filter(task_stages, parse_op_names(args.op_names))
    task_summary_path = write_task_summary(output_dir, task_stages, args)

    if args.runner == "rpc":
        runner = build_rpc_runner(
            args.tracker_host,
            args.tracker_port,
            args.device_key,
            args.session_timeout,
        )
    else:
        runner = "local"

    db, elapsed = run_tune(mod, target, work_dir, runner, args)
    sanitize_tuning_records(work_dir)

    lib_path = compile_and_export(mod, target, db, output_dir)
    report_path = write_tune_report(
        output_dir,
        args,
        elapsed,
        lib_path,
        work_dir,
        task_summary_path,
        task_stages,
    )

    print(f"tune_output_dir={output_dir}")
    print(f"tune_so_path={lib_path}")
    print(f"tune_report={report_path}")
    print(f"task_summary_json={task_summary_path}")
    print(f"tune_elapsed_sec={elapsed:.1f}")


if __name__ == "__main__":
    main()
