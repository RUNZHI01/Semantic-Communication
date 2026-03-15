from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from board_probe import (  # noqa: E402
    CONNECT_SCRIPT,
    PROJECT_ROOT,
    REMOTE_PROBE_CODE,
    SSH_WITH_PASSWORD_SCRIPT,
    build_probe_command,
    load_probe_output,
    run_live_probe,
    write_probe_output,
)


EXPECTED_REMOTE_COMMAND = f"python3 -c {shlex.quote(REMOTE_PROBE_CODE)}"


class BuildProbeCommandTest(unittest.TestCase):
    def write_env(self, content: str, *, relative: bool = False) -> str:
        temp_dir = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.addCleanup(temp_dir.cleanup)
        env_path = Path(temp_dir.name) / "probe.env"
        env_path.write_text(content, encoding="utf-8")
        if relative:
            return str(env_path.relative_to(PROJECT_ROOT))
        return str(env_path)

    def test_password_env_uses_ssh_with_password_script_with_default_port(self) -> None:
        env_file = self.write_env(
            "\n".join(
                [
                    "REMOTE_HOST=demo-board",
                    "REMOTE_USER=demo-user",
                    "REMOTE_PASS=demo-pass",
                ]
            ),
            relative=True,
        )

        command = build_probe_command(env_file)

        self.assertEqual(
            command,
            [
                "bash",
                str(SSH_WITH_PASSWORD_SCRIPT),
                "--host",
                "demo-board",
                "--user",
                "demo-user",
                "--pass",
                "demo-pass",
                "--port",
                "22",
                "--",
                EXPECTED_REMOTE_COMMAND,
            ],
        )

    def test_password_env_honors_remote_ssh_port_override(self) -> None:
        env_file = self.write_env(
            "\n".join(
                [
                    "REMOTE_HOST=demo-board",
                    "REMOTE_USER=demo-user",
                    "REMOTE_PASS=demo-pass",
                    "REMOTE_SSH_PORT=2202",
                ]
            )
        )

        command = build_probe_command(env_file)

        self.assertEqual(
            command,
            [
                "bash",
                str(SSH_WITH_PASSWORD_SCRIPT),
                "--host",
                "demo-board",
                "--user",
                "demo-user",
                "--pass",
                "demo-pass",
                "--port",
                "2202",
                "--",
                EXPECTED_REMOTE_COMMAND,
            ],
        )

    def test_missing_password_auth_vars_falls_back_to_connect_script_with_env(self) -> None:
        env_file = self.write_env(
            "\n".join(
                [
                    "REMOTE_HOST=demo-board",
                    "REMOTE_USER=demo-user",
                ]
            ),
            relative=True,
        )

        command = build_probe_command(env_file)

        self.assertEqual(
            command,
            [
                "bash",
                str(CONNECT_SCRIPT),
                "--env",
                env_file,
                "--",
                EXPECTED_REMOTE_COMMAND,
            ],
        )


