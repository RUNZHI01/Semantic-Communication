from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "session_bootstrap" / "scripts"
PYTHON_RUNNER = SCRIPTS_DIR / "big_little_pipeline.py"
WRAPPER_RUNNER = SCRIPTS_DIR / "run_big_little_pipeline.sh"
COMPARE_RUNNER = SCRIPTS_DIR / "run_big_little_compare.sh"


def parse_last_json(stdout: str) -> dict[str, object]:
    for raw in reversed(stdout.splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise AssertionError(f"no JSON payload found in output:\n{stdout}")


def write_mock_inputs(input_dir: Path, count: int) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        array = np.full((1, 32, 32, 32), fill_value=index + 1, dtype=np.float32)
        np.save(input_dir / f"sample_{index:03d}.npy", array)


def write_mock_artifact(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"mock-big-little-artifact")


class BigLittlePipelineTest(unittest.TestCase):
    def test_python_runner_dry_run_writes_summary_outputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            input_dir = temp_dir / "inputs"
            output_dir = temp_dir / "outputs"
            summary_json = temp_dir / "summary.json"
            summary_md = temp_dir / "summary.md"
            write_mock_artifact(artifact_path)
            write_mock_inputs(input_dir, count=3)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(PYTHON_RUNNER),
                    "--artifact-path",
                    str(artifact_path),
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--snr",
                    "12",
                    "--batch-size",
                    "1",
                    "--variant",
                    "current",
                    "--dry-run",
                    "--allow-missing-affinity",
                    "--big-cores",
                    "0",
                    "--little-cores",
                    "1",
                    "--backend",
                    "threads",
                    "--max-inputs",
                    "3",
                    "--summary-json",
                    str(summary_json),
                    "--summary-md",
                    str(summary_md),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = parse_last_json(completed.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["processed_count"], 3)
            self.assertEqual(payload["output_count"], 3)
            self.assertTrue(summary_json.is_file())
            self.assertTrue(summary_md.is_file())
            self.assertTrue((output_dir / "reconstructions").is_dir())

    def test_wrapper_local_env_dry_run_emits_report(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "artifact" / "optimized_model.so"
            input_dir = temp_dir / "inputs"
            output_base = temp_dir / "remote_outputs"
            log_dir = temp_dir / "logs"
            report_dir = temp_dir / "reports"
            env_file = temp_dir / "local.env"
            write_mock_artifact(artifact_path)
            write_mock_inputs(input_dir, count=4)
            env_file.write_text(
                "\n".join(
                    [
                        f"LOG_DIR={shlex.quote(str(log_dir))}",
                        f"REPORT_DIR={shlex.quote(str(report_dir))}",
                        "REMOTE_MODE=local",
                        f"REMOTE_TVM_PYTHON={shlex.quote(sys.executable)}",
                        f"REMOTE_INPUT_DIR={shlex.quote(str(input_dir))}",
                        f"REMOTE_OUTPUT_BASE={shlex.quote(str(output_base))}",
                        f"REMOTE_CURRENT_ARTIFACT={shlex.quote(str(artifact_path))}",
                        "REMOTE_SNR_CURRENT=12",
                        "REMOTE_BATCH_CURRENT=1",
                        "BIG_LITTLE_BIG_CORES=0",
                        "BIG_LITTLE_LITTLE_CORES=1",
                        "BIG_LITTLE_BACKEND=threads",
                        "BIG_LITTLE_ALLOW_MISSING_AFFINITY=1",
                        "BIG_LITTLE_INPUT_QUEUE_SIZE=2",
                        "BIG_LITTLE_OUTPUT_QUEUE_SIZE=2",
                        "BIG_LITTLE_DRY_RUN=1",
                        "BIG_LITTLE_MOCK_INFER_MS=5",
                        "BIG_LITTLE_MAX_INPUTS=4",
                        "BIG_LITTLE_OUTPUT_PREFIX=unit_big_little_outputs",
                        "BIG_LITTLE_REPORT_PREFIX=unit_big_little_report",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    "bash",
                    str(WRAPPER_RUNNER),
                    "--env",
                    str(env_file),
                    "--variant",
                    "current",
                    "--run-id",
                    "unit_big_little_wrapper",
                    "--allow-overwrite",
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = parse_last_json(completed.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["pipeline"]["status"], "ok")
            self.assertEqual(payload["pipeline"]["processed_count"], 4)
            report_json = report_dir / "unit_big_little_wrapper.json"
            report_md = report_dir / "unit_big_little_wrapper.md"
            self.assertTrue(report_json.is_file())
            self.assertTrue(report_md.is_file())

    def test_compare_wrapper_uses_serial_override_and_pipeline_wrapper(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "artifact" / "optimized_model.so"
            input_dir = temp_dir / "inputs"
            output_base = temp_dir / "remote_outputs"
            log_dir = temp_dir / "logs"
            report_dir = temp_dir / "reports"
            env_file = temp_dir / "local.env"
            write_mock_artifact(artifact_path)
            write_mock_inputs(input_dir, count=4)
            env_file.write_text(
                "\n".join(
                    [
                        f"LOG_DIR={shlex.quote(str(log_dir))}",
                        f"REPORT_DIR={shlex.quote(str(report_dir))}",
                        "REMOTE_MODE=local",
                        f"REMOTE_TVM_PYTHON={shlex.quote(sys.executable)}",
                        f"REMOTE_INPUT_DIR={shlex.quote(str(input_dir))}",
                        f"REMOTE_OUTPUT_BASE={shlex.quote(str(output_base))}",
                        f"REMOTE_CURRENT_ARTIFACT={shlex.quote(str(artifact_path))}",
                        "REMOTE_SNR_CURRENT=12",
                        "REMOTE_BATCH_CURRENT=1",
                        "BIG_LITTLE_BIG_CORES=0",
                        "BIG_LITTLE_LITTLE_CORES=1",
                        "BIG_LITTLE_BACKEND=threads",
                        "BIG_LITTLE_ALLOW_MISSING_AFFINITY=1",
                        "BIG_LITTLE_INPUT_QUEUE_SIZE=2",
                        "BIG_LITTLE_OUTPUT_QUEUE_SIZE=2",
                        "BIG_LITTLE_DRY_RUN=1",
                        "BIG_LITTLE_MOCK_INFER_MS=5",
                        "BIG_LITTLE_MAX_INPUTS=4",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            serial_payload = json.dumps(
                {
                    "status": "ok",
                    "load_ms": 5.0,
                    "vm_init_ms": 1.0,
                    "run_samples_ms": [100.0, 100.0, 100.0, 100.0],
                    "processed_count": 4,
                    "run_count": 4,
                }
            )
            serial_cmd = f"printf '%s\\n' {shlex.quote(serial_payload)}"
            pipeline_cmd = "bash ./session_bootstrap/scripts/run_big_little_pipeline.sh --variant current --run-id unit_big_little_compare_pipeline --allow-overwrite"

            completed = subprocess.run(
                [
                    "bash",
                    str(COMPARE_RUNNER),
                    "--env",
                    str(env_file),
                    "--run-id",
                    "unit_big_little_compare",
                    "--serial-cmd",
                    serial_cmd,
                    "--pipeline-cmd",
                    pipeline_cmd,
                    "--allow-overwrite",
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            payload = parse_last_json(completed.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertIn("comparison", payload)
            self.assertIsNotNone(payload["comparison"]["throughput_uplift_pct"])


if __name__ == "__main__":
    unittest.main()
