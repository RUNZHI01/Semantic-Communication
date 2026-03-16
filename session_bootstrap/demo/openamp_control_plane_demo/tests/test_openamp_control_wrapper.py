from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import openamp_control_wrapper  # noqa: E402


class OpenAMPControlWrapperTest(unittest.TestCase):
    def test_emit_event_records_hook_timeout_instead_of_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "control_trace.jsonl"
            timeout_error = subprocess.TimeoutExpired(
                cmd=["bash", "-lc", "echo hook"],
                timeout=7.5,
                output="",
            )
            timeout_error.stderr = "hook timed out\n"

            with patch(
                "openamp_control_wrapper.subprocess.run",
                side_effect=timeout_error,
            ):
                result = openamp_control_wrapper.emit_event(
                    trace_path=trace_path,
                    phase="HEARTBEAT",
                    payload={"job_id": 101},
                    transport="hook",
                    hook_cmd="echo hook",
                    hook_timeout_sec=7.5,
                )
            event = json.loads(trace_path.read_text(encoding="utf-8").strip())

        self.assertIsNone(result["returncode"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["timeout_sec"], 7.5)
        self.assertEqual(result["stderr"], "hook timed out\n")
        self.assertEqual(
            result["response"],
            {
                "phase": "HEARTBEAT",
                "source": "openamp_control_wrapper",
                "transport_status": "hook_timeout",
                "protocol_semantics": "not_verified",
                "note": "HEARTBEAT control hook timed out after 7.5s.",
            },
        )
        self.assertTrue(event["hook_result"]["timed_out"])

    def test_main_keeps_duplicate_job_id_denial_visible_without_retrying(self) -> None:
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
                admission_mode="legacy_sha",
                signed_manifest_file="",
                signed_manifest_public_key="",
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
                return {}

            stdout = io.StringIO()
            with (
                patch("openamp_control_wrapper.parse_args", return_value=args),
                patch(
                    "openamp_control_wrapper.resolve_expected_sha256",
                    return_value=("a" * 64, None, "--expected-sha256"),
                ),
                patch("openamp_control_wrapper.emit_event", side_effect=fake_emit_event),
                contextlib.redirect_stdout(stdout),
            ):
                result = openamp_control_wrapper.main()
            manifest = json.loads((output_dir / "job_manifest.json").read_text(encoding="utf-8"))
            summary = json.loads(stdout.getvalue().strip())

        self.assertEqual(result, 2)
        self.assertEqual(
            emit_calls,
            [
                ("STATUS_REQ", 101),
                ("JOB_REQ", 101),
                ("JOB_ACK", 101),
            ],
        )
        self.assertEqual(manifest["job_id"], 101)
        self.assertNotIn("requested_job_id", manifest)
        self.assertNotIn("retry_count", manifest)
        self.assertNotIn("retry_reason", manifest)
        self.assertEqual(summary["job_id"], 101)
        self.assertEqual(summary["result"], "denied_by_control_hook")


if __name__ == "__main__":
    unittest.main()
