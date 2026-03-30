#!/usr/bin/env python3
"""Prepare a first manual hook overlay for fused_conv2d_transpose1_add9.

This helper stays narrow on purpose:
- reuse the existing handwritten scaffold directory as the source of truth
- materialize one editable placeholder manual implementation file
- generate one rebuild overlay env that points at that file
- avoid touching trusted current or any stock rebuild wrapper
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_NAME = "fused_conv2d_transpose1_add9"
DEFAULT_SCAFFOLD_DIR = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "tmp"
    / "handwritten_fused_conv2d_transpose1_add9_scaffold"
)
DEFAULT_TEMPLATE_PATH = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "templates"
    / "handwritten"
    / "fused_conv2d_transpose1_add9_manual_impl.py.tmpl"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a placeholder manual implementation file plus rebuild overlay "
            f"for the handwritten {OPERATOR_NAME} scaffold."
        )
    )
    parser.add_argument(
        "--scaffold-dir",
        type=Path,
        default=DEFAULT_SCAFFOLD_DIR,
        help="Existing scaffold directory produced by prepare_fused_conv2d_transpose1_add9_handwritten_scaffold.py.",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=DEFAULT_TEMPLATE_PATH,
        help="Checked-in placeholder template used to create the editable manual implementation file.",
    )
    parser.add_argument(
        "--manual-impl-path",
        type=Path,
        help="Output path for the editable placeholder manual implementation file.",
    )
    parser.add_argument(
        "--output-env",
        type=Path,
        help="Output path for the rebuild overlay env that points at the placeholder file.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwriting an existing manual implementation file or overlay env.",
    )
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(f"ERROR: {label} not found: {path}")
    return path


def require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
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


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def ensure_clean_outputs(paths: list[Path], allow_overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not allow_overwrite:
        joined = "\n  ".join(str(path) for path in existing)
        raise SystemExit(
            "ERROR: output already exists. Re-run with --allow-overwrite or choose a "
            f"new location.\n  {joined}"
        )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_bookkeeping(bookkeeping_json: Path) -> dict[str, Any]:
    payload = json.loads(bookkeeping_json.read_text(encoding="utf-8"))
    operator = payload.get("operator")
    if operator != OPERATOR_NAME:
        raise SystemExit(
            f"ERROR: expected bookkeeping operator {OPERATOR_NAME!r}, got {operator!r}"
        )
    return payload


def render_manual_impl(
    *,
    template_path: Path,
    bookkeeping: dict[str, Any],
    bookkeeping_json: Path,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    operator_context = bookkeeping.get("operator_context") or {}
    current_best_staging = bookkeeping.get("current_best_staging") or {}
    replacements = {
        "__OPERATOR_NAME__": bookkeeping.get("operator", OPERATOR_NAME),
        "__REFERENCE_STAGING_SHA256__": current_best_staging.get("artifact_sha256", ""),
        "__REFERENCE_PROFILE_JSON__": bookkeeping.get("current_profile_json", ""),
        "__ARGUMENT_SHAPES__": operator_context.get("current_argument_shapes", ""),
        "__BOOKKEEPING_JSON__": repo_native(bookkeeping_json),
        "__REMOTE_ARCHIVE_DIR__": bookkeeping.get("remote_archive_dir", ""),
    }
    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise SystemExit(f"ERROR: missing token in template: {token}")
        rendered = rendered.replace(token, json.dumps(value, ensure_ascii=False))
    return rendered


def build_overlay_env(
    *,
    rebuild_env: Path,
    manual_impl_path: Path,
    bookkeeping_json: Path,
) -> str:
    lines = [
        "# Auto-generated overlay for the first handwritten fused_conv2d_transpose1_add9 hook.",
        "# shellcheck source=/dev/null",
        f"source {shell_quote(str(rebuild_env.resolve()))}",
        "",
        "# These variables are the local build-side handoff; stock wrappers only source this env.",
        "# The first local patch should import TVM_HANDWRITTEN_IMPL_PATH and call",
        "# TVM_HANDWRITTEN_IMPL_ENTRYPOINT before compile when TVM_HANDWRITTEN_OP matches.",
        f"TVM_HANDWRITTEN_OP={OPERATOR_NAME}",
        f"TVM_HANDWRITTEN_IMPL_PATH={shell_quote(repo_native(manual_impl_path))}",
        "TVM_HANDWRITTEN_IMPL_ENTRYPOINT=build_manual_impl",
        "TVM_HANDWRITTEN_IMPL_METADATA_FN=describe_placeholder",
        f"TVM_HANDWRITTEN_BOOKKEEPING_JSON={shell_quote(repo_native(bookkeeping_json))}",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.scaffold_dir = require_dir(as_abs(args.scaffold_dir), "scaffold dir")
    args.template_path = require_file(as_abs(args.template_path), "manual implementation template")

    rebuild_env = require_file(args.scaffold_dir / "manual_rebuild.env", "scaffold rebuild env")
    bookkeeping_json = require_file(args.scaffold_dir / "bookkeeping.json", "scaffold bookkeeping")
    bookkeeping = load_bookkeeping(bookkeeping_json)

    args.manual_impl_path = as_abs(
        args.manual_impl_path
        if args.manual_impl_path is not None
        else args.scaffold_dir / f"{OPERATOR_NAME}_manual_impl.py"
    )
    args.output_env = as_abs(
        args.output_env if args.output_env is not None else args.scaffold_dir / "manual_hook_overlay.env"
    )
    ensure_clean_outputs([args.manual_impl_path, args.output_env], args.allow_overwrite)

    write_text(
        args.manual_impl_path,
        render_manual_impl(
            template_path=args.template_path,
            bookkeeping=bookkeeping,
            bookkeeping_json=bookkeeping_json,
        ),
    )
    write_text(
        args.output_env,
        build_overlay_env(
            rebuild_env=rebuild_env,
            manual_impl_path=args.manual_impl_path,
            bookkeeping_json=bookkeeping_json,
        ),
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "scaffold_dir": str(args.scaffold_dir),
                "manual_impl_path": str(args.manual_impl_path),
                "output_env": str(args.output_env),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
