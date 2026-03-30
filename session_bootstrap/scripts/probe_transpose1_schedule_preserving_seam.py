#!/usr/bin/env python3
"""Probe a schedule-preserving handwritten evaluation seam from local artifacts.

This helper is intentionally local-only. It does not claim performance validity.
It answers a narrower contract question:

- can the best scheduled task for a chosen operator be recovered from the
  staged MetaSchedule database?
- after MetaScheduleApplyDatabase, does the full module still expose a
  scheduled PrimFunc for that operator that could become a post-database
  handwritten hook seam?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from relax_ms_utils import load_onnx_to_relax, summarize_task_stages

DEFAULT_OPERATOR = "fused_conv2d_transpose1_add9"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe whether a local tune output exposes a schedule-preserving "
            "handwritten seam for a specific operator."
        )
    )
    parser.add_argument(
        "--task-summary",
        type=Path,
        required=True,
        help="Path to task_summary.json from a staged tune output.",
    )
    parser.add_argument(
        "--database-dir",
        type=Path,
        required=True,
        help="Directory containing database_workload.json and database_tuning_record.json.",
    )
    parser.add_argument(
        "--operator",
        default=DEFAULT_OPERATOR,
        help=f"Operator/task name to probe. Default: {DEFAULT_OPERATOR}",
    )
    parser.add_argument(
        "--build-standalone-scheduled-task",
        action="store_true",
        help=(
            "Also attempt a local tvm.build() of the scheduled per-task IRModule. "
            "This is a structural build probe only, not a benchmark."
        ),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional output path for the probe JSON report.",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def require_database_dir(path: Path) -> Path:
    directory = require_dir(path, "database dir")
    require_file(directory / "database_workload.json", "database workload")
    require_file(directory / "database_tuning_record.json", "database tuning record")
    return directory


def parse_input_shape(raw_value: str) -> list[int]:
    dims = [item.strip() for item in str(raw_value).split(",") if item.strip()]
    if not dims:
        raise SystemExit(f"ERROR: invalid input_shape: {raw_value!r}")
    try:
        return [int(item) for item in dims]
    except ValueError as err:
        raise SystemExit(f"ERROR: invalid input_shape: {raw_value!r}") from err


def load_task_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(require_file(path, "task summary").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"ERROR: unexpected task summary payload in {path}")
    return payload


def find_stage_task_row(task_summary: dict[str, Any], operator: str) -> dict[str, Any] | None:
    stages = task_summary.get("stages")
    if not isinstance(stages, dict):
        return None

    for stage_name, stage_payload in stages.items():
        if not isinstance(stage_payload, dict):
            continue
        tasks = stage_payload.get("tasks")
        if not isinstance(tasks, list):
            continue
        for row in tasks:
            if not isinstance(row, dict):
                continue
            if row.get("task_name") == operator:
                result = dict(row)
                result["stage_name"] = stage_name
                return result
    return None


def _as_float_list(values: Any) -> list[float] | None:
    if values is None:
        return None
    if not isinstance(values, (list, tuple)):
        return None
    result: list[float] = []
    for value in values:
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            return None
    return result


def probe_schedule_seam(
    task_summary_path: Path,
    database_dir: Path,
    operator: str,
    *,
    build_standalone_scheduled_task: bool,
) -> dict[str, Any]:
    import tvm  # pylint: disable=import-outside-toplevel
    from tvm.relax.transform import (  # pylint: disable=import-outside-toplevel
        MetaScheduleApplyDatabase,
    )
    from tvm.s_tir.meta_schedule.database import (  # pylint: disable=import-outside-toplevel
        JSONDatabase,
    )
    from tvm.s_tir.meta_schedule.relax_integration import (  # pylint: disable=import-outside-toplevel
        extract_tasks,
    )

    task_summary = load_task_summary(task_summary_path)
    database_dir = require_database_dir(database_dir)
    onnx_path = require_file(Path(task_summary["onnx_path"]), "onnx model")
    input_shape = parse_input_shape(task_summary["input_shape"])
    input_name = str(task_summary.get("input_name") or "input")
    input_dtype = str(task_summary.get("input_dtype") or "float32")
    target = tvm.target.Target(task_summary["target"])

    raw_mod = load_onnx_to_relax(
        onnx_path=str(onnx_path),
        input_name=input_name,
        input_shape=input_shape,
        input_dtype=input_dtype,
    )
    tuned_mod, task_stages = summarize_task_stages(raw_mod, target)
    extracted_tasks = list(extract_tasks(tuned_mod, target))
    extracted_task = next((task for task in extracted_tasks if task.task_name == operator), None)
    if extracted_task is None:
        raise SystemExit(
            "ERROR: operator is absent from extracted tuned tasks: "
            f"{operator}"
        )

    db = JSONDatabase(
        str(database_dir / "database_workload.json"),
        str(database_dir / "database_tuning_record.json"),
    )

    scheduled_record = db.query_tuning_record(
        extracted_task.dispatched[0],
        target,
        extracted_task.task_name,
    )
    scheduled_ir_module = db.query_ir_module(
        extracted_task.dispatched[0],
        target,
        extracted_task.task_name,
    )
    scheduled_schedule = db.query_schedule(
        extracted_task.dispatched[0],
        target,
        extracted_task.task_name,
    )

    standalone_build = {
        "attempted": bool(build_standalone_scheduled_task),
        "status": "skipped",
        "error": None,
    }
    if build_standalone_scheduled_task:
        if scheduled_ir_module is None:
            standalone_build["status"] = "missing_scheduled_ir_module"
        else:
            try:
                tvm.build(scheduled_ir_module, target=target)
            except Exception as err:  # pragma: no cover - integration-only path
                standalone_build["status"] = "failed"
                standalone_build["error"] = f"{type(err).__name__}: {err}"
            else:
                standalone_build["status"] = "built"

    with target, db, tvm.transform.PassContext(opt_level=3):
        applied_mod = MetaScheduleApplyDatabase(enable_warning=False)(tuned_mod)

    applied_global_var_names = [gv.name_hint for gv in applied_mod.get_global_vars()]
    applied_operator_func: Any | None = None
    applied_operator_present = operator in applied_global_var_names
    if applied_operator_present:
        applied_operator_func = applied_mod[applied_mod.get_global_var(operator)]

    report = {
        "task_summary_json": str(task_summary_path.resolve()),
        "database_dir": str(database_dir.resolve()),
        "operator": operator,
        "task_summary_row": find_stage_task_row(task_summary, operator),
        "reconstructed_task_row": find_stage_task_row({"stages": task_stages}, operator),
        "extracted_task": {
            "task_name": extracted_task.task_name,
            "weight": int(extracted_task.weight),
            "dispatched_count": len(extracted_task.dispatched),
            "dispatched_global_vars": [
                gv.name_hint for gv in extracted_task.dispatched[0].get_global_vars()
            ],
            "dispatched_tir_is_scheduled": bool(
                extracted_task.dispatched[0].attrs
                and extracted_task.dispatched[0].attrs.get("tir.is_scheduled", False)
            ),
        },
        "database_lookup": {
            "query_tuning_record_hit": scheduled_record is not None,
            "query_ir_module_hit": scheduled_ir_module is not None,
            "query_schedule_hit": scheduled_schedule is not None,
            "scheduled_run_secs": None
            if scheduled_record is None
            else _as_float_list(scheduled_record.run_secs),
            "scheduled_tuning_record_trace_inst_count": None
            if scheduled_record is None
            else len(scheduled_record.trace.insts),
            "scheduled_trace_inst_count": None
            if scheduled_schedule is None
            else len(scheduled_schedule.trace.insts),
            "scheduled_ir_module_global_vars": None
            if scheduled_ir_module is None
            else [gv.name_hint for gv in scheduled_ir_module.get_global_vars()],
            "query_schedule_matches_query_ir_module": (
                None
                if scheduled_schedule is None or scheduled_ir_module is None
                else bool(tvm.ir.structural_equal(scheduled_schedule.mod, scheduled_ir_module))
            ),
        },
        "standalone_scheduled_task_build": standalone_build,
        "post_database_apply": {
            "operator_present": applied_operator_present,
            "operator_tir_is_scheduled": bool(
                applied_operator_func is not None
                and applied_operator_func.attrs
                and applied_operator_func.attrs.get("tir.is_scheduled", False)
            ),
            "operator_func_type": None
            if applied_operator_func is None
            else type(applied_operator_func).__name__,
            "global_var_names_sample": applied_global_var_names[:40],
        },
        "recommended_seam": {
            "seam_id": "post_database_scheduled_primfunc_swap",
            "why": (
                "Apply MetaScheduleApplyDatabase first, then expose/replace the "
                "named scheduled PrimFunc inside the applied module."
            ),
            "precondition": (
                "Handwritten candidates must be authored against the scheduled "
                "operator form or an explicitly derived scheduled editable seed, "
                "not the raw pre-compile seed."
            ),
        },
    }
    return report


def main() -> None:
    args = parse_args()
    report = probe_schedule_seam(
        task_summary_path=args.task_summary,
        database_dir=args.database_dir,
        operator=args.operator,
        build_standalone_scheduled_task=args.build_standalone_scheduled_task,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
