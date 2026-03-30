#!/usr/bin/env python3
"""Run the transpose1 post-DB schedule-preserving local build path.

This is a thin operator-specific wrapper over
`probe_transpose1_schedule_preserving_seam.py`. It exists so the preferred local
workflow for `fused_conv2d_transpose1_add9` does not require the user to repeat
best-staging task-summary / DB paths by hand.

This helper is still local-only and diagnostic-only:
- it does not launch remote work
- it does not make runtime/performance claims
- it only produces build-level evidence for the post-db scheduled swap path
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_transpose1_schedule_preserving_seam as seam_probe

DEFAULT_TASK_SUMMARY = (
    Path(__file__).resolve().parents[1]
    / "tmp"
    / "phytium_runtime_joint_top6_targeted_staging_search_20260330_2315"
    / "task_summary.json"
)
DEFAULT_DATABASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "tmp"
    / "phytium_runtime_joint_top6_targeted_staging_search_20260330_2315"
    / "tuning_logs"
)
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "tmp"
    / "transpose1_post_db_swap_local_build"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-specific wrapper for the transpose1 post-db scheduled swap "
            "local build path."
        )
    )
    parser.add_argument(
        "--task-summary",
        type=Path,
        default=DEFAULT_TASK_SUMMARY,
        help="Best-staging task_summary.json for transpose1.",
    )
    parser.add_argument(
        "--database-dir",
        type=Path,
        default=DEFAULT_DATABASE_DIR,
        help="Best-staging tuning_logs directory for transpose1.",
    )
    parser.add_argument(
        "--candidate-impl",
        type=Path,
        default=seam_probe.DEFAULT_CANDIDATE_IMPL,
        help="Checked-in handwritten candidate entrypoint.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the local swapped artifact and adjacent JSON report.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional extra JSON report output path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = seam_probe.probe_schedule_seam(
        task_summary_path=args.task_summary,
        database_dir=args.database_dir,
        operator=seam_probe.DEFAULT_OPERATOR,
        candidate_impl=args.candidate_impl,
        build_standalone_scheduled_task=True,
        output_dir=args.output_dir,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    adjacent_report_path = None
    local_build_output = report.get("local_build_output")
    if isinstance(local_build_output, dict):
        report_path = local_build_output.get("report_path")
        if isinstance(report_path, str) and report_path.strip():
            adjacent_report_path = Path(report_path)
    seam_probe.write_report_outputs(
        payload,
        output_json=args.output_json,
        adjacent_report_path=adjacent_report_path,
    )
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
