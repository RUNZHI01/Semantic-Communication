#!/usr/bin/env python3
"""Local correctness compare for transpose1 scheduled reference vs working copy."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import tvm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_NAME = "fused_conv2d_transpose1_add9"
DEFAULT_REFERENCE_TIR = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "handwritten"
    / OPERATOR_NAME
    / f"{OPERATOR_NAME}_post_db_scheduled_reference_seed_tir.py"
)
DEFAULT_CANDIDATE_TIR = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "handwritten"
    / OPERATOR_NAME
    / f"{OPERATOR_NAME}_scheduled_form_candidate_v1_working_copy_tir.py"
)

INPUT_SHAPES = {
    "lv318": (1, 48, 64, 64),
    "param_0": (48, 24, 3, 3),
    "lv320": (1, 24, 1, 1),
    "output": (1, 24, 128, 128),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the transpose1 scheduled reference seed and the current working "
            "copy locally, then compare outputs on a fixed random seed."
        )
    )
    parser.add_argument(
        "--reference-tir",
        type=Path,
        default=DEFAULT_REFERENCE_TIR,
        help="Checked-in frozen scheduled reference seed TIR.",
    )
    parser.add_argument(
        "--candidate-tir",
        type=Path,
        default=DEFAULT_CANDIDATE_TIR,
        help="Checked-in scheduled-form working copy TIR to compare.",
    )
    parser.add_argument(
        "--target",
        default="llvm",
        help="Local build target for the correctness compare. Default: llvm.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260331,
        help="Frozen RNG seed for generated inputs.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional JSON output path.",
    )
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise SystemExit(f"ERROR: {label} not found: {resolved}")
    return resolved


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_native(path: Path) -> str:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return str(path)
    return f"./{relative.as_posix()}"


def load_python_module(module_path: Path):
    module_name = f"transpose1_correctness_{module_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"ERROR: unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def load_ir_module(module_path: Path):
    loaded = load_python_module(module_path)
    ir_module = getattr(loaded, "Module", None)
    if ir_module is None:
        raise SystemExit(f"ERROR: no `Module` IRModule found in {module_path}")
    return ir_module


def build_runtime(ir_module: Any, target: str):
    return tvm.build(ir_module, target=target)


def get_packed_func(runtime_module: tvm.runtime.Module):
    func = runtime_module.get_function(OPERATOR_NAME)
    if func is None:
        raise SystemExit(
            f"ERROR: runtime module does not expose packed func {OPERATOR_NAME!r}"
        )
    return func


def make_inputs(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        "lv318": rng.uniform(-1.0, 1.0, size=INPUT_SHAPES["lv318"]).astype("float32"),
        "param_0": rng.uniform(-1.0, 1.0, size=INPUT_SHAPES["param_0"]).astype("float32"),
        "lv320": rng.uniform(-1.0, 1.0, size=INPUT_SHAPES["lv320"]).astype("float32"),
    }


def run_module(runtime_module: tvm.runtime.Module, inputs: dict[str, np.ndarray]) -> np.ndarray:
    func = get_packed_func(runtime_module)
    device = tvm.cpu(0)
    lv318 = tvm.runtime.tensor(inputs["lv318"], device=device)
    param_0 = tvm.runtime.tensor(inputs["param_0"], device=device)
    lv320 = tvm.runtime.tensor(inputs["lv320"], device=device)
    output = tvm.runtime.empty(INPUT_SHAPES["output"], "float32", device=device)
    func(lv318, param_0, lv320, output)
    return output.numpy()


def build_report(
    *,
    reference_tir: Path,
    candidate_tir: Path,
    target: str,
    seed: int,
    reference_output: np.ndarray,
    candidate_output: np.ndarray,
) -> dict[str, Any]:
    diff = candidate_output - reference_output
    abs_diff = np.abs(diff)
    exact_equal = bool(np.array_equal(reference_output, candidate_output))
    max_abs_diff = float(abs_diff.max(initial=0.0))
    nonzero_diff_count = int(np.count_nonzero(abs_diff))

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "operator": OPERATOR_NAME,
        "reference_tir": repo_native(reference_tir),
        "reference_tir_sha256": file_sha256(reference_tir),
        "candidate_tir": repo_native(candidate_tir),
        "candidate_tir_sha256": file_sha256(candidate_tir),
        "target": target,
        "seed": seed,
        "input_shapes": {name: list(shape) for name, shape in INPUT_SHAPES.items()},
        "exact_equal": exact_equal,
        "allclose_atol0_rtol0": bool(
            np.allclose(reference_output, candidate_output, atol=0.0, rtol=0.0)
        ),
        "allclose_atol1e-6_rtol1e-6": bool(
            np.allclose(reference_output, candidate_output, atol=1e-6, rtol=1e-6)
        ),
        "allclose_atol1e-5_rtol1e-5": bool(
            np.allclose(reference_output, candidate_output, atol=1e-5, rtol=1e-5)
        ),
        "max_abs_diff": max_abs_diff,
        "mean_abs_diff": float(abs_diff.mean()),
        "nonzero_diff_count": nonzero_diff_count,
        "reference_output_checksum": sha256(reference_output.tobytes()).hexdigest(),
        "candidate_output_checksum": sha256(candidate_output.tobytes()).hexdigest(),
    }


def maybe_write_json(payload: dict[str, Any], output_json: Path | None) -> None:
    if output_json is None:
        return
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reference_tir = require_file(args.reference_tir, "reference tir")
    candidate_tir = require_file(args.candidate_tir, "candidate tir")

    reference_module = load_ir_module(reference_tir)
    candidate_module = load_ir_module(candidate_tir)

    inputs = make_inputs(args.seed)
    reference_runtime = build_runtime(reference_module, args.target)
    candidate_runtime = build_runtime(candidate_module, args.target)
    reference_output = run_module(reference_runtime, inputs)
    candidate_output = run_module(candidate_runtime, inputs)

    report = build_report(
        reference_tir=reference_tir,
        candidate_tir=candidate_tir,
        target=args.target,
        seed=args.seed,
        reference_output=reference_output,
        candidate_output=candidate_output,
    )
    maybe_write_json(report, args.output_json)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
