from __future__ import annotations

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
    discover_validated_inference_env,
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

    def test_demo_defaults_prefill_real_repo_files_without_password(self) -> None:
        access = build_demo_default_board_access(None)
        expected_inference_env = discover_validated_inference_env() or first_existing_env(DEFAULT_INFERENCE_ENV_CANDIDATES)

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
        self.assertEqual(access.field_sources["password"], "session")


if __name__ == "__main__":
    unittest.main()
