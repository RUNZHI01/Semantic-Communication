from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from board_access import (  # noqa: E402
    DEFAULT_INFERENCE_ENV_CANDIDATES,
    build_board_access_config,
    build_demo_default_board_access,
    discover_trusted_baseline_expected_sha,
    discover_validated_inference_env,
    discover_validated_openamp_remote_project_root,
    first_existing_env,
)


class DemoBoardAccessDefaultsTest(unittest.TestCase):
    def test_discover_validated_inference_env_uses_report_linked_env_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            env_path = temp_root / "trusted.env"
            report_path = temp_root / "trusted.md"
            env_path.write_text("REMOTE_HOST=demo-board\n", encoding="utf-8")
            report_path.write_text(f"- env_file: {env_path}\n", encoding="utf-8")

            discovered = discover_validated_inference_env((str(report_path),))

        self.assertEqual(discovered, env_path.resolve())

    def test_discover_validated_openamp_remote_project_root_uses_run_manifest_board_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / "run_manifest.json"
            manifest_path.write_text(
                json.dumps({"board_access": {"remote_project_root": "/tmp/openamp_demo/project"}}),
                encoding="utf-8",
            )

            discovered = discover_validated_openamp_remote_project_root((str(manifest_path),))

        self.assertEqual(discovered, "/tmp/openamp_demo/project")

    def test_discover_trusted_baseline_expected_sha_requires_matching_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            matching_report = temp_root / "matching.md"
            mismatched_report = temp_root / "mismatched.md"
            matching_report.write_text(
                "\n".join(
                    [
                        "- baseline_expected_sha256_configured: 85d701db0021c26412c3e5e08a4ca043470aaa01fb2d6792cb3b3b29e93bf849",
                        "- baseline_artifact_path: /remote/baseline/tvm_tune_logs/optimized_model.so",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            mismatched_report.write_text(
                "\n".join(
                    [
                        "- baseline_expected_sha256_configured: 9478c8277b013ccbcae9dabaf72dd123efc7908405a359b951d7c85f780b8df8",
                        "- baseline_artifact_path: /remote/other/tvm_tune_logs/optimized_model.so",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            discovered = discover_trusted_baseline_expected_sha(
                {"REMOTE_BASELINE_ARTIFACT": "/remote/baseline/tvm_tune_logs/optimized_model.so"},
                (str(mismatched_report), str(matching_report)),
            )

        self.assertEqual(discovered, "85d701db0021c26412c3e5e08a4ca043470aaa01fb2d6792cb3b3b29e93bf849")

    def test_demo_defaults_prefill_real_repo_files_without_password(self) -> None:
        access = build_demo_default_board_access(None)
        expected_inference_env = discover_validated_inference_env() or first_existing_env(DEFAULT_INFERENCE_ENV_CANDIDATES)
        expected_remote_project_root = discover_validated_openamp_remote_project_root()

        self.assertEqual(access.host, "100.121.87.73")
        self.assertEqual(access.user, "user")
        self.assertEqual(access.port, "22")
        self.assertEqual(
            access.preloaded_ssh_env_file,
            DEMO_ROOT.parents[2] / "session_bootstrap/config/phytium_pi_login.example.env",
        )
        self.assertEqual(
            access.preloaded_inference_env_file,
            expected_inference_env,
        )
        self.assertFalse(access.password)
        self.assertEqual(access.missing_connection_fields(), ["password"])
        self.assertEqual(access.missing_inference_fields("current"), ["password"])
        self.assertEqual(access.missing_inference_fields("baseline"), ["password"])
        self.assertNotIn("REMOTE_PASS", access.env_values)
        self.assertNotIn("PHYTIUM_PI_PASSWORD", access.env_values)
        self.assertEqual(access.build_env().get("REMOTE_PROJECT_ROOT", ""), expected_remote_project_root)
        self.assertEqual(
            access.build_env().get("INFERENCE_BASELINE_EXPECTED_SHA256", ""),
            "85d701db0021c26412c3e5e08a4ca043470aaa01fb2d6792cb3b3b29e93bf849",
        )

    def test_password_only_update_reuses_preloaded_ssh_and_inference_defaults(self) -> None:
        defaults = build_demo_default_board_access(None)

        access = build_board_access_config({"password": "demo-pass"}, fallback=defaults)

        self.assertEqual(access.host, defaults.host)
        self.assertEqual(access.user, defaults.user)
        self.assertEqual(access.port, defaults.port)
        self.assertEqual(access.env_file, defaults.env_file)
        self.assertEqual(access.password, "demo-pass")
        self.assertTrue(access.connection_ready)
        self.assertEqual(access.missing_inference_fields("current"), [])
        self.assertEqual(access.missing_inference_fields("baseline"), [])
        self.assertEqual(access.build_env()["REMOTE_PASS"], "demo-pass")
        self.assertEqual(
            access.build_env().get("REMOTE_PROJECT_ROOT", ""),
            defaults.build_env().get("REMOTE_PROJECT_ROOT", ""),
        )
        self.assertEqual(access.field_sources["password"], "session")


if __name__ == "__main__":
    unittest.main()
