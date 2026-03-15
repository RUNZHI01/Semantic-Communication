from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from threading import Lock
import textwrap
import unittest
from unittest.mock import Mock


DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parents[2]
LEGACY_RUNNER = REPO_ROOT / "session_bootstrap" / "scripts" / "run_remote_legacy_tvm_compat.sh"

if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import inference_runner  # noqa: E402
from inference_runner import LiveRemoteReconstructionJob, PROJECT_ROOT  # noqa: E402


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)


class LegacyCompatRunnerContractTest(unittest.TestCase):
    def test_local_runner_emits_json_summary_after_legacy_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_python_root = temp_dir / "fake_pythonpath"
            fake_tvm_dir = fake_python_root / "tvm"
            fake_tvm_dir.mkdir(parents=True)

            write_file(
                fake_tvm_dir / "__init__.py",
                textwrap.dedent(
                    """\
                    from . import relax, runtime


                    def cpu(index=0):
                        return ("cpu", index)
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "runtime.py",
                textwrap.dedent(
                    """\
                    class _Module:
                        type_key = "library"


                    def load_module(path):
                        return _Module()
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "relax.py",
                textwrap.dedent(
                    """\
                    class VirtualMachine:
                        def __init__(self, lib, dev):
                            self.lib = lib
                            self.dev = dev
                    """
                ),
            )

            fake_python = temp_dir / "fake_python.sh"
            write_executable(
                fake_python,
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    export PYTHONPATH="{fake_python_root}${{PYTHONPATH:+:${{PYTHONPATH}}}}"
                    exec python3 "$@"
                    """
                ),
            )

            jscc_dir = temp_dir / "jscc"
            jscc_dir.mkdir()
            artifact_dir = jscc_dir / "tvm_tune_logs"
            artifact_dir.mkdir()
            artifact_path = artifact_dir / "optimized_model.so"
            artifact_bytes = b"legacy-openamp-artifact"
            artifact_path.write_bytes(artifact_bytes)
            expected_sha = hashlib.sha256(artifact_bytes).hexdigest()

            write_file(
                jscc_dir / "tvm_002.py",
                textwrap.dedent(
                    """\
                    import argparse
                    from pathlib import Path


                    parser = argparse.ArgumentParser()
                    parser.add_argument("--input_dir", required=True)
                    parser.add_argument("--output_dir", required=True)
                    parser.add_argument("--snr", required=True)
                    parser.add_argument("--batch_size", required=True)
                    args = parser.parse_args()

                    input_files = sorted(path for path in Path(args.input_dir).iterdir() if path.is_file())
                    recon_dir = Path(args.output_dir) / "reconstructions"
                    recon_dir.mkdir(parents=True, exist_ok=True)
                    for input_path in input_files:
                        save_path = recon_dir / f"{input_path.stem}_recon.png"
                        save_path.write_bytes(b"fake-png")
                        print("批量推理时间（1 个样本）: 0.012 秒")
                        print(f"重构图像保存至: {save_path}")
                    print("处理完成")
                    """
                ),
            )

            input_dir = temp_dir / "inputs"
            input_dir.mkdir()
            (input_dir / "sample_000.pt").write_bytes(b"latent-000")
            (input_dir / "sample_001.npy").write_bytes(b"latent-001")
            output_base = temp_dir / "outputs"
            output_base.mkdir()

            env = os.environ.copy()
            env.update(
                {
                    "REMOTE_MODE": "local",
                    "REMOTE_TVM_PYTHON": str(fake_python),
                    "REMOTE_JSCC_DIR": str(jscc_dir),
                    "REMOTE_INPUT_DIR": str(input_dir),
                    "REMOTE_OUTPUT_BASE": str(output_base),
                    "REMOTE_SNR_BASELINE": "10",
                    "REMOTE_BATCH_BASELINE": "1",
                    "REMOTE_BASELINE_ARTIFACT": str(artifact_path),
                    "INFERENCE_BASELINE_EXPECTED_SHA256": expected_sha,
                }
            )

            result = subprocess.run(
                ["bash", str(LEGACY_RUNNER), "--variant", "baseline", "--max-inputs", "1"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            self.assertGreaterEqual(len(lines), 3)
            self.assertIn("批量推理时间（1 个样本）", result.stdout)

            summary = json.loads(lines[-1])
            self.assertEqual(summary["variant"], "baseline")
            self.assertEqual(summary["artifact_path"], str(artifact_path))
            self.assertEqual(summary["artifact_sha256"], expected_sha)
            self.assertEqual(summary["artifact_sha256_expected"], expected_sha)
            self.assertTrue(summary["artifact_sha256_match"])
            self.assertEqual(summary["output_count"], 1)
            self.assertEqual(summary["processed_count"], 1)
            self.assertEqual(summary["input_count"], 1)
            self.assertEqual(summary["available_input_count"], 2)
            self.assertEqual(summary["run_count"], 1)
            self.assertEqual(summary["run_samples_ms"], [12.0])
            self.assertEqual(summary["run_median_ms"], 12.0)
            self.assertEqual(summary["run_mean_ms"], 12.0)
            self.assertEqual(summary["load_ms"], 0.0)
            self.assertEqual(summary["vm_init_ms"], 0.0)
            self.assertEqual(summary["max_inputs"], 1)
            self.assertEqual(summary["parser"], "legacy_latency_lines")
            self.assertEqual(summary["save_format"], "png")
            self.assertTrue(summary["output_dir"].endswith("/reconstructions"))

    def test_local_runner_respects_100_image_cap_and_ignores_stale_outputs_in_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_python_root = temp_dir / "fake_pythonpath"
            fake_tvm_dir = fake_python_root / "tvm"
            fake_tvm_dir.mkdir(parents=True)

            write_file(
                fake_tvm_dir / "__init__.py",
                textwrap.dedent(
                    """\
                    from . import relax, runtime


                    def cpu(index=0):
                        return ("cpu", index)
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "runtime.py",
                textwrap.dedent(
                    """\
                    class _Module:
                        type_key = "library"


                    def load_module(path):
                        return _Module()
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "relax.py",
                textwrap.dedent(
                    """\
                    class VirtualMachine:
                        def __init__(self, lib, dev):
                            self.lib = lib
                            self.dev = dev
                    """
                ),
            )

            fake_python = temp_dir / "fake_python.sh"
            write_executable(
                fake_python,
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    export PYTHONPATH="{fake_python_root}${{PYTHONPATH:+:${{PYTHONPATH}}}}"
                    exec python3 "$@"
                    """
                ),
            )

            jscc_dir = temp_dir / "jscc"
            jscc_dir.mkdir()
            artifact_dir = jscc_dir / "tvm_tune_logs"
            artifact_dir.mkdir()
            artifact_path = artifact_dir / "optimized_model.so"
            artifact_bytes = b"legacy-openamp-artifact"
            artifact_path.write_bytes(artifact_bytes)
            expected_sha = hashlib.sha256(artifact_bytes).hexdigest()

            write_file(
                jscc_dir / "tvm_002.py",
                textwrap.dedent(
                    """\
                    import argparse
                    from pathlib import Path


                    parser = argparse.ArgumentParser()
                    parser.add_argument("--input_dir", required=True)
                    parser.add_argument("--output_dir", required=True)
                    parser.add_argument("--snr", required=True)
                    parser.add_argument("--batch_size", required=True)
                    args = parser.parse_args()

                    input_files = sorted(path for path in Path(args.input_dir).iterdir() if path.is_file())
                    recon_dir = Path(args.output_dir) / "reconstructions"
                    recon_dir.mkdir(parents=True, exist_ok=True)
                    for input_path in input_files:
                        save_path = recon_dir / f"{input_path.stem}_recon.png"
                        save_path.write_bytes(b"fake-png")
                        print("批量推理时间（1 个样本）: 0.012 秒")
                    print("处理完成")
                    """
                ),
            )

            input_dir = temp_dir / "inputs"
            input_dir.mkdir()
            for index in range(105):
                suffix = ".pt" if index % 2 == 0 else ".npy"
                (input_dir / f"sample_{index:03d}{suffix}").write_bytes(f"latent-{index:03d}".encode("utf-8"))
            output_base = temp_dir / "outputs"
            output_base.mkdir()
            stale_recon_dir = output_base / "inference_benchmark_baseline" / "reconstructions"
            stale_recon_dir.mkdir(parents=True)
            stale_output = stale_recon_dir / "stale_extra.png"
            stale_output.write_bytes(b"stale-png")
            os.utime(stale_output, (1, 1))

            env = os.environ.copy()
            env.update(
                {
                    "REMOTE_MODE": "local",
                    "REMOTE_TVM_PYTHON": str(fake_python),
                    "REMOTE_JSCC_DIR": str(jscc_dir),
                    "REMOTE_INPUT_DIR": str(input_dir),
                    "REMOTE_OUTPUT_BASE": str(output_base),
                    "REMOTE_SNR_BASELINE": "10",
                    "REMOTE_BATCH_BASELINE": "1",
                    "REMOTE_BASELINE_ARTIFACT": str(artifact_path),
                    "INFERENCE_BASELINE_EXPECTED_SHA256": expected_sha,
                }
            )

            result = subprocess.run(
                ["bash", str(LEGACY_RUNNER), "--variant", "baseline", "--max-inputs", "300"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads([line.strip() for line in result.stdout.splitlines() if line.strip()][-1])
            self.assertEqual(summary["variant"], "baseline")
            self.assertEqual(summary["artifact_path"], str(artifact_path))
            self.assertEqual(summary["artifact_sha256"], expected_sha)
            self.assertEqual(summary["artifact_sha256_expected"], expected_sha)
            self.assertTrue(summary["artifact_sha256_match"])
            self.assertEqual(summary["available_input_count"], 105)
            self.assertEqual(summary["input_count"], 105)
            self.assertEqual(summary["processed_count"], 105)
            self.assertEqual(summary["run_count"], 105)
            self.assertEqual(len(summary["run_samples_ms"]), 105)
            self.assertEqual(summary["output_count"], 105)
            self.assertEqual(summary["max_inputs"], 300)
            self.assertEqual(summary["save_format"], "png")
            self.assertTrue(summary["output_dir"].endswith("/reconstructions"))

    def test_legacy_runner_defaults_to_demo_100_image_cap_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_python_root = temp_dir / "fake_pythonpath"
            fake_tvm_dir = fake_python_root / "tvm"
            fake_tvm_dir.mkdir(parents=True)

            write_file(
                fake_tvm_dir / "__init__.py",
                textwrap.dedent(
                    """\
                    from . import relax, runtime


                    def cpu(index=0):
                        return ("cpu", index)
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "runtime.py",
                textwrap.dedent(
                    """\
                    class _Module:
                        type_key = "library"


                    def load_module(path):
                        return _Module()
                    """
                ),
            )
            write_file(
                fake_tvm_dir / "relax.py",
                textwrap.dedent(
                    """\
                    class VirtualMachine:
                        def __init__(self, lib, dev):
                            self.lib = lib
                            self.dev = dev
                    """
                ),
            )

            fake_python = temp_dir / "fake_python.sh"
            write_executable(
                fake_python,
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    export PYTHONPATH="{fake_python_root}${{PYTHONPATH:+:${{PYTHONPATH}}}}"
                    exec python3 "$@"
                    """
                ),
            )

            jscc_dir = temp_dir / "jscc"
            jscc_dir.mkdir()
            artifact_dir = jscc_dir / "tvm_tune_logs"
            artifact_dir.mkdir()
            artifact_path = artifact_dir / "optimized_model.so"
            artifact_bytes = b"legacy-openamp-artifact"
            artifact_path.write_bytes(artifact_bytes)
            expected_sha = hashlib.sha256(artifact_bytes).hexdigest()

            write_file(
                jscc_dir / "tvm_002.py",
                textwrap.dedent(
                    """\
                    import argparse
                    from pathlib import Path


                    parser = argparse.ArgumentParser()
                    parser.add_argument("--input_dir", required=True)
                    parser.add_argument("--output_dir", required=True)
                    parser.add_argument("--snr", required=True)
                    parser.add_argument("--batch_size", required=True)
                    args = parser.parse_args()

                    input_files = sorted(path for path in Path(args.input_dir).iterdir() if path.is_file())
                    recon_dir = Path(args.output_dir) / "reconstructions"
                    recon_dir.mkdir(parents=True, exist_ok=True)
                    for input_path in input_files:
                        (recon_dir / f"{input_path.stem}_recon.png").write_bytes(b"fake-png")
                        print("批量推理时间（1 个样本）: 0.010 秒")
                    """
                ),
            )

            input_dir = temp_dir / "inputs"
            input_dir.mkdir()
            for index in range(105):
                suffix = ".pt" if index % 2 == 0 else ".npy"
                (input_dir / f"sample_{index:03d}{suffix}").write_bytes(f"latent-{index:03d}".encode("utf-8"))
            output_base = temp_dir / "outputs"
            output_base.mkdir()

            env = os.environ.copy()
            env.update(
                {
                    "REMOTE_MODE": "local",
                    "REMOTE_TVM_PYTHON": str(fake_python),
                    "REMOTE_JSCC_DIR": str(jscc_dir),
                    "REMOTE_INPUT_DIR": str(input_dir),
                    "REMOTE_OUTPUT_BASE": str(output_base),
                    "REMOTE_SNR_BASELINE": "10",
                    "REMOTE_BATCH_BASELINE": "1",
                    "REMOTE_BASELINE_ARTIFACT": str(artifact_path),
                    "INFERENCE_BASELINE_EXPECTED_SHA256": expected_sha,
                    "OPENAMP_DEMO_MODE": "1",
                    "OPENAMP_DEMO_MAX_INPUTS": "300",
                }
            )

            result = subprocess.run(
                ["bash", str(LEGACY_RUNNER), "--variant", "baseline"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads([line.strip() for line in result.stdout.splitlines() if line.strip()][-1])
            self.assertEqual(summary["max_inputs"], 300)
            self.assertEqual(summary["input_count"], 105)
            self.assertEqual(summary["processed_count"], 105)
            self.assertEqual(summary["output_count"], 105)
            self.assertEqual(summary["available_input_count"], 105)


class LegacyBaselineLiveConsumptionTest(unittest.TestCase):
    def test_live_job_accepts_legacy_summary_json_as_success(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir_name:
            output_dir = Path(temp_dir_name)
            trace_path = output_dir / "control_trace.jsonl"
            summary_path = output_dir / "wrapper_summary.json"
            runner_log_path = output_dir / "runner.log"

            trace_events = [
                {
                    "at": "2026-03-15T21:00:00+0800",
                    "phase": "STATUS_REQ",
                    "payload": {"job_id": 4242},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "STATUS_REQ",
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
                    "at": "2026-03-15T21:00:01+0800",
                    "phase": "JOB_REQ",
                    "payload": {"job_id": 4242, "expected_sha256": "b" * 64},
                    "hook_result": {
                        "returncode": 0,
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "ALLOW",
                            "guard_state_name": "JOB_ACTIVE",
                            "fault_name": "NONE",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                        },
                    },
                },
                {
                    "at": "2026-03-15T21:00:01+0800",
                    "phase": "JOB_ACK",
                    "payload": {
                        "job_id": 4242,
                        "decision": "ALLOW",
                        "guard_state_name": "JOB_ACTIVE",
                        "fault_name": "NONE",
                    },
                },
                {
                    "at": "2026-03-15T21:00:03+0800",
                    "phase": "JOB_DONE",
                    "payload": {
                        "job_id": 4242,
                        "elapsed_ms": 2000,
                        "result_code": 0,
                        "runner_exit_code": 0,
                        "timed_out": False,
                    },
                },
            ]
            trace_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in trace_events) + "\n",
                encoding="utf-8",
            )
            summary_path.write_text(
                json.dumps({"result": "success"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            runner_summary = {
                "variant": "baseline",
                "artifact_path": "/tmp/baseline/optimized_model.so",
                "artifact_sha256": "b" * 64,
                "artifact_sha256_expected": "b" * 64,
                "artifact_sha256_match": True,
                "output_dir": "/tmp/openamp_demo_hook/4242/inference_benchmark_baseline/reconstructions",
                "output_count": 1,
                "processed_count": 1,
                "input_count": 1,
                "available_input_count": 1,
                "load_ms": 0.0,
                "vm_init_ms": 0.0,
                "run_count": 1,
                "run_samples_ms": [12.0],
                "run_median_ms": 12.0,
                "run_mean_ms": 12.0,
                "run_min_ms": 12.0,
                "run_max_ms": 12.0,
                "run_variance_ms2": 0.0,
                "output_shape": None,
                "output_dtype": None,
                "snr": 10.0,
                "batch_size": 1,
                "save_format": "png",
                "seed": None,
                "max_inputs": 1,
                "parser": "legacy_latency_lines",
            }
            runner_log_path.write_text(
                "[2026-03-15T21:00:00+0800] openamp wrapper start\n"
                "runner_cmd=bash ./session_bootstrap/scripts/run_remote_legacy_tvm_compat.sh --variant baseline --max-inputs 1\n"
                "[legacy-compat] variant=baseline script=tvm_002.py output_dir=/tmp/out snr=10 batch_size=1 max_inputs=1\n"
                "批量推理时间（1 个样本）: 0.012 秒\n"
                + json.dumps(runner_summary, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )

            job = LiveRemoteReconstructionJob.__new__(LiveRemoteReconstructionJob)
            job.job_id = "4242"
            job.variant = "baseline"
            job._timeout_sec = 10.0
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
            self.assertEqual(snapshot["execution_mode"], "live")
            self.assertEqual(snapshot["status_category"], "success")
            self.assertEqual(snapshot["runner_summary"]["parser"], "legacy_latency_lines")
            self.assertEqual(snapshot["runner_summary"]["run_median_ms"], 12.0)
            self.assertEqual(snapshot["runner_summary"]["artifact_sha256"], "b" * 64)
            self.assertEqual(snapshot["progress"]["completed_count"], 1)
            self.assertEqual(snapshot["progress"]["expected_count"], 1)
            self.assertEqual(snapshot["progress"]["count_source"], "runner_summary.processed_count")
            self.assertEqual(snapshot["progress"]["stages"][3]["status"], "done")


if __name__ == "__main__":
    unittest.main()