class LoadWriteProbeOutputTest(unittest.TestCase):
    def make_probe_path(self, *, relative: bool = False) -> str:
        temp_dir = tempfile.TemporaryDirectory(dir=PROJECT_ROOT)
        self.addCleanup(temp_dir.cleanup)
        probe_path = Path(temp_dir.name) / "cache" / "probe.json"
        if relative:
            return str(probe_path.relative_to(PROJECT_ROOT))
        return str(probe_path)

    def test_write_probe_output_writes_json_to_target_path(self) -> None:
        payload = {
            "requested_at": "2026-03-15T13:00:00+0800",
            "reachable": True,
            "status": "success",
            "details": {"hostname": "demo-board"},
        }
        output_path = Path(self.make_probe_path())

        write_probe_output(payload, output_path)

        self.assertTrue(output_path.exists())
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), payload)
        self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))

    def test_load_probe_output_reads_valid_json_from_relative_path(self) -> None:
        payload = {
            "requested_at": "2026-03-15T13:05:00+0800",
            "reachable": True,
            "status": "success",
        }
        output_path = self.make_probe_path(relative=True)

        write_probe_output(payload, output_path)

        self.assertEqual(load_probe_output(output_path), payload)

    def test_load_probe_output_returns_none_for_missing_file(self) -> None:
        output_path = self.make_probe_path(relative=True)

        self.assertIsNone(load_probe_output(output_path))

    def test_load_probe_output_returns_none_for_malformed_json(self) -> None:
        output_path = Path(self.make_probe_path())
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{not-json\n", encoding="utf-8")

        self.assertIsNone(load_probe_output(output_path))


class RunLiveProbeTest(unittest.TestCase):
    def test_success_payload_shaping_from_valid_json_stdout(self) -> None:
        command = ["bash", "fake-connect"]
        details = {
            "hostname": "phytium-demo",
            "remoteproc": [
                {"name": "remoteproc0", "state": "running"},
                {"name": "remoteproc1", "state": "offline"},
            ],
            "rpmsg_devices": ["/dev/rpmsg0", "/dev/rpmsg1"],
            "firmware": {"sha256": "abcdef1234567890fedcba"},
        }
        completed = subprocess.CompletedProcess(
            command,
            0,
            stdout="ssh banner\n" + json.dumps(details) + "\n",
            stderr="",
        )

        with (
            patch("board_probe.now_iso", return_value="2026-03-15T12:00:00+0800"),
            patch("board_probe.build_probe_command", return_value=command) as build_command,
            patch("board_probe.subprocess.run", return_value=completed) as run_mock,
        ):
            payload = run_live_probe(env_file="demo.env", timeout_sec=12.5)

        build_command.assert_called_once_with("demo.env")
        run_mock.assert_called_once_with(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=12.5,
        )
        self.assertEqual(
            payload,
            {
                "requested_at": "2026-03-15T12:00:00+0800",
                "reachable": True,
                "status": "success",
                "summary": "phytium-demo reachable; remoteproc0=running, remoteproc1=offline; 2 rpmsg device(s); firmware abcdef123456.",
                "error": "",
                "details": details,
            },
        )

    def test_timeout_returns_timeout_payload(self) -> None:
        command = ["bash", "fake-connect"]

        with (
            patch("board_probe.now_iso", return_value="2026-03-15T12:05:00+0800"),
            patch("board_probe.build_probe_command", return_value=command) as build_command,
            patch(
                "board_probe.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=command, timeout=3.0),
            ) as run_mock,
        ):
            payload = run_live_probe(timeout_sec=3.0)

        build_command.assert_called_once_with(None)
        run_mock.assert_called_once_with(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=3.0,
        )
        self.assertEqual(
            payload,
            {
                "requested_at": "2026-03-15T12:05:00+0800",
                "reachable": False,
                "status": "timeout",
                "summary": "The read-only SSH probe timed out before a response arrived.",
                "error": "probe timeout",
                "details": {},
            },
        )

    def test_non_zero_exit_returns_error_payload(self) -> None:
        command = ["bash", "fake-connect"]
        completed = subprocess.CompletedProcess(
            command,
            7,
            stdout="transient stdout\n",
            stderr="permission denied\n",
        )

        with (
            patch("board_probe.now_iso", return_value="2026-03-15T12:10:00+0800"),
            patch("board_probe.build_probe_command", return_value=command) as build_command,
            patch("board_probe.subprocess.run", return_value=completed) as run_mock,
        ):
            payload = run_live_probe(timeout_sec=9.0)

        build_command.assert_called_once_with(None)
        run_mock.assert_called_once_with(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=9.0,
        )
        self.assertEqual(
            payload,
            {
                "requested_at": "2026-03-15T12:10:00+0800",
                "reachable": False,
                "status": "error",
                "summary": "The read-only SSH probe could not reach the board from this environment.",
                "error": "permission denied",
                "details": {},
            },
        )

    def test_invalid_json_stdout_returns_parse_error_payload(self) -> None:
        command = ["bash", "fake-connect"]
        completed = subprocess.CompletedProcess(
            command,
            0,
            stdout="ssh banner\nnot-json\n",
            stderr="stderr line\n",
        )

        with (
            patch("board_probe.now_iso", return_value="2026-03-15T12:15:00+0800"),
            patch("board_probe.build_probe_command", return_value=command) as build_command,
            patch("board_probe.subprocess.run", return_value=completed) as run_mock,
        ):
            payload = run_live_probe(timeout_sec=6.0)

        build_command.assert_called_once_with(None)
        run_mock.assert_called_once_with(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=6.0,
        )
        self.assertEqual(payload["requested_at"], "2026-03-15T12:15:00+0800")
        self.assertFalse(payload["reachable"])
        self.assertEqual(payload["status"], "parse_error")
        self.assertEqual(
            payload["summary"],
            "The read-only SSH probe returned output that could not be parsed as JSON.",
        )
        self.assertIn("Expecting value", payload["error"])
        self.assertEqual(
            payload["details"],
            {"stdout": "ssh banner\nnot-json", "stderr": "stderr line"},
        )


if __name__ == "__main__":
    unittest.main()
