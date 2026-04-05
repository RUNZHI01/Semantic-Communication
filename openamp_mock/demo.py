from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
from typing import Callable

from .evidence import write_example_bundle
from .crypto_guard import CryptoGuard
from .crypto_transport import CryptoTransport
from .guard import SafetyGuard
from .orchestrator import Orchestrator
from .protocol import (
    Decision,
    FORMAL_TRUSTED_CURRENT_SHA,
    FaultCode,
    JobSpec,
    fault_tag,
)
from .transport import MockTransport


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    tc_id: str
    fit_id: str | None
    description: str
    injected_fault: str | None
    expected_result: str
    risk_item: str | None


SCENARIOS: dict[str, ScenarioSpec] = {
    "allow": ScenarioSpec(
        name="allow",
        tc_id="TC-001",
        fit_id=None,
        description="合法作业获批并正常完成",
        injected_fault=None,
        expected_result="JOB_ACK(ALLOW) 后完成 JOB_DONE(success)，guard 返回 READY。",
        risk_item=None,
    ),
    "deny_sha": ScenarioSpec(
        name="deny_sha",
        tc_id="TC-003",
        fit_id="FIT-01",
        description="错误 trusted current SHA 被前置拒绝",
        injected_fault="提交与 trusted current 不一致的 expected_sha256。",
        expected_result="收到 JOB_ACK(DENY, F001)，不进入 TVM 执行。",
        risk_item="未知 artifact 执行风险",
    ),
    "deny_input": ScenarioSpec(
        name="deny_input",
        tc_id="TC-004",
        fit_id="FIT-02",
        description="输入契约违规被前置拒绝",
        injected_fault="构造 batch=4，触发固定 batch=1 契约拒绝。",
        expected_result="收到 JOB_ACK(DENY, F002)，guard 记录输入契约故障。",
        risk_item="输入契约违规风险",
    ),
    "timeout": ScenarioSpec(
        name="timeout",
        tc_id="TC-006",
        fit_id="FIT-03",
        description="heartbeat 超时触发 SAFE_STOP",
        injected_fault="合法作业启动后故意停止 heartbeat。",
        expected_result="guard 触发 SAFE_STOP(F003) 并进入 FAULT_LATCHED。",
        risk_item="主控失活风险",
    ),
}


class MockSession:
    def __init__(
        self,
        trusted_sha256: str = FORMAL_TRUSTED_CURRENT_SHA,
        *,
        use_crypto_transport: bool = False,
        shared_secret: bytes = b"openamp-ctrl-plane-shared-secret-32",
    ) -> None:
        base_transport = MockTransport()
        if use_crypto_transport:
            self.transport = CryptoTransport(
                base_transport,
                CryptoGuard(shared_secret=shared_secret[:32]),
            )
        else:
            self.transport = base_transport
        self.guard = SafetyGuard(trusted_sha256=trusted_sha256)
        self.orchestrator = Orchestrator()
        self.now_ms = 0

    def pump(self) -> None:
        while self.transport.has_pending():
            while self.transport.has_linux_pending():
                message = self.transport.pop_for_guard()
                self.guard.handle(message, self.now_ms, self.transport)
            while self.transport.has_guard_pending():
                message = self.transport.pop_for_linux()
                self.orchestrator.handle(message, self.now_ms)

    def advance(self, delta_ms: int) -> None:
        self.now_ms += delta_ms
        self.guard.check_timeouts(self.now_ms, self.transport)
        self.pump()

    def reset_guard(self) -> None:
        self.orchestrator.send_reset(self.now_ms, self.transport)
        self.pump()


