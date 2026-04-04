from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import crypto_runtime  # noqa: E402


class CryptoRuntimeTest(unittest.TestCase):
    def test_resolve_local_crypto_client_discovers_sibling_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            current_repo = temp_root / "Semantic-Communication"
            sibling_repo = temp_root / "ICCompetition2026"
            (current_repo / "session_bootstrap").mkdir(parents=True)
            (sibling_repo / "scripts").mkdir(parents=True)
            client_script = sibling_repo / "scripts" / "tcp_client.py"
            client_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            with (
                patch.object(crypto_runtime, "PROJECT_ROOT", current_repo),
                patch.object(crypto_runtime.Path, "cwd", return_value=current_repo),
            ):
                resolved, searched = crypto_runtime.resolve_local_crypto_client({})

        self.assertEqual(resolved, client_script.resolve())
        self.assertIn(client_script.resolve(), searched)

    def test_build_remote_crypto_server_command_uses_env_overrides(self) -> None:
        env_values = {
            "MLKEM_REMOTE_PROJECT_ROOT": "/opt/semantic",
            "MLKEM_REMOTE_PYTHON": "/opt/mlkem/bin/python",
            "REMOTE_TVM_PYTHON": "/opt/tvm/bin/python",
            "REMOTE_CURRENT_ARTIFACT": "/models/current.so",
            "MLKEM_PORT": "9540",
            "MLKEM_STATUS_PORT": "18080",
            "MLKEM_REMOTE_LOG_PATH": "/tmp/mlkem-server.log",
            "MLKEM_REMOTE_PRELUDE": "export EXTRA_FLAG=1",
            "MLKEM_CIPHER_SUITE": "SM4_GCM",
        }

        command = crypto_runtime.build_remote_crypto_server_command(
            env_values,
            local_server_script=Path("/tmp/local/scripts/tcp_server.py"),
        )

        self.assertIn("/opt/mlkem/bin/python", command)
        self.assertIn("/opt/semantic/scripts/tcp_server.py", command)
        self.assertIn("--port 9540", command)
        self.assertIn("--status-port 18080", command)
        self.assertIn("--artifact-path /models/current.so", command)
        self.assertIn("--tvm-python /opt/tvm/bin/python", command)
        self.assertIn("--suite SM4_GCM", command)
        self.assertIn("nohup", command)
        self.assertIn("export EXTRA_FLAG=1", command)

    def test_run_ssh_command_falls_back_to_askpass_when_sshpass_missing(self) -> None:
        captured: dict[str, object] = {}

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            command = args[0]
            env = kwargs["env"]
            captured["command"] = command
            captured["env"] = env
            askpass_path = Path(str(env["SSH_ASKPASS"]))
            captured["askpass_exists_during_run"] = askpass_path.exists()
            captured["askpass_body"] = askpass_path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

        with (
            patch("crypto_runtime.shutil.which", return_value=None),
            patch("crypto_runtime.subprocess.run", side_effect=fake_run),
        ):
            result = crypto_runtime.run_ssh_command(
                host="demo-board",
                user="demo-user",
                password="demo-pass",
                port="22",
                remote_command="echo ready",
                timeout=5,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(captured["command"][0], "ssh")
        self.assertTrue(captured["askpass_exists_during_run"])
        self.assertIn("demo-pass", str(captured["askpass_body"]))
        self.assertEqual(captured["env"]["SSH_ASKPASS_REQUIRE"], "force")
        self.assertFalse(Path(str(captured["env"]["SSH_ASKPASS"])).exists())

    def test_build_local_crypto_client_command_uses_detected_oqs_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            current_repo = temp_root / "Semantic-Communication"
            sibling_repo = temp_root / "ICCompetition2026"
            current_repo.mkdir()
            (sibling_repo / "scripts").mkdir(parents=True)
            (sibling_repo / "liboqs-dist").mkdir(parents=True)
            client_script = sibling_repo / "scripts" / "tcp_client.py"
            client_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            input_path = temp_root / "sample.bin"
            input_path.write_bytes(b"\0" * 32)

            with (
                patch.object(crypto_runtime, "PROJECT_ROOT", current_repo),
                patch.object(crypto_runtime.Path, "cwd", return_value=current_repo),
            ):
                command, env = crypto_runtime.build_local_crypto_client_command(
                    {},
                    host="127.0.0.1",
                    input_path=input_path,
                    client_script=client_script,
                )

        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1], str(client_script))
        self.assertEqual(env["OQS_INSTALL_PATH"], str((sibling_repo / "liboqs-dist").resolve()))


if __name__ == "__main__":
    unittest.main()
