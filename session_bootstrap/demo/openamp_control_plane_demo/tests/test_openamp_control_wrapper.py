from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import openamp_control_wrapper  # noqa: E402


class OpenAMPControlWrapperTest(unittest.TestCase):
    def test_main_retries_duplicate_job_id_once_with_fresh_control_plane_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            args = openamp_control_wrapper.argparse.Namespace(
                runner_cmd="echo runner",
                output_dir=str(output_dir),
                job_id=101,
                variant="current_reconstruction",
                expected_sha256="",
                trusted_artifact_label="",
                trusted_artifacts_file=str(output_dir / "trusted.json"),
                deadline_ms=300000,
                expected_outputs=300,
                job_flags="reconstruction",
                heartbeat_interval_sec=5.0,
                runner_timeout_sec=0.0,
                transport="hook",
                control_hook_cmd="echo hook",
                control_hook_timeout_sec=5.0,
                dry_run=False,
            )
            emit_calls: list[tuple[str, int]] = []

            def fake_emit_event(*, trace_path, phase, payload, transport, hook_cmd, hook_timeout_sec):  # type: ignore[no-untyped-def]
                emit_calls.append((phase, int(payload.get("job_id", 0) or 0)))
                if phase == "STATUS_REQ":
                    return {
                        "response": {
                            "phase": "STATUS_REQ",
                            "transport_status": "status_resp_received",
                            "protocol_semantics": "implemented",
                        }
                    }
                if phase == "JOB_REQ" and payload["job_id"] == 101:
                    return {
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "DENY",
                            "fault_name": "DUPLICATE_JOB_ID",
                            "guard_state_name": "JOB_ACTIVE",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable JOB_ACK frame from firmware.",
                        }
                    }
                if phase == "JOB_REQ":
                    return {
                        "response": {
                            "phase": "JOB_REQ",
                            "decision": "ALLOW",
                            "fault_name": "NONE",
                            "guard_state_name": "JOB_ACTIVE",
                            "transport_status": "job_ack_received",
                            "protocol_semantics": "implemented",
                            "note": "Received a decodable JOB_ACK frame from firmware.",
                        }
                    }
                return {}

            fake_process = Mock()
            fake_process.poll.side_effect = [0]
            fake_process.returncode = 0

            stdout = io.StringIO()
            with (
                patch("openamp_control_wrapper.parse_args", return_value=args),
                patch(
                    "openamp_control_wrapper.resolve_expected_sha256",
                    return_value=("a" * 64, None, "--expected-sha256"),
                ),
                patch("openamp_control_wrapper.emit_event", side_effect=fake_emit_event),
                patch("openamp_control_wrapper.next_retry_job_id", return_value=202),
                patch("openamp_control_wrapper.subprocess.Popen", return_value=fake_process) as popen_mock,
                patch("openamp_control_wrapper.time.monotonic", side_effect=[0.0, 0.0, 0.0]),
                contextlib.redirect_stdout(stdout),
            ):
                result = openamp_control_wrapper.main()
            manifest = json.loads((output_dir / "job_manifest.json").read_text(encoding="utf-8"))
            summary = json.loads(stdout.getvalue().strip())

        self.assertEqual(result, 0)
        self.assertEqual(
            emit_calls,
            [
                ("STATUS_REQ", 101),
                ("JOB_REQ", 101),
                ("STATUS_REQ", 202),
                ("JOB_REQ", 202),
                ("JOB_ACK", 202),
                ("JOB_DONE", 202),
            ],
        )
        popen_mock.assert_called_once()
        self.assertEqual(manifest["requested_job_id"], 101)
        self.assertEqual(manifest["job_id"], 202)
        self.assertEqual(manifest["retry_count"], 1)
        self.assertEqual(manifest["retry_reason"], "DUPLICATE_JOB_ID")
        self.assertEqual(summary["job_id"], 202)
        self.assertEqual(summary["result"], "success")


if __name__ == "__main__":
    unittest.main()
