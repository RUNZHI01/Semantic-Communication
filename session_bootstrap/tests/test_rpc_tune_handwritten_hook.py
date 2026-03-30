from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "session_bootstrap"
    / "scripts"
    / "rpc_tune.py"
)
SCRIPT_DIR = SCRIPT.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

spec = importlib.util.spec_from_file_location("rpc_tune", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load module from {SCRIPT}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_task_stages(operator_name: str) -> dict[str, object]:
    row = {
        "rank": 1,
        "task_name": operator_name,
        "weight": 1,
        "dispatched_count": 1,
        "prim_funcs": [operator_name],
        "target": "llvm",
    }
    return {
        module.RAW_STAGE_NAME: {
            "stage_name": module.RAW_STAGE_NAME,
            "pipeline": None,
            "total_tasks": 1,
            "tasks": [row],
        },
        module.TUNED_STAGE_NAME: {
            "stage_name": module.TUNED_STAGE_NAME,
            "pipeline": "FuseTIR",
            "total_tasks": 1,
            "tasks": [row],
        },
    }


class RpcTuneHandwrittenHookTest(unittest.TestCase):
    def test_disabled_when_impl_path_is_unset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            with mock.patch.dict(os.environ, {}, clear=True):
                report = module.maybe_apply_handwritten_hook(
                    mod="fake-mod",
                    target="llvm",
                    database="fake-db",
                    output_dir=str(temp_dir),
                    task_stages=make_task_stages("fused_conv2d_transpose1_add9"),
                )

        self.assertIsNone(report)

    def test_placeholder_module_is_traced_and_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            impl_path = temp_dir / "manual_impl.py"
            state_json = temp_dir / "state.json"
            bookkeeping_json = temp_dir / "bookkeeping.json"
            write_text(bookkeeping_json, "{}\n")
            write_text(
                impl_path,
                textwrap.dedent(
                    f"""\
                    import json
                    from pathlib import Path

                    STATE_JSON = Path({str(state_json)!r})


                    def describe_placeholder(context):
                        STATE_JSON.write_text(
                            json.dumps(
                                {{
                                    "metadata_phase": context["phase"],
                                    "metadata_operator": context["operator"],
                                }}
                            ),
                            encoding="utf-8",
                        )
                        return {{
                            "operator": "fused_conv2d_transpose1_add9",
                            "placeholder_only": True,
                            "tag": "placeholder",
                        }}


                    def build_manual_impl(context):
                        payload = json.loads(STATE_JSON.read_text(encoding="utf-8"))
                        payload["entrypoint_phase"] = context["phase"]
                        STATE_JSON.write_text(json.dumps(payload), encoding="utf-8")
                        raise NotImplementedError("placeholder only")
                    """
                ),
            )

            env = {
                "TVM_HANDWRITTEN_IMPL_PATH": str(impl_path),
                "TVM_HANDWRITTEN_OP": "fused_conv2d_transpose1_add9",
                "TVM_HANDWRITTEN_IMPL_ENTRYPOINT": "build_manual_impl",
                "TVM_HANDWRITTEN_IMPL_METADATA_FN": "describe_placeholder",
                "TVM_HANDWRITTEN_BOOKKEEPING_JSON": str(bookkeeping_json),
            }
            with mock.patch.dict(os.environ, env, clear=True):
                report = module.maybe_apply_handwritten_hook(
                    mod="fake-mod",
                    target="llvm",
                    database="fake-db",
                    output_dir=str(temp_dir),
                    task_stages=make_task_stages("fused_conv2d_transpose1_add9"),
                )

            state = json.loads(state_json.read_text(encoding="utf-8"))

        self.assertIsNotNone(report)
        self.assertEqual(report["status"], "placeholder_only")
        self.assertTrue(report["placeholder_only"])
        self.assertEqual(report["metadata"]["tag"], "placeholder")
        self.assertEqual(report["metadata_operator"], "fused_conv2d_transpose1_add9")
        self.assertEqual(report["bookkeeping_json"], str(bookkeeping_json))
        self.assertEqual(
            report["task_stage_matches"][module.TUNED_STAGE_NAME],
            True,
        )
        self.assertEqual(report["entrypoint_notice"], "placeholder only")
        self.assertEqual(state["metadata_phase"], "pre_compile")
        self.assertEqual(state["metadata_operator"], "fused_conv2d_transpose1_add9")
        self.assertEqual(state["entrypoint_phase"], "pre_compile")

    def test_metadata_operator_mismatch_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            impl_path = temp_dir / "manual_impl.py"
            write_text(
                impl_path,
                textwrap.dedent(
                    """\
                    def describe_placeholder():
                        return {
                            "operator": "wrong_operator",
                            "placeholder_only": True,
                        }


                    def build_manual_impl():
                        return None
                    """
                ),
            )

            env = {
                "TVM_HANDWRITTEN_IMPL_PATH": str(impl_path),
                "TVM_HANDWRITTEN_OP": "fused_conv2d_transpose1_add9",
                "TVM_HANDWRITTEN_IMPL_ENTRYPOINT": "build_manual_impl",
                "TVM_HANDWRITTEN_IMPL_METADATA_FN": "describe_placeholder",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(
                    ValueError,
                    "Handwritten metadata operator mismatch",
                ):
                    module.maybe_apply_handwritten_hook(
                        mod="fake-mod",
                        target="llvm",
                        database="fake-db",
                        output_dir=str(temp_dir),
                        task_stages=make_task_stages("fused_conv2d_transpose1_add9"),
                    )

    def test_operator_must_exist_in_task_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            impl_path = temp_dir / "manual_impl.py"
            write_text(
                impl_path,
                textwrap.dedent(
                    """\
                    def describe_placeholder():
                        return {
                            "operator": "fused_conv2d_transpose1_add9",
                            "placeholder_only": True,
                        }


                    def build_manual_impl():
                        return None
                    """
                ),
            )

            env = {
                "TVM_HANDWRITTEN_IMPL_PATH": str(impl_path),
                "TVM_HANDWRITTEN_OP": "fused_conv2d_transpose1_add9",
                "TVM_HANDWRITTEN_IMPL_ENTRYPOINT": "build_manual_impl",
                "TVM_HANDWRITTEN_IMPL_METADATA_FN": "describe_placeholder",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(
                    ValueError,
                    "is not present in the extracted task stages",
                ):
                    module.maybe_apply_handwritten_hook(
                        mod="fake-mod",
                        target="llvm",
                        database="fake-db",
                        output_dir=str(temp_dir),
                        task_stages=make_task_stages("different_operator"),
                    )

    def test_report_writers_include_handwritten_hook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            args = SimpleNamespace(
                onnx_path="/tmp/model.onnx",
                target="llvm",
                input_shape="1,32,32,32",
                op_names="fused_conv2d_transpose1_add9",
                total_trials=0,
                runner="local",
                tracker_host="127.0.0.1",
                tracker_port=9190,
                device_key="armv8",
                existing_db="",
            )
            task_stages = make_task_stages("fused_conv2d_transpose1_add9")
            handwritten_hook = {
                "enabled": True,
                "status": "placeholder_only",
                "operator": "fused_conv2d_transpose1_add9",
            }

            task_summary_path = module.write_task_summary(
                str(temp_dir),
                task_stages,
                args,
                handwritten_hook=handwritten_hook,
            )
            report_path = module.write_tune_report(
                str(temp_dir),
                args,
                elapsed_sec=0.5,
                lib_path=str(temp_dir / "optimized_model.so"),
                work_dir=str(temp_dir / "tuning_logs"),
                task_summary_path=task_summary_path,
                task_stages=task_stages,
                handwritten_hook=handwritten_hook,
            )

            task_summary = json.loads(Path(task_summary_path).read_text(encoding="utf-8"))
            report = json.loads(Path(report_path).read_text(encoding="utf-8"))

        self.assertEqual(task_summary["handwritten_hook"], handwritten_hook)
        self.assertEqual(report["handwritten_hook"], handwritten_hook)


if __name__ == "__main__":
    unittest.main()
