from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import tempfile
import textwrap
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parents[2]
LAUNCHER = REPO_ROOT / "session_bootstrap" / "scripts" / "run_openamp_demo.sh"
SERVER = REPO_ROOT / "session_bootstrap" / "demo" / "openamp_control_plane_demo" / "server.py"


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


class OpenAMPDemoLauncherTest(unittest.TestCase):
    def build_mock_env(self, temp_dir: Path, ss_before: str, ss_after: str, ps_output: str) -> tuple[dict[str, str], Path]:
        bin_dir = temp_dir / "bin"
        bin_dir.mkdir()

        ss_before_path = temp_dir / "ss_before.txt"
        ss_after_path = temp_dir / "ss_after.txt"
        ps_output_path = temp_dir / "ps_output.txt"
        ss_call_count_path = temp_dir / "ss.calls"
        python_log_path = temp_dir / "python.log"

        ss_before_path.write_text(ss_before, encoding="utf-8")
        ss_after_path.write_text(ss_after, encoding="utf-8")
        ps_output_path.write_text(ps_output, encoding="utf-8")

        write_executable(
            bin_dir / "ss",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                call_count=0
                if [[ -f "${MOCK_SS_CALL_COUNT_FILE}" ]]; then
                    call_count="$(cat "${MOCK_SS_CALL_COUNT_FILE}")"
                fi
                if [[ "${call_count}" == "0" ]]; then
                    printf '1' > "${MOCK_SS_CALL_COUNT_FILE}"
                    cat "${MOCK_SS_OUTPUT_FILE}"
                else
                    cat "${MOCK_SS_OUTPUT_AFTER_FILE}"
                fi
                """
            ),
        )
        write_executable(
            bin_dir / "ps",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                if [[ "${1:-}" == "-eo" && "${2:-}" == "pid=,args=" ]]; then
                    cat "${MOCK_PS_OUTPUT_FILE}"
                    exit 0
                fi
                printf 'unexpected ps invocation: %s\n' "$*" >&2
                exit 1
                """
            ),
        )
        write_executable(
            bin_dir / "kill",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                exit 0
                """
            ),
        )
        write_executable(
            bin_dir / "python3",
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\n' "$*" > "${MOCK_PYTHON_LOG_FILE}"
                exit 0
                """
            ),
        )

        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir}:{env['PATH']}",
                "MOCK_SS_OUTPUT_FILE": str(ss_before_path),
                "MOCK_SS_OUTPUT_AFTER_FILE": str(ss_after_path),
                "MOCK_SS_CALL_COUNT_FILE": str(ss_call_count_path),
                "MOCK_PS_OUTPUT_FILE": str(ps_output_path),
                "MOCK_PYTHON_LOG_FILE": str(python_log_path),
            }
        )
        return env, python_log_path

    def test_reclaims_existing_demo_server_listener_before_restart(self) -> None:
        port = "8090"
        ss_before = f"LISTEN 0 5 127.0.0.1:{port} 0.0.0.0:*\n"
        fake_pid = "999999"
        ps_output = f"{fake_pid} python3 {SERVER} --port {port}\n"

        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            env, python_log_path = self.build_mock_env(temp_dir, ss_before, "", ps_output)

            result = subprocess.run(
                ["bash", str(LAUNCHER), "--port", port],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Reclaiming port {port} from existing OpenAMP demo server PID {fake_pid}.", result.stderr)
            self.assertEqual(python_log_path.read_text(encoding="utf-8").strip(), f"{SERVER} --port {port}")

    def test_refuses_to_kill_non_demo_listener_on_requested_port(self) -> None:
        port = "8091"
        ss_before = f"LISTEN 0 5 127.0.0.1:{port} 0.0.0.0:*\n"

        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            env, python_log_path = self.build_mock_env(temp_dir, ss_before, "", "")

            result = subprocess.run(
                ["bash", str(LAUNCHER), f"--port={port}"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(f"Requested OpenAMP demo port {port} is already in use", result.stderr)
            self.assertIn("Refusing to stop a non-OpenAMP listener.", result.stderr)
            self.assertFalse(python_log_path.exists())


if __name__ == "__main__":
    unittest.main()
