from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import inference_runner  # noqa: E402
from board_access import BoardAccessConfig  # noqa: E402
from inference_runner import (  # noqa: E402
    PROJECT_ROOT,
    LiveRemoteReconstructionJob,
    REMOTE_RECONSTRUCTION_SCRIPT,
    run_remote_reconstruction,
)


def make_access(env_values: dict[str, str] | None = None) -> BoardAccessConfig:
    values = {
        "REMOTE_TVM_PYTHON": "/usr/bin/python3",
        "REMOTE_INPUT_DIR": "/tmp/input",
        "REMOTE_OUTPUT_BASE": "/tmp/output",
        "REMOTE_SNR_CURRENT": "12",
        "REMOTE_BATCH_CURRENT": "1",
    }
    values.update(env_values or {})
    return BoardAccessConfig(
        host="demo-board",
        user="demo-user",
        password="demo-pass",
        port="22",
        env_file=None,
        env_values=values,
        source_summary="unit test",
    )


class RunRemoteReconstructionTest(unittest.TestCase):
    def test_generate_live_job_id_wraps_to_non_zero_uint32_and_stays_unique(self) -> None:
        original_last_job_id = inference_runner._LAST_LIVE_JOB_ID
        try:
            inference_runner._LAST_LIVE_JOB_ID = 0
            with patch("inference_runner.time.time", side_effect=[4294967.296, 4294967.296]):
                first = inference_runner.generate_live_job_id()
                second = inference_runner.generate_live_job_id()
        finally:
            inference_runner._LAST_LIVE_JOB_ID = original_last_job_id

        self.assertEqual(first, "1")
        self.assertEqual(second, "2")
        self.assertLessEqual(int(second), inference_runner.UINT32_MAX)

    def test_missing_required_config_returns_operator_friendly_config_error(self) -> None:
        access = make_access(
            {
                "REMOTE_TVM_PYTHON": "",
                "REMOTE_INPUT_DIR": "",
            }
        )

        payload = run_remote_reconstruction(access, variant="current")

        self.assertEqual(payload["status"], "config_error")
        self.assertEqual(payload["status_category"], "config_error")
        self.assertIn("远端推理配置不完整或不可用", payload["message"])
        self.assertNotIn("REMOTE_TVM_PYTHON", payload["message"])
        self.assertIn("REMOTE_TVM_PYTHON", payload["diagnostics"]["missing_fields"])
        self.assertIn("REMOTE_INPUT_DIR", payload["diagnostics"]["missing_fields"])

    def test_auth_failure_keeps_raw_stderr_in_diagnostics_only(self) -> None:
        access = make_access()
        command = [
            "bash",
            str(REMOTE_RECONSTRUCTION_SCRIPT),
            "--variant",
            "current",
            "--max-inputs",
            "1",
            "--seed",
            "0",
        ]
        completed = subprocess.CompletedProcess(
            command,
            255,
            stdout="",
            stderr="Permission denied (publickey,password).\n",
        )

        with patch("inference_runner.subprocess.run", return_value=completed) as run_mock:
            payload = run_remote_reconstruction(access, variant="current", timeout_sec=12.0)

        run_mock.assert_called_once_with(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=12.0,
            env={
                **access.build_subprocess_env(),
                "REMOTE_MODE": "ssh",
            },
        )
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["status_category"], "auth_error")
        self.assertIn("认证失败", payload["message"])
        self.assertNotIn("Permission denied", payload["message"])
        self.assertEqual(
            payload["diagnostics"],
            {
                "stderr": "Permission denied (publickey,password).",
                "returncode": 255,
            },
        )

    def test_artifact_sha_mismatch_surfaces_actionable_category_and_structured_diagnostics(self) -> None:
        access = make_access()
        expected_sha = "1946b08e6cf20a1259fa43f9e849a06f50ae1230c08d4df7081fba1edae4c644"
        actual_sha = "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1"
        artifact_path = "/home/user/Downloads/jscc-test/jscc/tvm_tune_logs/optimized_model.so"
        completed = subprocess.CompletedProcess(
            ["bash", str(REMOTE_RECONSTRUCTION_SCRIPT)],
            1,
            stdout="",
            stderr=(
                "ERROR: artifact sha256 mismatch "
                f"path={artifact_path} expected={expected_sha} actual={actual_sha}\n"
            ),
        )

        with patch("inference_runner.subprocess.run", return_value=completed):
            payload = run_remote_reconstruction(access, variant="current")

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["status_category"], "artifact_mismatch")
        self.assertIn("trusted current SHA 不一致", payload["message"])
        self.assertNotIn(expected_sha, payload["message"])
        self.assertEqual(
            payload["diagnostics"],
            {
                "stderr": (
                    "ERROR: artifact sha256 mismatch "
                    f"path={artifact_path} expected={expected_sha} actual={actual_sha}"
                ),
                "returncode": 1,
                "artifact_path": artifact_path,
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
            },
        )

    def test_build_hook_command_forwards_remote_project_root_to_proxy(self) -> None:
        access = make_access({"REMOTE_PROJECT_ROOT": "/tmp/openamp_wrong_sha_fit/project"})
        job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
        job.job_id = "job-123"

        command = shlex.split(job._build_hook_command(access))

        self.assertIn("--remote-project-root", command)
        self.assertEqual(
            command[command.index("--remote-project-root") + 1],
            "/tmp/openamp_wrong_sha_fit/project",
        )

    def test_live_job_constructor_passes_generated_uint32_job_id_to_wrapper_and_hook(self) -> None:
        access = make_access({"REMOTE_PROJECT_ROOT": "/tmp/openamp_demo/project"})

        with (
            patch("inference_runner.generate_live_job_id", return_value="4242"),
            patch("inference_runner.tempfile.mkdtemp", return_value="/tmp/openamp_demo_live_test"),
            patch("inference_runner.subprocess.Popen", return_value=object()) as popen_mock,
            patch("inference_runner.Thread") as thread_cls,
        ):
            thread_cls.return_value.start.return_value = None
            live_job = LiveRemoteReconstructionJob(access, variant="current")

        self.assertEqual(live_job.job_id, "4242")
        command = popen_mock.call_args.args[0]
        self.assertEqual(command[command.index("--job-id") + 1], "4242")
        hook_command = command[command.index("--control-hook-cmd") + 1]
        self.assertIn("--remote-output-root", hook_command)
        self.assertIn("/tmp/openamp_demo_hook/4242", hook_command)


if __name__ == "__main__":
    unittest.main()
