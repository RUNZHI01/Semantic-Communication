from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "session_bootstrap"
    / "handwritten"
    / "fused_conv2d_transpose1_add9"
    / "fused_conv2d_transpose1_add9_manual_candidate.py"
)

spec = importlib.util.spec_from_file_location(
    "fused_conv2d_transpose1_add9_manual_candidate",
    MODULE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load module from {MODULE_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FusedConv2dTranspose1Add9ManualCandidateTest(unittest.TestCase):
    def test_candidate_reports_checked_in_hook_path_honestly(self) -> None:
        metadata = module.describe_placeholder()
        self.assertEqual(metadata["operator"], "fused_conv2d_transpose1_add9")
        self.assertFalse(metadata["placeholder_only"])
        self.assertFalse(metadata["manual_override_applied"])
        self.assertEqual(metadata["validation_scope"], "checked_in_candidate_only")
        self.assertTrue(Path(metadata["candidate_tir"]).is_file())
        self.assertTrue(Path(metadata["seed_manifest"]).is_file())

        result = module.build_manual_impl(
            {
                "phase": "pre_compile",
                "task_stages": {
                    "legalized_fused_tir": {
                        "tasks": [
                            {
                                "rank": 16,
                                "task_name": "fused_conv2d_transpose1_add9",
                            }
                        ]
                    }
                },
            }
        )
        self.assertFalse(result["manual_override_applied"])
        self.assertEqual(result["phase"], "pre_compile")
        self.assertEqual(result["validation_scope"], "checked_in_candidate_only")
        self.assertEqual(result["task_row"]["stage_name"], "legalized_fused_tir")


if __name__ == "__main__":
    unittest.main()
