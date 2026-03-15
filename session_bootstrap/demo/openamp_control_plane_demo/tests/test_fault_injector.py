from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from board_access import BoardAccessConfig  # noqa: E402
from fault_injector import run_fault_action  # noqa: E402


def make_access() -> BoardAccessConfig:
    return BoardAccessConfig(
        host="demo-board",
        user="demo-user",
        password="demo-pass",
        port="22",
        env_file=None,
        env_values={},
        source_summary="unit test",
    )


class RunFaultActionTest(unittest.TestCase):
    def test_auth_failure_maps_to_operator_message_with_diagnostics(self) -> None:
        access = make_access()
        completed = subprocess.CompletedProcess(
            ["bash", "fake-ssh"],
            255,
            stdout="",
            stderr="Permission denied (publickey,password).\n",
        )

        with patch("fault_injector.subprocess.run", return_value=completed):
            payload = run_fault_action(access, fault_type="wrong_sha", trusted_sha="a" * 64, timeout_sec=8.0)

        self.assertEqual(payload["status"], "parse_error")
        self.assertEqual(payload["status_category"], "auth_error")
        self.assertIn("认证失败", payload["message"])
        self.assertNotIn("Permission denied", payload["message"])
        self.assertEqual(
            payload["diagnostics"],
            {
                "stderr": "Permission denied (publickey,password).",
                "error": "remote fault action produced no JSON payload",
                "returncode": 255,
            },
        )


if __name__ == "__main__":
    unittest.main()
