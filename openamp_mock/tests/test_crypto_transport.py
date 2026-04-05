from __future__ import annotations

import unittest

from openamp_mock.crypto_guard import CryptoGuard
from openamp_mock.crypto_transport import CryptoTransport
from openamp_mock.demo import (
    MockSession,
    run_allow_scenario,
    run_input_contract_deny_scenario,
    run_timeout_scenario,
    run_wrong_sha_deny_scenario,
)
from openamp_mock.guard import SafetyGuard
from openamp_mock.orchestrator import Orchestrator
from openamp_mock.protocol import FORMAL_TRUSTED_CURRENT_SHA, JobSpec, MessageType, build_message
from openamp_mock.transport import MockTransport


class CryptoTransportTest(unittest.TestCase):
    def test_encrypt_and_decrypt_roundtrip(self) -> None:
        guard = CryptoGuard(shared_secret=b"k" * 32)
        message = build_message(
            msg_type=MessageType.JOB_REQ,
            seq=1,
            job_id=42,
            payload={"expected_sha256": FORMAL_TRUSTED_CURRENT_SHA},
        )
        encrypted = guard.encrypt(message)
        self.assertEqual(encrypted.header.msg_type, int(MessageType.ENCRYPTED_CTRL))
        decrypted = guard.decrypt(encrypted)
        self.assertEqual(decrypted.header.msg_type, int(MessageType.JOB_REQ))
        self.assertEqual(decrypted.payload, message.payload)

    def test_mock_closed_loop_still_passes_with_crypto_transport(self) -> None:
        transport = CryptoTransport(MockTransport(), CryptoGuard(shared_secret=b"s" * 32))
        guard = SafetyGuard(trusted_sha256=FORMAL_TRUSTED_CURRENT_SHA)
        orchestrator = Orchestrator()

        now_ms = 0
        job = JobSpec(job_id=7001, expected_sha256=FORMAL_TRUSTED_CURRENT_SHA, flags="payload")
        orchestrator.submit_job(job, now_ms, transport)

        while transport.has_pending():
            while transport.has_linux_pending():
                guard.handle(transport.pop_for_guard(), now_ms, transport)
            while transport.has_guard_pending():
                orchestrator.handle(transport.pop_for_linux(), now_ms)

        self.assertEqual(orchestrator.state.value, "ALLOWED")
        self.assertEqual(guard.state.value, "JOB_ACTIVE")
        self.assertGreater(transport.stats["encrypt_tx"], 0)
        self.assertGreater(transport.stats["decrypt_rx"], 0)

    def test_existing_plain_mock_scenario_unchanged(self) -> None:
        _, result = run_allow_scenario()
        self.assertTrue(result["passed"])

    def test_mock_session_can_enable_crypto_transport(self) -> None:
        session = MockSession(use_crypto_transport=True)
        job = JobSpec(job_id=7002, expected_sha256=FORMAL_TRUSTED_CURRENT_SHA, flags="payload")
        session.orchestrator.submit_job(job, session.now_ms, session.transport)
        session.pump()
        self.assertEqual(session.orchestrator.state.value, "ALLOWED")
        self.assertEqual(session.guard.state.value, "JOB_ACTIVE")

    def test_all_core_scenarios_pass_with_crypto_transport(self) -> None:
        for runner in (
            run_allow_scenario,
            run_wrong_sha_deny_scenario,
            run_input_contract_deny_scenario,
            run_timeout_scenario,
        ):
            _, result = runner(use_crypto_transport=True)
            self.assertTrue(result["passed"])
            self.assertTrue(result["control_plane_encrypted"])
            crypto_stats = result["control_plane_crypto_stats"]
            self.assertGreater(crypto_stats["encrypt_tx"], 0)


if __name__ == "__main__":
    unittest.main()
