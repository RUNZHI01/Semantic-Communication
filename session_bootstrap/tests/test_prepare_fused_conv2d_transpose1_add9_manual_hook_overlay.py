from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "session_bootstrap"
    / "scripts"
    / "prepare_fused_conv2d_transpose1_add9_manual_hook_overlay.py"
)

spec = importlib.util.spec_from_file_location(
    "prepare_fused_conv2d_transpose1_add9_manual_hook_overlay",
    SCRIPT,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load module from {SCRIPT}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PrepareFusedConv2dTranspose1Add9ManualHookOverlayTest(unittest.TestCase):
    def test_generates_placeholder_manual_impl_and_overlay_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            scaffold_dir = temp_dir / "scaffold"
            rebuild_env = scaffold_dir / "manual_rebuild.env"
            bookkeeping_json = scaffold_dir / "bookkeeping.json"

            write_text(rebuild_env, "TUNE_TOTAL_TRIALS=0\n")
            write_text(
                bookkeeping_json,
                json.dumps(
                    {
                        "operator": "fused_conv2d_transpose1_add9",
                        "current_best_staging": {
                            "artifact_sha256": (
                                "5bd14b9f97d1d06f04a484cd8b1b3f57"
                                "a955d65711ed65a22f9925dcec44698d"
                            )
                        },
                        "current_profile_json": "/tmp/current_profile.json",
                        "remote_archive_dir": "/tmp/handwritten_archive",
                        "operator_context": {
                            "current_argument_shapes": (
                                "float32[1, 48, 64, 64], "
                                "float32[48, 24, 3, 3], "
                                "float32[1, 24, 1, 1], "
                                "float32[1, 24, 128, 128]"
                            )
                        },
                    },
                    indent=2,
                )
                + "\n",
            )

            rc = module.main(["--scaffold-dir", str(scaffold_dir)])
            self.assertEqual(rc, 0)

            manual_impl_path = scaffold_dir / "fused_conv2d_transpose1_add9_manual_impl.py"
            overlay_env_path = scaffold_dir / "manual_hook_overlay.env"

            overlay_env = overlay_env_path.read_text(encoding="utf-8")
            self.assertIn(f"source {str(rebuild_env)}", overlay_env)
            self.assertIn("TVM_HANDWRITTEN_OP=fused_conv2d_transpose1_add9", overlay_env)
            self.assertIn(
                f"TVM_HANDWRITTEN_IMPL_PATH={manual_impl_path}",
                overlay_env,
            )
            self.assertIn("TVM_HANDWRITTEN_IMPL_ENTRYPOINT=build_manual_impl", overlay_env)
            self.assertIn("TVM_HANDWRITTEN_IMPL_METADATA_FN=describe_placeholder", overlay_env)
            self.assertIn(
                f"TVM_HANDWRITTEN_BOOKKEEPING_JSON={bookkeeping_json}",
                overlay_env,
            )

            impl_spec = importlib.util.spec_from_file_location("manual_impl_placeholder", manual_impl_path)
            if impl_spec is None or impl_spec.loader is None:
                raise RuntimeError(f"unable to load generated module from {manual_impl_path}")
            impl_module = importlib.util.module_from_spec(impl_spec)
            impl_spec.loader.exec_module(impl_module)

            payload = impl_module.describe_placeholder()
            self.assertEqual(payload["operator"], "fused_conv2d_transpose1_add9")
            self.assertEqual(
                payload["reference_staging_sha256"],
                "5bd14b9f97d1d06f04a484cd8b1b3f57a955d65711ed65a22f9925dcec44698d",
            )
            self.assertEqual(payload["bookkeeping_json"], str(bookkeeping_json))
            self.assertTrue(payload["placeholder_only"])
            with self.assertRaises(NotImplementedError):
                impl_module.build_manual_impl()


if __name__ == "__main__":
    unittest.main()