def run_allow_scenario(*, use_crypto_transport: bool = False) -> tuple[MockSession, dict[str, object]]:
    spec = SCENARIOS["allow"]
    session = MockSession(use_crypto_transport=use_crypto_transport)
    job = JobSpec(job_id=1001, expected_sha256=FORMAL_TRUSTED_CURRENT_SHA, flags="payload")
    session.orchestrator.submit_job(job, session.now_ms, session.transport)
    session.pump()
    session.advance(100)
    session.orchestrator.send_heartbeat(
        now_ms=session.now_ms,
        transport=session.transport,
        elapsed_ms=100,
        completed_outputs=0,
        progress_x100=5000,
    )
    session.pump()
    session.advance(100)
    session.orchestrator.send_heartbeat(
        now_ms=session.now_ms,
        transport=session.transport,
        elapsed_ms=200,
        completed_outputs=1,
        progress_x100=10000,
    )
    session.pump()
    session.orchestrator.finish_job(
        now_ms=session.now_ms,
        transport=session.transport,
        success=True,
        output_count=1,
    )
    session.pump()
    session.orchestrator.request_status(session.now_ms, session.transport)
    session.pump()
    return session, _result_from_session(spec, session)


def run_wrong_sha_deny_scenario(*, use_crypto_transport: bool = False) -> tuple[MockSession, dict[str, object]]:
    spec = SCENARIOS["deny_sha"]
    session = MockSession(use_crypto_transport=use_crypto_transport)
    job = JobSpec(
        job_id=1002,
        expected_sha256="deadbeef" * 8,
        artifact_sha_actual=FORMAL_TRUSTED_CURRENT_SHA,
        flags="payload",
    )
    session.orchestrator.submit_job(job, session.now_ms, session.transport)
    session.pump()
    session.orchestrator.request_status(session.now_ms, session.transport)
    session.pump()
    return session, _result_from_session(spec, session)


def run_input_contract_deny_scenario(*, use_crypto_transport: bool = False) -> tuple[MockSession, dict[str, object]]:
    spec = SCENARIOS["deny_input"]
    session = MockSession(use_crypto_transport=use_crypto_transport)
    job = JobSpec(
        job_id=1003,
        expected_sha256=FORMAL_TRUSTED_CURRENT_SHA,
        input_shape=(4, 32, 32, 32),
        flags="payload",
    )
    session.orchestrator.submit_job(job, session.now_ms, session.transport)
    session.pump()
    session.orchestrator.request_status(session.now_ms, session.transport)
    session.pump()
    return session, _result_from_session(spec, session)


def run_timeout_scenario(*, use_crypto_transport: bool = False) -> tuple[MockSession, dict[str, object]]:
    spec = SCENARIOS["timeout"]
    session = MockSession(use_crypto_transport=use_crypto_transport)
    job = JobSpec(job_id=1004, expected_sha256=FORMAL_TRUSTED_CURRENT_SHA, flags="payload")
    session.orchestrator.submit_job(job, session.now_ms, session.transport)
    session.pump()
    session.advance(100)
    session.orchestrator.send_heartbeat(
        now_ms=session.now_ms,
        transport=session.transport,
        elapsed_ms=100,
        completed_outputs=0,
        progress_x100=2500,
    )
    session.pump()
    session.advance(300)
    session.orchestrator.finish_job(
        now_ms=session.now_ms,
        transport=session.transport,
        success=False,
        output_count=0,
    )
    session.pump()
    session.orchestrator.request_status(session.now_ms, session.transport)
    session.pump()
    return session, _result_from_session(spec, session)


def run_named_scenarios(
    names: list[str],
    *,
    use_crypto_transport: bool = False,
) -> tuple[list[MockSession], list[dict[str, object]]]:
    runners: dict[str, Callable[[], tuple[MockSession, dict[str, object]]]] = {
        "allow": lambda: run_allow_scenario(use_crypto_transport=use_crypto_transport),
        "deny_sha": lambda: run_wrong_sha_deny_scenario(use_crypto_transport=use_crypto_transport),
        "deny_input": lambda: run_input_contract_deny_scenario(use_crypto_transport=use_crypto_transport),
        "timeout": lambda: run_timeout_scenario(use_crypto_transport=use_crypto_transport),
    }
    sessions: list[MockSession] = []
    results: list[dict[str, object]] = []
    for name in names:
        session, result = runners[name]()
        sessions.append(session)
        results.append(result)
    return sessions, results


