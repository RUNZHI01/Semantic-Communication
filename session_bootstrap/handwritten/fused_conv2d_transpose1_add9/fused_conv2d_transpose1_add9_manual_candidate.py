"""Checked-in hook-facing candidate for fused_conv2d_transpose1_add9.

Edit the sibling editable TIR file when shaping the first real manual candidate.
This module stays intentionally narrow:
- it is a repo-native TVM_HANDWRITTEN_IMPL_PATH target
- it reports the checked-in candidate through the existing rpc_tune.py hook
- it does not claim a compile-time override yet
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OPERATOR_NAME = "fused_conv2d_transpose1_add9"
EDITABLE_TIR_FILENAME = f"{OPERATOR_NAME}_editable_seed_tir.py"
MANIFEST_FILENAME = "seed_manifest.json"


def _module_dir() -> Path:
    return Path(__file__).resolve().parent


def _editable_tir_path() -> Path:
    return _module_dir() / EDITABLE_TIR_FILENAME


def _manifest_path() -> Path:
    return _module_dir() / MANIFEST_FILENAME


def _load_manifest() -> dict[str, Any]:
    manifest_path = _manifest_path()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"seed manifest not found: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    operator = payload.get("operator")
    if operator != OPERATOR_NAME:
        raise ValueError(
            f"expected manifest operator {OPERATOR_NAME!r}, got {operator!r}"
        )
    return payload


def _select_task_row(task_stages: Any) -> dict[str, Any] | None:
    if not isinstance(task_stages, dict):
        return None

    preferred = None
    fallback = None
    for stage_name, payload in task_stages.items():
        tasks = payload.get("tasks") or []
        for row in tasks:
            if row.get("task_name") != OPERATOR_NAME:
                continue
            candidate = dict(row)
            candidate["stage_name"] = stage_name
            if stage_name == "legalized_fused_tir":
                preferred = candidate
                break
            if fallback is None:
                fallback = candidate
        if preferred is not None:
            break
    return preferred or fallback


def describe_placeholder(context: dict[str, Any] | None = None) -> dict[str, object]:
    del context
    manifest = _load_manifest()
    return {
        "operator": OPERATOR_NAME,
        "reference_staging_sha256": manifest.get("reference_staging_sha256"),
        "reference_profile_json": manifest.get("reference_profile_json"),
        "argument_shapes": manifest.get("argument_shapes"),
        "seed_capture_kind": manifest.get("seed_capture_kind"),
        "candidate_tir": str(_editable_tir_path()),
        "seed_manifest": str(_manifest_path()),
        "placeholder_only": False,
        "manual_override_applied": False,
        "validation_scope": "checked_in_candidate_only",
        "next_step": (
            "Edit the checked-in editable_seed_tir.py file, then keep using this "
            "module as the handwritten-hook entrypoint until a later compile-time "
            "override step is ready."
        ),
    }


def build_manual_impl(context: dict[str, Any] | None = None) -> dict[str, object]:
    manifest = _load_manifest()
    editable_tir_path = _editable_tir_path()
    if not editable_tir_path.is_file():
        raise FileNotFoundError(f"editable seed TIR not found: {editable_tir_path}")

    return {
        "manual_override_applied": False,
        "operator": OPERATOR_NAME,
        "phase": None if context is None else context.get("phase"),
        "task_row": None
        if context is None
        else _select_task_row(context.get("task_stages")),
        "reference_staging_sha256": manifest.get("reference_staging_sha256"),
        "candidate_tir": str(editable_tir_path),
        "seed_manifest": str(_manifest_path()),
        "validation_scope": "checked_in_candidate_only",
        "notes": [
            "The checked-in candidate path is active.",
            "Compile output is unchanged until a later override step consumes the edited TIR.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(describe_placeholder(), indent=2, ensure_ascii=False))
