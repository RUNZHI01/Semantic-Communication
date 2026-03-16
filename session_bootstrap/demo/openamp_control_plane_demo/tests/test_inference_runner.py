from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from threading import Lock
import unittest
from unittest.mock import Mock, patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import inference_runner  # noqa: E402
from board_access import BoardAccessConfig  # noqa: E402
from inference_runner import (  # noqa: E402
    PROJECT_ROOT,
    LiveRemoteReconstructionJob,
    REMOTE_RECONSTRUCTION_SCRIPT,
    live_control_hook_timeout_sec,
    run_remote_reconstruction,
)


def make_access(env_values: dict[str, str] | None = None) -> BoardAccessConfig:
    values = {
        "REMOTE_TVM_PYTHON": "/usr/bin/python3",
        "REMOTE_INPUT_DIR": "/tmp/input",
        "REMOTE_OUTPUT_BASE": "/tmp/output",
        "REMOTE_SNR_CURRENT": "12",
        "REMOTE_BATCH_CURRENT": "1",
        "INFERENCE_CURRENT_EXPECTED_SHA256": "a" * 64,
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
    def test_generate_live_job_id_uses_non_zero_uint32_nonce_and_stays_unique(self) -> None:
        original_last_job_id = inference_runner._LAST_LIVE_JOB_ID
        try:
            inference_runner._LAST_LIVE_JOB_ID = 0
            with patch("inference_runner.secrets.randbelow", side_effect=[0, 0, inference_runner.UINT32_MAX - 1]):
                first = inference_runner.generate_live_job_id()
                second = inference_runner.generate_live_job_id()
        finally:
            inference_runner._LAST_LIVE_JOB_ID = original_last_job_id

        self.assertEqual(first, "1")
        self.assertEqual(second, str(inference_runner.UINT32_MAX))
        self.assertLessEqual(int(second), inference_runner.UINT32_MAX)

    def test_count_completed_images_from_runner_log_uses_real_latency_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner_log = Path(temp_dir) / "runner.log"
            runner_log.write_text(
                "\n".join(
                    [
                        "[current-real] variant=current",
                        "2026-03-16 10:00:01 - INFO - 批量推理时间（1 个样本）: 0.011000 秒",
                        "重构图像保存至: /tmp/run/sample_001.png",
                        "2026-03-16 10:00:02 - INFO - 批量推理时间（1 个样本）: 0.012000 秒",
                        "batch inference time: 0.013 sec",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            completed = inference_runner.count_completed_images_from_runner_log(runner_log)

        self.assertEqual(completed, 3)

    def test_build_completion_counts_marks_missing_runner_log_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner_log = Path(temp_dir) / "runner.log"

            counts = inference_runner.build_completion_counts(
                runner_log_path=runner_log,
                expected_outputs=inference_runner.DEFAULT_MAX_INPUTS,
            )

        self.assertEqual(counts["completed_count"], 0)
        self.assertEqual(counts["expected_count"], inference_runner.DEFAULT_MAX_INPUTS)
        self.assertEqual(counts["count_label"], f"0 / {inference_runner.DEFAULT_MAX_INPUTS}")
        self.assertEqual(counts["count_source"], "runner_log.missing")

    def test_running_snapshot_reports_real_completed_count_from_runner_log(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            runner_log_path = output_dir / "runner.log"
            runner_log_path.write_text(
                "\n".join(
                    [
                        "[2026-03-16T11:00:00+0800] openamp wrapper start",
                        "批量推理时间（1 个样本）: 0.012 秒",
                        "批量推理时间（1 个样本）: 0.014 秒",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            trace_path = output_dir / "control_trace.jsonl"
            trace_path.write_text(
                json.dumps(
                    {
                        "at": "2026-03-16T11:00:01+0800",
                        "phase": "JOB_ACK",
                        "payload": {"job_id": 4242, "decision": "ALLOW", "guard_state_name": "JOB_ACTIVE"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = output_dir / "wrapper_summary.json"
            job._runner_log_path = runner_log_path
            job._lock = Lock()
            job._final_snapshot = None
            job._process = None

            snapshot = job.snapshot()

        self.assertEqual(snapshot["request_state"], "running")
        self.assertEqual(snapshot["progress"]["completed_count"], 2)
        self.assertEqual(snapshot["progress"]["expected_count"], inference_runner.DEFAULT_MAX_INPUTS)
        self.assertEqual(snapshot["progress"]["remaining_count"], inference_runner.DEFAULT_MAX_INPUTS - 2)
        self.assertEqual(snapshot["progress"]["count_label"], f"2 / {inference_runner.DEFAULT_MAX_INPUTS}")
        self.assertEqual(snapshot["progress"]["count_source"], "runner_log.sample_latency_lines")
        self.assertEqual(snapshot["progress"]["percent"], 1)

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
        runner_cmd = inference_runner.build_runner_command(
            access,
            variant="current",
            max_inputs=inference_runner.DEFAULT_MAX_INPUTS,
            seed=0,
        )
        command = ["bash", "-lc", runner_cmd]
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
                "OPENAMP_DEMO_MODE": "1",
                "OPENAMP_DEMO_MAX_INPUTS": str(inference_runner.DEFAULT_MAX_INPUTS),
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
        command = ["bash", "-lc", inference_runner.build_runner_command(access, variant="current", max_inputs=1, seed=0)]
        completed = subprocess.CompletedProcess(
            command,
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

    def test_build_hook_command_keeps_live_demo_on_bundled_bridge_runtime(self) -> None:
        access = make_access({"REMOTE_PROJECT_ROOT": "/tmp/openamp_wrong_sha_fit/project"})
        job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
        job.job_id = "job-123"

        command = shlex.split(job._build_hook_command(access))

        self.assertNotIn("--remote-project-root", command)

    def test_build_runner_command_adds_sample_cap_for_configured_legacy_baseline_cmd(self) -> None:
        access = make_access(
            {
                "REMOTE_SNR_BASELINE": "10",
                "REMOTE_BATCH_BASELINE": "1",
                "INFERENCE_BASELINE_EXPECTED_SHA256": "b" * 64,
                "INFERENCE_BASELINE_CMD": "bash ./session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh --variant baseline",
            }
        )

        command = inference_runner.build_runner_command(access, variant="baseline", max_inputs=1, seed=0)

        self.assertEqual(
            command,
            "bash ./session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh --variant baseline --max-inputs 1",
        )
        self.assertNotIn(REMOTE_RECONSTRUCTION_SCRIPT.name, command)
        self.assertNotIn("--seed", command)

    def test_build_runner_command_keeps_sampling_args_for_current_reconstruction_cmd(self) -> None:
        access = make_access(
            {
                "INFERENCE_CURRENT_CMD": (
                    "bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh "
                    "--variant current --max-inputs 1 --seed 99 --profile-ops"
                ),
            }
        )

        command = inference_runner.build_runner_command(access, variant="current", max_inputs=3, seed=7)

        self.assertEqual(
            command,
            (
                f"bash {REMOTE_RECONSTRUCTION_SCRIPT} --variant current --max-inputs 3 --seed 7"
            ),
        )
        self.assertNotIn("--profile-ops", command)
        self.assertNotIn("--max-inputs 1", command)
        self.assertNotIn("--seed 99", command)

    def test_build_runner_command_for_current_ignores_legacy_current_cmd_residue(self) -> None:
        access = make_access(
            {
                "INFERENCE_CURRENT_CMD": "bash ./session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh --variant current --max-inputs 1",
            }
        )

        command = inference_runner.build_runner_command(access, variant="current", max_inputs=300, seed=0)

        self.assertEqual(
            command,
            (
                f"bash {REMOTE_RECONSTRUCTION_SCRIPT} --variant current --max-inputs 300 --seed 0"
            ),
        )
        self.assertNotIn("run_remote_legacy_tvm_compat.sh", command)

    def test_baseline_live_job_requires_formal_baseline_expected_sha_before_launch(self) -> None:
        access = make_access(
            {
                "REMOTE_SNR_BASELINE": "12",
                "REMOTE_BATCH_BASELINE": "1",
            }
        )

        with patch("inference_runner.subprocess.Popen") as popen_mock:
            live_job = LiveRemoteReconstructionJob(access, variant="baseline")

        snapshot = live_job.snapshot()
        self.assertEqual(snapshot["status"], "config_error")
        self.assertEqual(snapshot["status_category"], "config_error")
        self.assertIn("formal baseline expected SHA", snapshot["message"])
        self.assertEqual(snapshot["diagnostics"]["missing_fields"], ["INFERENCE_BASELINE_EXPECTED_SHA256"])
        popen_mock.assert_not_called()

    def test_live_job_constructor_passes_generated_uint32_job_id_to_wrapper_and_hook(self) -> None:
        access = make_access(
            {
                "REMOTE_PROJECT_ROOT": "/tmp/openamp_demo/project",
                "INFERENCE_CURRENT_CMD": "bash ./session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh --variant current --max-inputs 1",
            }
        )

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
        self.assertEqual(
            command[command.index("--control-hook-timeout-sec") + 1],
            str(live_control_hook_timeout_sec(900.0)),
        )
        self.assertEqual(
            command[command.index("--expected-outputs") + 1],
            str(inference_runner.DEFAULT_MAX_INPUTS),
        )
        runner_cmd = command[command.index("--runner-cmd") + 1]
        self.assertIn(str(REMOTE_RECONSTRUCTION_SCRIPT), runner_cmd)
        self.assertNotIn("run_remote_legacy_tvm_compat.sh", runner_cmd)
        self.assertIn(f"--max-inputs {inference_runner.DEFAULT_MAX_INPUTS}", runner_cmd)
        self.assertIn("--seed 0", runner_cmd)
        hook_command = command[command.index("--control-hook-cmd") + 1]
        self.assertIn("--remote-output-root", hook_command)
        self.assertIn("/tmp/openamp_demo_hook/4242", hook_command)
        env = popen_mock.call_args.kwargs["env"]
        self.assertEqual(env["OPENAMP_DEMO_MODE"], "1")
        self.assertEqual(env["OPENAMP_DEMO_MAX_INPUTS"], str(inference_runner.DEFAULT_MAX_INPUTS))

    def test_live_job_control_hook_timeout_is_capped_at_runner_timeout_when_shorter(self) -> None:
        access = make_access()

        with (
            patch("inference_runner.generate_live_job_id", return_value="4242"),
            patch("inference_runner.tempfile.mkdtemp", return_value="/tmp/openamp_demo_live_test"),
            patch("inference_runner.subprocess.Popen", return_value=object()) as popen_mock,
            patch("inference_runner.Thread") as thread_cls,
        ):
            thread_cls.return_value.start.return_value = None
            LiveRemoteReconstructionJob(access, variant="current", timeout_sec=12.0)

        command = popen_mock.call_args.args[0]
        self.assertEqual(
            command[command.index("--control-hook-timeout-sec") + 1],
            str(live_control_hook_timeout_sec(12.0)),
        )

    def test_permission_gate_failure_surfaces_explicit_live_contract(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"

            summary_path.write_text(
                json.dumps({"result": "denied_by_control_hook"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-15T20:00:00+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
                            "source": "replayed_live_status_resp",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                            "rx_frame": {
                                "status_resp": {
                                    "guard_state_name": "READY",
                                    "last_fault_name": "NONE",
                                }
                            },
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:00:01+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4242, "expected_sha256": "abcd" * 16},
                    "hook_result": {
                        "returncode": 2,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "DENY",
                            "fault_code": 0,
                            "fault_name": "NONE",
                            "guard_state": 0,
                            "guard_state_name": "BOOT",
                            "source": "linux_bridge_permission_guard",
                            "transport_status": "permission_gate",
                            "protocol_semantics": "not_attempted",
                            "note": (
                                "JOB_REQ could not access /dev/rpmsg0: [Errno 13] Permission denied: "
                                "'/dev/rpmsg0'. The board-side bridge needs root or passwordless sudo "
                                "for RPMsg device access."
                            ),
                            "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
                            "rpmsg_dev": "/dev/rpmsg0",
                            "device_status": {
                                "rpmsg_ctrl": {"path": "/dev/rpmsg_ctrl0", "exists": True},
                                "rpmsg_dev": {"path": "/dev/rpmsg0", "exists": True},
                            },
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:00:01+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4242,
                        "decision": "DENY",
                        "fault_code": 0,
                        "fault_name": "NONE",
                        "guard_state": 0,
                        "guard_state_name": "BOOT",
                        "source": "linux_bridge_permission_guard",
                        "transport_status": "permission_gate",
                        "protocol_semantics": "not_attempted",
                        "note": (
                            "JOB_REQ could not access /dev/rpmsg0: [Errno 13] Permission denied: "
                            "'/dev/rpmsg0'. The board-side bridge needs root or passwordless sudo "
                            "for RPMsg device access."
                        ),
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = output_dir / "runner.log"
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = (summary_path.read_text(encoding="utf-8"), "")
            fake_process.returncode = 2
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "permission_error")
            self.assertIn("root 或 passwordless sudo", snapshot["message"])
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["transport_status"], "permission_gate")
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["rpmsg_dev"], "/dev/rpmsg0")
            self.assertIn("板端权限门禁", snapshot["progress"]["stages"][2]["detail"])
            self.assertIn("/dev/rpmsg0", snapshot["progress"]["stages"][2]["detail"])
            self.assertIn("transport=permission_gate", snapshot["progress"]["event_log"][2])

    def test_tx_ok_rx_timeout_marks_control_stages_as_failed_and_keeps_zero_progress(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"

            summary_path.write_text(
                json.dumps({"result": "denied_by_control_hook"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-16T11:24:03+0800",
                    "phase": "STATUS_REQ",
                    "payload": {
                        "job_id": 4203105938,
                        "variant": "current_reconstruction",
                        "expected_sha256": "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1",
                        "job_flags": "reconstruction",
                    },
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
                            "transport_status": "tx_ok_rx_timeout",
                            "protocol_semantics": "not_verified",
                            "note": (
                                "write to /dev/rpmsg0 succeeded but no response arrived before timeout. "
                                "Do not claim STATUS_RESP semantics from this result."
                            ),
                        },
                    },
                },
                {
                    "at": "2026-03-16T11:24:06+0800",
                    "phase": "JOB_REQ",
                    "payload": {
                        "job_id": 4203105938,
                        "expected_sha256": "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1",
                        "deadline_ms": 300000,
                        "expected_outputs": 300,
                        "job_flags": "reconstruction",
                        "runner_cmd": (
                            "bash /home/tianxing/tvm_metaschedule_execution_project/"
                            "session_bootstrap/scripts/run_remote_current_real_reconstruction.sh "
                            "--variant current --max-inputs 300 --seed 0"
                        ),
                    },
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "DENY",
                            "fault_code": 0,
                            "fault_name": "NONE",
                            "guard_state": 0,
                            "guard_state_name": "BOOT",
                            "source": "linux_bridge_transport_guard",
                            "transport_status": "tx_ok_rx_timeout",
                            "protocol_semantics": "not_verified",
                            "note": (
                                "JOB_REQ was written to /dev/rpmsg0 but no JOB_ACK arrived before timeout. "
                                "The wrapper must deny locally instead of assuming admission."
                            ),
                        },
                    },
                },
                {
                    "at": "2026-03-16T11:24:09+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4203105938,
                        "decision": "DENY",
                        "source": "linux_bridge_transport_guard",
                        "fault_code": 0,
                        "fault_name": "NONE",
                        "guard_state": 0,
                        "guard_state_name": "BOOT",
                        "transport_status": "tx_ok_rx_timeout",
                        "protocol_semantics": "not_verified",
                        "note": (
                            "JOB_REQ was written to /dev/rpmsg0 but no JOB_ACK arrived before timeout. "
                            "The wrapper must deny locally instead of assuming admission."
                        ),
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4203105938"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = output_dir / "runner.log"
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 2
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["progress"]["count_label"], f"0 / {inference_runner.DEFAULT_MAX_INPUTS}")
            self.assertEqual(snapshot["progress"]["count_source"], "runner_log.missing")
            self.assertEqual(snapshot["progress"]["stages"][0]["status"], "error")
            self.assertEqual(snapshot["progress"]["stages"][1]["status"], "error")
            self.assertEqual(snapshot["progress"]["stages"][2]["status"], "error")
            self.assertEqual(snapshot["progress"]["current_stage"], "连接失败")
            self.assertIn("tx_ok_rx_timeout", snapshot["progress"]["event_log"][2])

    def test_success_snapshot_keeps_control_hook_timeout_as_diagnostic_not_runner_timeout(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"
            runner_log_path = output_dir / "runner.log"

            summary_path.write_text(
                json.dumps({"result": "success"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-16T10:00:00+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "timed_out": False,
                        "duration_ms": 820,
                        "response": {
                            "phase": "STATUS_REQ",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                        },
                    },
                },
                {
                    "at": "2026-03-16T10:00:02+0800",
                    "phase": "HEARTBEAT",
                    "payload": {"job_id": 4242, "elapsed_ms": 2000, "runtime_state": "RUNNING"},
                    "hook_result": {
                        "returncode": None,
                        "timed_out": True,
                        "timeout_sec": 30.0,
                        "duration_ms": 30012,
                        "response": {
                            "phase": "HEARTBEAT",
                            "source": "openamp_control_wrapper",
                            "transport_status": "hook_timeout",
                            "protocol_semantics": "not_verified",
                            "note": "HEARTBEAT control hook timed out after 30.0s.",
                        },
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )
            runner_log_path.write_text(
                json.dumps(
                    {
                        "processed_count": 300,
                        "input_count": 300,
                        "load_ms": 2.9,
                        "vm_init_ms": 0.5,
                        "run_median_ms": 230.339,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = runner_log_path
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 0
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "success")
            self.assertEqual(snapshot["status_category"], "success")
            self.assertIn("hook 超时", snapshot["message"])
            self.assertEqual(snapshot["diagnostics"]["control_hook_stats"]["timeout_count"], 1)
            self.assertEqual(snapshot["diagnostics"]["control_hook_stats"]["heartbeat_event_count"], 1)
            self.assertAlmostEqual(snapshot["runner_summary"]["run_median_ms"], 230.339)

    def test_current_live_job_surfaces_slowdown_message_when_heartbeat_hooks_are_expensive(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"
            runner_log_path = output_dir / "runner.log"

            summary_path.write_text(
                json.dumps({"result": "success"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-16T10:28:32+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "timed_out": False,
                        "duration_ms": 2955,
                        "response": {
                            "phase": "STATUS_REQ",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                        },
                    },
                },
                {
                    "at": "2026-03-16T10:28:35+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "timed_out": False,
                        "duration_ms": 2876,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "ALLOW",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                        },
                    },
                },
                {
                    "at": "2026-03-16T10:28:35+0800",
                    "phase": "JOB_ACK",
                    "payload": {"job_id": 4242, "decision": "ALLOW", "guard_state_name": "JOB_ACTIVE"},
                },
            ]
            for offset, duration_ms in enumerate((3521, 3375, 3470, 2818, 3463, 3550, 3410, 3605, 3342), start=1):
                trace_events.append(
                    {
                        "at": f"2026-03-16T10:29:{offset:02d}+0800",
                        "phase": "HEARTBEAT",
                        "payload": {"job_id": 4242, "elapsed_ms": offset * 4000, "runtime_state": "RUNNING"},
                        "hook_result": {
                            "returncode": 0,
                            "timed_out": False,
                            "duration_ms": duration_ms,
                            "response": {
                                "phase": "HEARTBEAT",
                                "acknowledged": True,
                                "heartbeat_ok": 1,
                                "guard_state_name": "JOB_ACTIVE",
                                "source": "firmware_heartbeat_ack",
                                "transport_status": "heartbeat_ack_received",
                                "protocol_semantics": "implemented",
                            },
                        },
                    }
                )
            trace_events.append(
                {
                    "at": "2026-03-16T10:30:54+0800",
                    "phase": "JOB_DONE",
                    "payload": {"job_id": 4242, "elapsed_ms": 134774, "result_code": 0, "runner_exit_code": 0},
                    "hook_result": {
                        "returncode": 0,
                        "timed_out": False,
                        "duration_ms": 2899,
                        "response": {
                            "phase": "JOB_DONE",
                            "acknowledged": True,
                            "transport_status": "job_done_status_received",
                            "protocol_semantics": "implemented",
                        },
                    },
                }
            )
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )
            runner_log_path.write_text(
                json.dumps(
                    {
                        "processed_count": 300,
                        "input_count": 300,
                        "load_ms": 2.718,
                        "vm_init_ms": 0.473,
                        "run_median_ms": 370.274,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = runner_log_path
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 0
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "success")
            self.assertIn("370.274 ms", snapshot["message"])
            self.assertIn("230.339 ms", snapshot["message"])
            self.assertIn("HEARTBEAT hook", snapshot["message"])
            self.assertTrue(snapshot["diagnostics"]["performance_regression"]["control_plane_interference_suspected"])
            self.assertEqual(snapshot["diagnostics"]["performance_regression"]["heartbeat_event_count"], 9)
            self.assertGreater(snapshot["diagnostics"]["control_hook_stats"]["heartbeat_duration_total_ms"], 30000)

    def test_baseline_live_job_ack_artifact_mismatch_is_not_mislabeled_as_permission_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"

            summary_path.write_text(
                json.dumps({"result": "denied_by_control_hook"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-15T20:20:00+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
                            "source": "firmware_status_resp",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable STATUS_RESP frame.",
                            "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
                            "rpmsg_dev": "/dev/rpmsg0",
                            "rx_frame": {
                                "status_resp": {
                                    "guard_state_name": "READY",
                                    "last_fault_name": "ARTIFACT_SHA_MISMATCH",
                                }
                            },
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:20:01+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4242, "expected_sha256": "abcd" * 16},
                    "hook_result": {
                        "returncode": 2,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "DENY",
                            "fault_code": 1,
                            "fault_name": "ARTIFACT_SHA_MISMATCH",
                            "guard_state": 1,
                            "guard_state_name": "READY",
                            "source": "firmware_job_ack",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable JOB_ACK frame from firmware.",
                            "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
                            "rpmsg_dev": "/dev/rpmsg0",
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:20:01+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4242,
                        "decision": "DENY",
                        "fault_code": 1,
                        "fault_name": "ARTIFACT_SHA_MISMATCH",
                        "guard_state": 1,
                        "guard_state_name": "READY",
                        "source": "firmware_job_ack",
                        "transport_status": "job_ack_received",
                        "protocol_semantics": "implemented",
                        "note": "Received a decodable JOB_ACK frame from firmware.",
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "baseline"
            job._timeout_sec = 10.0
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = output_dir / "runner.log"
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 2
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "artifact_mismatch")
            self.assertIn("formal baseline expected SHA", snapshot["message"])
            self.assertNotIn("passwordless sudo", snapshot["message"])
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["fault_name"], "ARTIFACT_SHA_MISMATCH")
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["transport_status"], "job_ack_received")
            self.assertIn("ARTIFACT_SHA_MISMATCH", snapshot["progress"]["stages"][2]["detail"])

    def test_live_runner_log_artifact_mismatch_is_promoted_into_status_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"
            runner_log_path = output_dir / "runner.log"

            summary_path.write_text(
                json.dumps({"result": "runner_failed"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            artifact_path = "/home/user/Downloads/jscc-test/jscc/tvm_tune_logs/optimized_model.so"
            expected_sha = "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1"
            actual_sha = "85d701db0021c26412c3e5e08a4ca043470aaa01fb2d6792cb3b3b29e93bf849"
            runner_log_path.write_text(
                "\n".join(
                    [
                        "[2026-03-16T02:40:43+0800] openamp wrapper start",
                        "runner_cmd=bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current --max-inputs 300 --seed 0",
                        (
                            "ERROR: artifact sha256 mismatch "
                            f"path={artifact_path} expected={expected_sha} actual={actual_sha}"
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-16T02:40:39+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 1200412253},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
                            "source": "firmware_status_resp",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable STATUS_RESP frame.",
                        },
                    },
                },
                {
                    "at": "2026-03-16T02:40:40+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 1200412253, "expected_sha256": expected_sha},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "ALLOW",
                            "fault_name": "NONE",
                            "guard_state_name": "JOB_ACTIVE",
                            "source": "firmware_job_ack",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable JOB_ACK frame from firmware.",
                        },
                    },
                },
                {
                    "at": "2026-03-16T02:40:40+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 1200412253,
                        "decision": "ALLOW",
                        "fault_name": "NONE",
                        "guard_state_name": "JOB_ACTIVE",
                        "source": "firmware_job_ack",
                        "transport_status": "job_ack_received",
                        "protocol_semantics": "implemented",
                        "note": "Received a decodable JOB_ACK frame from firmware.",
                    },
                },
                {
                    "at": "2026-03-16T02:40:56+0800",
                    "phase": "JOB_DONE",
                    "payload": {
                        "job_id": 1200412253,
                        "elapsed_ms": 13056,
                        "result_code": 1,
                        "runner_exit_code": 1,
                        "timed_out": False,
                    },
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "JOB_DONE",
                            "reported_result_code": 1,
                            "reported_output_count": 0,
                            "reported_success": False,
                            "guard_state_name": "READY",
                            "last_fault_name": "OUTPUT_INCOMPLETE",
                            "source": "firmware_job_done_status",
                            "transport_status": "job_done_status_received",
                            "protocol_semantics": "implemented",
                            "note": "Received STATUS_RESP after failed JOB_DONE.",
                        },
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "1200412253"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = runner_log_path
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 1
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "artifact_mismatch")
            self.assertIn("trusted current SHA 不一致", snapshot["message"])
            self.assertEqual(snapshot["diagnostics"]["artifact_path"], artifact_path)
            self.assertEqual(snapshot["diagnostics"]["expected_sha256"], expected_sha)
            self.assertEqual(snapshot["diagnostics"]["actual_sha256"], actual_sha)
            self.assertIn("artifact sha256 mismatch", snapshot["diagnostics"]["runner_log_tail"])
            self.assertEqual(snapshot["progress"]["count_label"], f"0 / {inference_runner.DEFAULT_MAX_INPUTS}")

    def test_live_runner_log_tail_is_attached_for_generic_runner_failure(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"
            runner_log_path = output_dir / "runner.log"

            summary_path.write_text(
                json.dumps({"result": "runner_failed"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            runner_log_path.write_text(
                "\n".join(
                    [
                        "[2026-03-16T03:55:46+0800] openamp wrapper start",
                        "runner_cmd=bash ./session_bootstrap/scripts/run_remote_current_real_reconstruction.sh --variant current --max-inputs 300 --seed 0",
                        '  File "<string>", line 1',
                        "    import",
                        "         ^",
                        "SyntaxError: invalid syntax",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            trace_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "at": "2026-03-16T03:55:45+0800",
                                "phase": "JOB_ACK",
                                "payload": {
                                    "job_id": 1118993338,
                                    "decision": "ALLOW",
                                    "fault_name": "NONE",
                                    "guard_state_name": "JOB_ACTIVE",
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "at": "2026-03-16T03:55:48+0800",
                                "phase": "JOB_DONE",
                                "payload": {
                                    "job_id": 1118993338,
                                    "elapsed_ms": 2023,
                                    "result_code": 1,
                                    "runner_exit_code": 1,
                                    "timed_out": False,
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "1118993338"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._expected_outputs = inference_runner.DEFAULT_MAX_INPUTS
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = runner_log_path
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 1
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "error")
            self.assertIn("SyntaxError: invalid syntax", snapshot["diagnostics"]["runner_log_tail"])

    def test_duplicate_job_ack_is_not_mislabeled_as_permission_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"

            summary_path.write_text(
                json.dumps({"result": "denied_by_control_hook"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-16T02:27:47+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4072741809},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
                            "source": "firmware_status_resp",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable STATUS_RESP frame.",
                            "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
                            "rpmsg_dev": "/dev/rpmsg0",
                            "rx_frame": {
                                "status_resp": {
                                    "guard_state_name": "READY",
                                    "last_fault_name": "NONE",
                                }
                            },
                        },
                    },
                },
                {
                    "at": "2026-03-16T02:27:52+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4072741809, "expected_sha256": "abcd" * 16},
                    "hook_result": {
                        "returncode": 2,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "DENY",
                            "fault_code": 8,
                            "fault_name": "DUPLICATE_JOB_ID",
                            "guard_state": 2,
                            "guard_state_name": "JOB_ACTIVE",
                            "source": "firmware_job_ack",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable JOB_ACK frame from firmware.",
                            "rpmsg_ctrl": "/dev/rpmsg_ctrl0",
                            "rpmsg_dev": "/dev/rpmsg0",
                        },
                    },
                },
                {
                    "at": "2026-03-16T02:27:52+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4072741809,
                        "decision": "DENY",
                        "fault_code": 8,
                        "fault_name": "DUPLICATE_JOB_ID",
                        "guard_state": 2,
                        "guard_state_name": "JOB_ACTIVE",
                        "source": "firmware_job_ack",
                        "transport_status": "job_ack_received",
                        "protocol_semantics": "implemented",
                        "note": "Received a decodable JOB_ACK frame from firmware.",
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4072741809"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = output_dir / "runner.log"
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = ("", "")
            fake_process.returncode = 2
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "error")
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["fault_name"], "DUPLICATE_JOB_ID")
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["rpmsg_dev"], "/dev/rpmsg0")
            self.assertNotIn("passwordless sudo", snapshot["message"])
            self.assertIn("OpenAMP 控制面未放行", snapshot["message"])
            self.assertIn("DUPLICATE_JOB_ID", snapshot["progress"]["stages"][2]["detail"])

    def test_ssh_bridge_launch_failure_surfaces_host_env_error_and_stage_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            output_dir = Path(temp_dir)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"

            summary_path.write_text(
                json.dumps({"result": "denied_by_control_hook"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            trace_events = [
                {
                    "at": "2026-03-15T20:10:00+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 255,
                        "response": {
                            "phase": "STATUS_REQ",
                            "source": "openamp_demo_remote_hook_proxy",
                            "transport_status": "ssh_bridge_launch_failed",
                            "protocol_semantics": "not_verified",
                            "note": "远端 bridge 启动失败，rc=255。",
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:10:01+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4242, "expected_sha256": "abcd" * 16},
                    "hook_result": {
                        "returncode": 255,
                        "response": {
                            "phase": "JOB_REQ",
                            "source": "openamp_demo_remote_hook_proxy",
                            "transport_status": "ssh_bridge_launch_failed",
                            "protocol_semantics": "not_verified",
                            "note": "远端 bridge 启动失败，rc=255。",
                        },
                    },
                },
                {
                    "at": "2026-03-15T20:10:01+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4242,
                        "decision": "DENY",
                        "fault_code": 0,
                        "fault_name": "NONE",
                        "guard_state": 0,
                        "guard_state_name": "UNKNOWN",
                        "source": "openamp_demo_remote_hook_proxy",
                        "transport_status": "ssh_bridge_launch_failed",
                        "protocol_semantics": "not_verified",
                        "note": "远端 bridge 启动失败，rc=255。",
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "current"
            job._timeout_sec = 10.0
            job._output_dir = output_dir
            job._trace_path = trace_path
            job._summary_path = summary_path
            job._runner_log_path = output_dir / "runner.log"
            job._lock = Lock()
            job._final_snapshot = None

            fake_process = Mock()
            fake_process.communicate.return_value = (
                "",
                "socket: Operation not permitted\nssh: connect to host demo-board port 22: failure\n",
            )
            fake_process.returncode = 2
            job._process = fake_process

            job._wait_for_completion()

            snapshot = job._final_snapshot
            assert snapshot is not None
            self.assertEqual(snapshot["status"], "error")
            self.assertEqual(snapshot["status_category"], "host_env_error")
            self.assertIn("当前主机环境禁止建立 SSH socket", snapshot["message"])
            self.assertNotIn("passwordless sudo", snapshot["message"])
            self.assertEqual(snapshot["diagnostics"]["control_hook"]["transport_status"], "ssh_bridge_launch_failed")
            self.assertEqual(snapshot["progress"]["current_stage"], "连接失败")
            self.assertEqual(snapshot["progress"]["stages"][0]["status"], "error")
            self.assertEqual(snapshot["progress"]["stages"][1]["status"], "error")
            self.assertEqual(snapshot["progress"]["stages"][0]["detail"], "远端 bridge 启动失败，rc=255。")
            self.assertEqual(snapshot["progress"]["stages"][1]["detail"], "远端 bridge 启动失败，rc=255。")


if __name__ == "__main__":
    unittest.main()