def _result_from_session(spec: ScenarioSpec, session: MockSession) -> dict[str, object]:
    ack = session.orchestrator.last_ack or {}
    decision = "NONE"
    if "decision" in ack:
        decision = "ALLOW" if int(ack["decision"]) == int(Decision.ALLOW) else "DENY"
    last_fault = session.guard.last_fault_code
    current_job = session.orchestrator.current_job
    if current_job is None:
        raise RuntimeError("scenario finished without current job")
    passed = _scenario_passed(spec.name, session)
    status = session.orchestrator.last_status or {}
    transport_stats = getattr(session.transport, "stats", None)
    control_plane_encrypted = isinstance(transport_stats, dict)
    actual_result = (
        f"decision={decision}, orchestrator={session.orchestrator.state.value}, "
        f"guard={session.guard.state.value}, last_fault={fault_tag(last_fault)}"
    )
    return {
        "scenario": spec.name,
        "description": spec.description,
        "tc_id": spec.tc_id,
        "fit_id": spec.fit_id,
        "injected_fault": spec.injected_fault,
        "expected_result": spec.expected_result,
        "actual_result": actual_result,
        "risk_item": spec.risk_item,
        "passed": passed,
        "job_id": current_job.job_id,
        "flags": current_job.flags,
        "artifact_sha_expected": current_job.expected_sha256,
        "artifact_sha_actual": current_job.artifact_sha,
        "deadline_ms": current_job.deadline_ms,
        "expected_outputs": current_job.expected_outputs,
        "decision": decision,
        "orchestrator_state": session.orchestrator.state.value,
        "guard_state": session.guard.state.value,
        "last_fault_code": fault_tag(last_fault),
        "fault_log": session.guard.fault_log + session.orchestrator.fault_log,
        "guard_state_log": session.guard.state_log,
        "status_snapshot": status,
        "ctrl_log": session.transport.ctrl_log,
        "control_plane_encrypted": control_plane_encrypted,
        "control_plane_crypto_stats": dict(transport_stats) if control_plane_encrypted else {
            "encrypt_tx": 0,
            "decrypt_rx": 0,
            "passthrough_rx": 0,
        },
    }


def _scenario_passed(name: str, session: MockSession) -> bool:
    if name == "allow":
        return session.orchestrator.state.value == "DONE" and session.guard.state.value == "READY"
    if name == "deny_sha":
        return (
            session.orchestrator.state.value == "DENIED"
            and session.guard.last_fault_code == FaultCode.ARTIFACT_SHA_MISMATCH
        )
    if name == "deny_input":
        return (
            session.orchestrator.state.value == "DENIED"
            and session.guard.last_fault_code == FaultCode.INPUT_CONTRACT_INVALID
        )
    if name == "timeout":
        return (
            session.orchestrator.state.value == "SAFE_STOPPED"
            and session.guard.last_fault_code == FaultCode.HEARTBEAT_TIMEOUT
            and session.guard.state.value == "FAULT_LATCHED"
        )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenAMP minimal closed-loop mock scenarios.")
    parser.add_argument(
        "--scenario",
        choices=["allow", "deny_sha", "deny_input", "timeout", "all"],
        default="all",
        help="Scenario to run.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional evidence output directory.",
    )
    parser.add_argument(
        "--run-id",
        default=f"openamp_mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Logical run identifier for evidence files.",
    )
    parser.add_argument(
        "--crypto-transport",
        action="store_true",
        help="Wrap control-plane transport with ML-KEM-derived AEAD (demo-only).",
    )
    args = parser.parse_args()

    scenario_names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    _, results = run_named_scenarios(scenario_names, use_crypto_transport=args.crypto_transport)

    evidence_files: dict[str, str] = {}
    if args.output_dir:
        evidence_files = write_example_bundle(
            output_dir=args.output_dir,
            run_id=args.run_id,
            scenario_results=results,
            template_dir=Path("session_bootstrap/templates"),
        )

    payload = {
        "run_id": args.run_id,
        "scenario_results": results,
        "evidence_files": evidence_files,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
