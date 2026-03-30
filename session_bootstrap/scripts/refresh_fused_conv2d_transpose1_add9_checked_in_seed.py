#!/usr/bin/env python3
"""Refresh the checked-in editable seed for fused_conv2d_transpose1_add9.

This helper stays narrow on purpose:
- read the existing local-only seed capture under session_bootstrap/tmp
- keep a checked-in manifest derived from the captured seed JSON
- extract the real operator TIR from the local MetaSchedule task log
- avoid changing rebuild hooks or trusted-current paths
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_NAME = "fused_conv2d_transpose1_add9"
DEFAULT_SEED_JSON = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "handwritten_fused_conv2d_transpose1_add9_scaffold"
    / f"{OPERATOR_NAME}_manual_seed.json"
)
DEFAULT_SEED_TIR = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "handwritten_fused_conv2d_transpose1_add9_scaffold"
    / f"{OPERATOR_NAME}_manual_seed_tir.py"
)
DEFAULT_TASK_LOG = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "handwritten_fused_conv2d_transpose1_add9_seed_capture"
    / "tuning_logs"
    / "logs"
    / "tvm.s_tir.meta_schedule.logging.task_0_fused_conv2d_transpose1_add9.log"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "session_bootstrap" / "handwritten" / "fused_conv2d_transpose1_add9"
)
EDITABLE_TIR_FILENAME = f"{OPERATOR_NAME}_editable_seed_tir.py"
MANIFEST_FILENAME = "seed_manifest.json"
README_FILENAME = "README.md"
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} ")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh the checked-in editable seed package for "
            f"{OPERATOR_NAME} from the latest local seed capture."
        )
    )
    parser.add_argument(
        "--seed-json",
        type=Path,
        default=DEFAULT_SEED_JSON,
        help="Captured manual seed JSON emitted by the local-only seed hook.",
    )
    parser.add_argument(
        "--seed-tir",
        type=Path,
        default=DEFAULT_SEED_TIR,
        help="Captured pre-compile seed snapshot emitted by the local-only seed hook.",
    )
    parser.add_argument(
        "--task-log",
        type=Path,
        default=DEFAULT_TASK_LOG,
        help="MetaSchedule task log containing the operator TIR for this workload.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Repo-native directory that will hold the checked-in editable seed package.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwriting existing checked-in seed package files.",
    )
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def as_abs(path: Path) -> Path:
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def repo_native(path: Path | str) -> str:
    value = Path(path)
    resolved = value if value.is_absolute() else (PROJECT_ROOT / value).resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return str(resolved)
    return f"./{relative.as_posix()}"


def ensure_clean_outputs(paths: list[Path], allow_overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not allow_overwrite:
        joined = "\n  ".join(str(path) for path in existing)
        raise SystemExit(
            "ERROR: output already exists. Re-run with --allow-overwrite to refresh.\n"
            f"  {joined}"
        )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_seed_json(seed_json_path: Path) -> dict[str, Any]:
    payload = json.loads(seed_json_path.read_text(encoding="utf-8"))
    operator = payload.get("operator")
    if operator != OPERATOR_NAME:
        raise SystemExit(
            f"ERROR: expected seed operator {OPERATOR_NAME!r}, got {operator!r}"
        )
    return payload


def extract_initial_tir(task_log_path: Path) -> str:
    lines = task_log_path.read_text(encoding="utf-8").splitlines()
    marker = f'Initializing Task #0: "{OPERATOR_NAME}"'
    try:
        marker_index = next(i for i, line in enumerate(lines) if marker in line)
    except StopIteration as err:
        raise SystemExit(
            f"ERROR: could not find task marker for {OPERATOR_NAME} in {task_log_path}"
        ) from err

    start = None
    for index in range(marker_index + 1, len(lines)):
        if lines[index].startswith("# from tvm.script import ir as I"):
            start = index
            break
    if start is None:
        raise SystemExit(
            f"ERROR: could not find initial TIR script block in {task_log_path}"
        )

    collected: list[str] = []
    for index in range(start, len(lines)):
        line = lines[index]
        if index > start and TIMESTAMP_RE.match(line):
            break
        collected.append(line)

    tir_text = "\n".join(collected).strip()
    if not tir_text:
        raise SystemExit(f"ERROR: extracted empty TIR block from {task_log_path}")
    return tir_text + "\n"


def build_manifest(
    *,
    seed_payload: dict[str, Any],
    seed_json_path: Path,
    seed_tir_path: Path,
    task_log_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "operator": OPERATOR_NAME,
        "reference_staging_sha256": seed_payload.get("reference_staging_sha256"),
        "reference_profile_json": seed_payload.get("reference_profile_json"),
        "argument_shapes": seed_payload.get("argument_shapes"),
        "phase": seed_payload.get("phase"),
        "task_row": seed_payload.get("task_row"),
        "prim_func_capture": seed_payload.get("prim_func_capture"),
        "seed_capture_kind": seed_payload.get("seed_capture_kind"),
        "checked_in_edit_target": repo_native(output_dir / EDITABLE_TIR_FILENAME),
        "source_files": {
            "captured_seed_json": repo_native(seed_json_path),
            "captured_seed_tir": repo_native(seed_tir_path),
            "captured_task_log": repo_native(task_log_path),
        },
        "notes": [
            "The pre-compile seed snapshot captured the Relax callsite under `main`.",
            "The editable TIR in this directory is extracted from the local MetaSchedule task log for the selected operator workload.",
            "This package is repo-native and checked in, but not wired into rebuild hooks automatically.",
        ],
    }


def render_editable_tir(
    *,
    seed_json_path: Path,
    seed_tir_path: Path,
    task_log_path: Path,
    extracted_tir: str,
) -> str:
    normalized_tir = extracted_tir.replace(
        "# from tvm.script import ir as I\n# from tvm.script import tir as T\n",
        "from tvm.script import ir as I\nfrom tvm.script import tir as T\n",
        1,
    )
    header = [
        f"# Checked-in editable seed for {OPERATOR_NAME}.",
        "#",
        "# Source inputs:",
        f"# - captured seed json: {repo_native(seed_json_path)}",
        f"# - captured pre-compile seed snapshot: {repo_native(seed_tir_path)}",
        f"# - extracted operator task log: {repo_native(task_log_path)}",
        "#",
        "# Notes:",
        "# - the captured pre-compile seed snapshot only recorded the full Relax callsite",
        "# - this file preserves the actual operator TIR printed by the local MetaSchedule task log",
        "# - edit here when shaping the first handwritten candidate",
        "",
    ]
    return "\n".join(header) + normalized_tir


def render_readme(
    *,
    seed_json_path: Path,
    seed_tir_path: Path,
    task_log_path: Path,
    output_dir: Path,
) -> str:
    editable_tir_path = repo_native(output_dir / EDITABLE_TIR_FILENAME)
    return "\n".join(
        [
            f"# Checked-in seed: `{OPERATOR_NAME}`",
            "",
            "This directory is the first repo-native handoff after the local-only",
            "manual seed capture. It keeps the operator-specific editing surface in",
            "the repo without touching trusted current or launching any remote work.",
            "",
            "## Files",
            "",
            f"- `{EDITABLE_TIR_FILENAME}`: editable operator TIR extracted from the local MetaSchedule task log.",
            f"- `{MANIFEST_FILENAME}`: trimmed seed context copied from the captured seed JSON.",
            f"- `{README_FILENAME}`: short editing runbook.",
            "",
            "## Why this exists",
            "",
            f"- the captured pre-compile seed JSON at `{repo_native(seed_json_path)}` is real, but its paired seed snapshot only shows the Relax callsite under `main`",
            f"- the local task log at `{repo_native(task_log_path)}` contains the actual `fused_conv2d_transpose1_add9` TIR workload",
            "- this package checks that workload into the repo so the first manual edits are not trapped under `tmp/`",
            "",
            "## Refresh from the latest local capture",
            "",
            "```bash",
            "python3 ./session_bootstrap/scripts/refresh_fused_conv2d_transpose1_add9_checked_in_seed.py",
            "```",
            "",
            "The helper reads:",
            f"- `{repo_native(seed_json_path)}`",
            f"- `{repo_native(seed_tir_path)}`",
            f"- `{repo_native(task_log_path)}`",
            "",
            "It refuses to overwrite this directory unless `--allow-overwrite` is passed.",
            "",
            "## Edit toward candidate v0",
            "",
            f"1. Start from `{editable_tir_path}`.",
            "2. Keep the buffer contract stable:",
            "   input `(1, 48, 64, 64)`, weight `(48, 24, 3, 3)`, bias `(1, 24, 1, 1)`, output `(1, 24, 128, 128)`.",
            "3. Treat `data_dilate`, `data_pad`, `kernel_transform`, `compute`, and `T_add` as the honest baseline stages from the captured workload.",
            "4. First manual edits should stay narrow: reduce intermediate traffic, fuse cheap transforms when possible, and only then try tiling/vectorization around `compute`.",
            "5. Do not point remote validation at this directory until a local-only rebuild path explicitly consumes it.",
            "",
            "## Source reminder",
            "",
            f"The original captured pre-compile snapshot is still at `{repo_native(seed_tir_path)}` if you need the full Relax callsite context.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.seed_json = require_file(as_abs(args.seed_json), "captured seed json")
    args.seed_tir = require_file(as_abs(args.seed_tir), "captured seed tir")
    args.task_log = require_file(as_abs(args.task_log), "captured task log")
    args.output_dir = as_abs(args.output_dir)

    editable_tir_path = args.output_dir / EDITABLE_TIR_FILENAME
    manifest_path = args.output_dir / MANIFEST_FILENAME
    readme_path = args.output_dir / README_FILENAME
    ensure_clean_outputs(
        [editable_tir_path, manifest_path, readme_path], args.allow_overwrite
    )

    seed_payload = load_seed_json(args.seed_json)
    extracted_tir = extract_initial_tir(args.task_log)
    manifest = build_manifest(
        seed_payload=seed_payload,
        seed_json_path=args.seed_json,
        seed_tir_path=args.seed_tir,
        task_log_path=args.task_log,
        output_dir=args.output_dir,
    )

    write_text(
        editable_tir_path,
        render_editable_tir(
            seed_json_path=args.seed_json,
            seed_tir_path=args.seed_tir,
            task_log_path=args.task_log,
            extracted_tir=extracted_tir,
        ),
    )
    write_text(
        manifest_path,
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    )
    write_text(
        readme_path,
        render_readme(
            seed_json_path=args.seed_json,
            seed_tir_path=args.seed_tir,
            task_log_path=args.task_log,
            output_dir=args.output_dir,
        ),
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "output_dir": str(args.output_dir),
                "editable_tir_path": str(editable_tir_path),
                "manifest_path": str(manifest_path),
                "readme_path": str(readme_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
