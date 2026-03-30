#!/usr/bin/env python3
"""Probe the schedule-preserving seam for fused_conv2d_transpose1_add9.

This helper is intentionally local-only and diagnostic-only. It does not claim to
perform a valid handwritten performance evaluation. It only proves that the best
staging DB can recover the scheduled task/module for the transpose1 operator.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SESSION_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SESSION_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the best-staging MetaSchedule DB can recover the scheduled "
            "transpose1 task/module for local seam design work."
        )
    )
    parser.add_argument(
        "--task-summary",
        required=True,
        help="Path to a task_summary.json generated from the staged run.",
    )
    parser.add_argument(
        "--db-dir",
        required=True,
        help="Directory containing database_workload.json and database_tuning_record.json.",
    )
    parser.add_argument(
        "--task-name",
        default="fused_conv2d_transpose1_add9",
        help="Exact extracted task name to inspect.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    task_summary_path = Path(args.task_summary).resolve()
    db_dir = Path(args.db_dir).resolve()
    workload_path = db_dir / "database_workload.json"
    tuning_record_path = db_dir / "database_tuning_record.json"

    import tvm  # pylint: disable=import-outside-toplevel
    from tvm.relax.transform import MetaScheduleApplyDatabase  # pylint: disable=import-outside-toplevel
    from tvm.s_tir.meta_schedule.database import JSONDatabase  # pylint: disable=import-outside-toplevel
    from tvm.s_tir.meta_schedule.relax_integration import extract_tasks  # pylint: disable=import-outside-toplevel

    from session_bootstrap.scripts.relax_ms_utils import (  # pylint: disable=import-outside-toplevel
        load_onnx_to_relax,
        summarize_task_stages,
    )

    summary = json.loads(task_summary_path.read_text(encoding="utf-8"))
    input_shape = [int(x) for x in str(summary["input_shape"]).split(",")]
    mod = load_onnx_to_relax(summary["onnx_path"], "input", input_shape, "float32")
    target = tvm.target.Target(summary["target"])
    tuned_mod, _ = summarize_task_stages(mod, target)

    db = JSONDatabase(str(workload_path), str(tuning_record_path))
    extracted = list(extract_tasks(tuned_mod, target))
    task = next((task for task in extracted if task.task_name == args.task_name), None)
    if task is None:
        raise SystemExit(f"ERROR: task not found: {args.task_name}")

    task_mod = task.dispatched[0]
    record = db.query_tuning_record(task_mod, target, task.task_name)
    scheduled_mod = db.query_ir_module(task_mod, target, task.task_name)
    schedule = db.query_schedule(task_mod, target, task.task_name)

    with target, db, tvm.transform.PassContext(opt_level=3):
        applied = MetaScheduleApplyDatabase(enable_warning=False)(tuned_mod)
    applied_gvars = [gv.name_hint for gv in applied.get_global_vars()]
    scheduled_global_present = args.task_name in applied_gvars
    scheduled_global_attrs: dict[str, Any] | None = None
    if scheduled_global_present:
        func = applied[applied.get_global_var(args.task_name)]
        attrs = func.attrs if getattr(func, "attrs", None) else {}
        scheduled_global_attrs = {
            "tir.is_scheduled": bool(attrs.get("tir.is_scheduled", False)),
            "global_symbol": attrs.get("global_symbol"),
        }

    payload = {
        "status": "ok",
        "task_name": args.task_name,
        "task_found": True,
        "task_weight": int(task.weight),
        "task_dispatched_count": len(task.dispatched),
        "db_query_tuning_record": record is not None,
        "db_query_ir_module": scheduled_mod is not None,
        "db_query_schedule": schedule is not None,
        "query_schedule_trace_len": None if schedule is None else len(schedule.trace.insts),
        "query_schedule_matches_query_ir_module": (
            None
            if schedule is None or scheduled_mod is None
            else bool(tvm.ir.structural_equal(schedule.mod, scheduled_mod))
        ),
        "applied_module_has_named_global": scheduled_global_present,
        "applied_module_global_attrs": scheduled_global_attrs,
        "recommended_path_kind": "schedule_context_preserving_evaluation",
        "recommended_next_target": "post_db_scheduled_primfunc_swap",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
