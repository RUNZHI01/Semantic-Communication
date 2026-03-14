from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from openamp_mock.protocol import Decision, FaultCode, FORMAL_TRUSTED_CURRENT_SHA, MessageType


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_PATH = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_rpmsg_bridge.py"
BRIDGE_SPEC = importlib.util.spec_from_file_location("openamp_rpmsg_bridge", BRIDGE_PATH)
if BRIDGE_SPEC is None or BRIDGE_SPEC.loader is None:
    raise RuntimeError(f"failed to load bridge module from {BRIDGE_PATH}")
bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
BRIDGE_SPEC.loader.exec_module(bridge)


class OpenAmpRpmsgBridgeTest(unittest.TestCase):
    def test_build_job_req_payload_encodes_binary_wire_shape(self) -> None:
        payload = bridge.build_job_req_payload_from_hook(
            {
                "phase": "JOB_REQ",
                "payload": {
                    "job_id": 42,
                    "expected_sha256": FORMAL_TRUSTED_CURRENT_SHA,
                    "deadline_ms": 300000,
                    "expected_outputs": 300,
                    "job_flags": "reconstruction",
                },
            }
        )

        parsed = bridge.parse_job_req_payload(payload)
        self.assertTrue(parsed["parsed"])
        self.assertEqual(parsed["expected_sha256_hex"], FORMAL_TRUSTED_CURRENT_SHA)
        self.assertEqual(parsed["deadline_ms"], 300000)
        self.assertEqual(parsed["expected_outputs"], 300)
        self.assertEqual(parsed["flags"], 2)
        self.assertEqual(parsed["flag_name"], "reconstruction")

    def test_build_job_req_payload_maps_unknown_flag_to_zero(self) -> None:
        payload = bridge.build_job_req_payload_from_hook(
            {
                "phase": "JOB_REQ",
                "payload": {
                    "job_id": 99,
                    "expected_sha256": FORMAL_TRUSTED_CURRENT_SHA,
                    "deadline_ms": 1,
                    "expected_outputs": 1,
                    "job_flags": "future_flag",
                },
            }
        )

        parsed = bridge.parse_job_req_payload(payload)
        self.assertTrue(parsed["parsed"])
        self.assertEqual(parsed["flags"], 0)
        self.assertEqual(parsed["flag_name"], "unknown_0x0")

    def test_parse_job_ack_frame_and_classify_echo(self) -> None:
        ack_frame = bridge.build_frame(
            msg_type=MessageType.JOB_ACK,
            seq=7,
            job_id=1234,
            payload=bridge.JOB_ACK_STRUCT.pack(int(Decision.ALLOW), int(FaultCode.NONE), 2),
        )
        parsed = bridge.parse_frame(ack_frame)
        self.assertTrue(parsed["job_ack"]["parsed"])
        self.assertEqual(parsed["job_ack"]["decision_name"], "ALLOW")
        self.assertEqual(parsed["job_ack"]["guard_state_name"], "JOB_ACTIVE")

        req_frame = bridge.build_frame(
            msg_type=MessageType.JOB_REQ,
            seq=8,
            job_id=1234,
            payload=bridge.build_job_req_payload_from_hook(
                {
                    "phase": "JOB_REQ",
                    "payload": {
                        "job_id": 1234,
                        "expected_sha256": FORMAL_TRUSTED_CURRENT_SHA,
                        "deadline_ms": 500,
                        "expected_outputs": 1,
                        "job_flags": "smoke",
                    },
                }
            ),
        )
        summary = bridge.classify_job_probe(
            phase="JOB_REQ",
            tx_bytes=req_frame,
            rx_bytes=req_frame,
            rx_timeout=False,
        )
        self.assertEqual(summary["decision"], "DENY")
        self.assertEqual(summary["source"], "linux_bridge_transport_guard")
        self.assertEqual(summary["transport_status"], "transport_echo_only")


if __name__ == "__main__":
    unittest.main()
