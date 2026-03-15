from __future__ import annotations

from pathlib import Path
import sys
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from board_access import build_board_access_config, build_demo_default_board_access  # noqa: E402


class DemoBoardAccessDefaultsTest(unittest.TestCase):
    def test_demo_defaults_prefill_real_repo_files_without_password(self) -> None:
        access = build_demo_default_board_access(None)

        self.assertEqual(access.host, "100.121.87.73")
        self.assertEqual(access.user, "user")
        self.assertEqual(access.port, "22")
        self.assertEqual(
            access.preloaded_ssh_env_file,
            DEMO_ROOT.parents[2] / "session_bootstrap/config/phytium_pi_login.example.env",
        )
        self.assertEqual(
            access.preloaded_inference_env_file,
            DEMO_ROOT.parents[2] / "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
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
