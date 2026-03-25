from __future__ import annotations

from argparse import Namespace
import html
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote
import urllib.request


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import server  # noqa: E402
from server import DashboardState, DemoRequestHandler  # noqa: E402


REPO_ROOT = DEMO_ROOT.parents[2]


def live_probe_payload(requested_at: str, summary: str) -> dict[str, object]:
    return {
        "requested_at": requested_at,
        "reachable": True,
        "status": "success",
        "summary": summary,
        "error": "",
        "details": {
            "hostname": "phytium-demo",
            "remoteproc": [{"name": "remoteproc0", "state": "running"}],
            "firmware": {"sha256": "abcd" * 16},
        },
    }


def failed_probe_payload(requested_at: str, summary: str, error: str) -> dict[str, object]:
    return {
        "requested_at": requested_at,
        "reachable": False,
        "status": "error",
        "summary": summary,
        "error": error,
        "details": {},
    }


def live_progress_payload(label: str, state: str, percent: int, current_stage: str) -> dict[str, object]:
    expected_count = server.DEFAULT_MAX_INPUTS
    completed_count = max(0, round((percent / 100.0) * expected_count)) if state != "running" else percent
    return {
        "state": state,
        "label": label,
        "tone": "online" if label == "真实在线推进" else "degraded",
        "percent": percent,
        "phase_percent": 76 if state == "running" else 100,
        "completed_count": completed_count,
        "expected_count": expected_count,
        "remaining_count": expected_count - completed_count,
        "completion_ratio": completed_count / expected_count,
        "count_source": "runner_log.sample_latency_lines" if state == "running" else "runner_summary.processed_count",
        "count_label": f"{completed_count} / {expected_count}",
        "current_stage": current_stage,
        "stages": [
            {"key": "connected", "label": "已连接", "status": "done", "detail": "STATUS_RESP: READY / fault=NONE"},
            {"key": "dispatched", "label": "已下发", "status": "done", "detail": "已向 OpenAMP 控制面提交 JOB_REQ。"},
            {"key": "running", "label": "板端执行中", "status": "current" if state == "running" else "done", "detail": "JOB_ACK(ALLOW) / guard=JOB_ACTIVE"},
            {
                "key": "returned",
                "label": "已返回结果",
                "status": "pending" if state == "running" else ("done" if label == "真实在线推进" else "error"),
                "detail": "等待 JOB_DONE。" if state == "running" else "JOB_DONE 已回收，runner_exit=0 / result=0",
            },
        ],
        "event_log": [
            "[19:24:47] STATUS_REQ -> guard=READY / fault=NONE",
            "[19:24:48] JOB_REQ -> trusted_sha=1946b08e6cf2",
            "[19:24:48] JOB_ACK(ALLOW) -> guard=JOB_ACTIVE / fault=NONE",
        ],
    }


class FakeInferenceJob:
    def __init__(self, snapshots: list[dict[str, object]], *, job_id: str = "demo-job-001") -> None:
        self.job_id = job_id
        self._snapshots = [json.loads(json.dumps(item)) for item in snapshots]
        self._calls = 0

    def snapshot(self) -> dict[str, object]:
        index = min(self._calls, len(self._snapshots) - 1)
        self._calls += 1
        return json.loads(json.dumps(self._snapshots[index]))


class NonClosingBytesIO(io.BytesIO):
    def close(self) -> None:
        return


class FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = NonClosingBytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        if "r" in mode:
            return self._rfile
        if "w" in mode:
            return self._wfile
        raise ValueError(f"Unsupported mode: {mode}")

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def close(self) -> None:
        return

    def response_bytes(self) -> bytes:
        return self._wfile.getvalue()


def request_response(
    state: DashboardState,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    payload = body or b""
    request_bytes = (
        f"{method} {path} HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        "Connection: close\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "\r\n"
    ).encode("utf-8") + payload
    server = type("FakeServer", (), {"app_state": state})()
    sock = FakeSocket(request_bytes)
    DemoRequestHandler(sock, ("127.0.0.1", 12345), server)

    raw_response = sock.response_bytes()
    header_bytes, response_body = raw_response.split(b"\r\n\r\n", 1)
    header_lines = header_bytes.decode("iso-8859-1").split("\r\n")
    status = int(header_lines[0].split()[1])
    headers: dict[str, str] = {}
    for line in header_lines[1:]:
        if not line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    return status, headers, response_body


def request_json(
    state: DashboardState,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], dict[str, object]]:
    status, headers, response_body = request_response(state, method, path, body)
    try:
        return status, headers, json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(response_body.decode("utf-8")) from exc


def request_text(
    state: DashboardState,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], str]:
    status, headers, response_body = request_response(state, method, path, body)
    return status, headers, response_body.decode("utf-8")


def archive_event(
    *,
    session_id: str,
    sequence: int,
    timestamp: str,
    event_type: str,
    message: str,
    plane: str = "control",
    source: str = "archive_test",
    job_id: str = "",
    mode_scope: str = server.CONTROL_MODE_SCOPE,
    data: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "event_id": f"{session_id}:{sequence:06d}",
        "sequence": sequence,
        "session_id": session_id,
        "timestamp": timestamp,
        "type": event_type,
        "job_id": job_id,
        "source": source,
        "plane": plane,
        "mode_scope": mode_scope,
        "message": message,
        "data": data or {},
    }


def write_archive_session(
    archive_root: str | Path,
    *,
    session_id: str,
    events: list[dict[str, object]] | None = None,
    snapshot: dict[str, object] | None = None,
) -> Path:
    session_dir = Path(archive_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    if events is not None:
        (session_dir / "events.jsonl").write_text(
            "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in events),
            encoding="utf-8",
        )
    if snapshot is not None:
        (session_dir / "state_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return session_dir


class DashboardStateTest(unittest.TestCase):
    def test_startup_uses_saved_successful_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "openamp_demo_live_probe_latest.json"
            payload = live_probe_payload("2026-03-15T12:00:00+0800", "saved probe summary")
            cache_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            state = DashboardState(None, 30.0, cache_path)
            snapshot = state.current_snapshot()

        self.assertEqual(snapshot["mode"]["effective_label"], "在线读数可用")
        self.assertEqual(snapshot["board"]["current_status"]["label"], "保存的只读 SSH 探板")
        self.assertEqual(snapshot["board"]["current_status"]["requested_at"], payload["requested_at"])
        self.assertTrue(snapshot["board"]["current_status"]["reachable"])

    def test_failed_refresh_keeps_last_successful_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "openamp_demo_live_probe_latest.json"
            success = live_probe_payload("2026-03-15T12:00:00+0800", "first success")
            failure = {
                "requested_at": "2026-03-15T12:05:00+0800",
                "reachable": False,
                "status": "error",
                "summary": "probe failed",
                "error": "ssh timeout",
                "details": {},
            }

            state = DashboardState(None, 30.0, cache_path)

            with patch("server.run_live_probe", return_value=success):
                self.assertEqual(state.refresh_live_probe(), success)

            cached_after_success = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(cached_after_success["requested_at"], success["requested_at"])

            with patch("server.run_live_probe", return_value=failure):
                self.assertEqual(state.refresh_live_probe(), failure)

            snapshot = state.current_snapshot()
            cached_after_failure = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(snapshot["board"]["current_status"]["requested_at"], success["requested_at"])
        self.assertTrue(snapshot["board"]["current_status"]["reachable"])
        self.assertEqual(cached_after_failure["requested_at"], success["requested_at"])


class ServerMainTest(unittest.TestCase):
    def test_main_builds_server_and_serves_without_startup_probe(self) -> None:
        args = Namespace(
            host="0.0.0.0",
            port=8090,
            probe_env="config/openamp.env",
            probe_timeout_sec=12.5,
            probe_startup=False,
            demo_admission_mode="",
            signed_manifest_file="",
            signed_manifest_public_key="",
            baseline_admission_mode="",
            baseline_signed_manifest_file="",
            baseline_signed_manifest_public_key="",
        )
        events: list[str] = []
        fake_app_state = Mock()
        fake_server = Mock()

        def build_state(
            probe_env: str,
            probe_timeout_sec: float,
            demo_startup_env_overrides: dict[str, str] | None = None,
            event_archive_root: str | Path | None = None,
        ) -> Mock:
            events.append("state_init")
            self.assertEqual(probe_env, args.probe_env)
            self.assertEqual(probe_timeout_sec, args.probe_timeout_sec)
            self.assertEqual(demo_startup_env_overrides, {})
            self.assertEqual(event_archive_root, server.default_event_archive_root())
            return fake_app_state

        def build_server(server_address: tuple[str, int], handler: type[DemoRequestHandler], app_state: Mock) -> Mock:
            events.append("server_init")
            self.assertEqual(server_address, (args.host, args.port))
            self.assertIs(handler, DemoRequestHandler)
            self.assertIs(app_state, fake_app_state)
            return fake_server

        fake_server.serve_forever.side_effect = lambda: events.append("serve_forever")

        with (
            patch("server.parse_args", return_value=args),
            patch("server.DashboardState", side_effect=build_state) as state_cls,
            patch("server.DemoHTTPServer", side_effect=build_server) as server_cls,
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            exit_code = server.main()

        state_cls.assert_called_once_with(
            args.probe_env,
            args.probe_timeout_sec,
            demo_startup_env_overrides={},
            event_archive_root=server.default_event_archive_root(),
        )
        server_cls.assert_called_once_with((args.host, args.port), DemoRequestHandler, fake_app_state)
        fake_app_state.refresh_live_probe.assert_not_called()
        fake_server.serve_forever.assert_called_once_with()
        self.assertEqual(exit_code, 0)
        self.assertEqual(events, ["state_init", "server_init", "serve_forever"])
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "Feiteng semantic visual return demo dashboard: http://0.0.0.0:8090",
                f"Project root: {server.PROJECT_ROOT}",
            ],
        )

    def test_main_runs_startup_probe_before_starting_server(self) -> None:
        args = Namespace(
            host="127.0.0.1",
            port=8079,
            probe_env="config/probe.env",
            probe_timeout_sec=5.0,
            probe_startup=True,
            demo_admission_mode="",
            signed_manifest_file="",
            signed_manifest_public_key="",
            baseline_admission_mode="",
            baseline_signed_manifest_file="",
            baseline_signed_manifest_public_key="",
        )
        events: list[str] = []
        fake_app_state = Mock()
        fake_server = Mock()

        def build_state(
            probe_env: str,
            probe_timeout_sec: float,
            demo_startup_env_overrides: dict[str, str] | None = None,
            event_archive_root: str | Path | None = None,
        ) -> Mock:
            events.append("state_init")
            self.assertEqual(probe_env, args.probe_env)
            self.assertEqual(probe_timeout_sec, args.probe_timeout_sec)
            self.assertEqual(demo_startup_env_overrides, {})
            self.assertEqual(event_archive_root, server.default_event_archive_root())
            return fake_app_state

        def build_server(server_address: tuple[str, int], handler: type[DemoRequestHandler], app_state: Mock) -> Mock:
            events.append("server_init")
            self.assertEqual(server_address, (args.host, args.port))
            self.assertIs(handler, DemoRequestHandler)
            self.assertIs(app_state, fake_app_state)
            return fake_server

        fake_app_state.refresh_live_probe.side_effect = lambda: events.append("refresh_live_probe")
        fake_server.serve_forever.side_effect = lambda: events.append("serve_forever")

        with (
            patch("server.parse_args", return_value=args),
            patch("server.DashboardState", side_effect=build_state) as state_cls,
            patch("server.DemoHTTPServer", side_effect=build_server) as server_cls,
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            exit_code = server.main()

        state_cls.assert_called_once_with(
            args.probe_env,
            args.probe_timeout_sec,
            demo_startup_env_overrides={},
            event_archive_root=server.default_event_archive_root(),
        )
        server_cls.assert_called_once_with((args.host, args.port), DemoRequestHandler, fake_app_state)
        fake_app_state.refresh_live_probe.assert_called_once_with()
        fake_server.serve_forever.assert_called_once_with()
        self.assertEqual(exit_code, 0)
        self.assertEqual(events, ["state_init", "refresh_live_probe", "server_init", "serve_forever"])


class DemoHTTPServerTest(unittest.TestCase):
    def test_snapshot_endpoint_returns_expected_high_level_fields(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(state, "GET", "/api/snapshot")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertIn("generated_at", payload)
        self.assertEqual(payload["project"]["name"], "飞腾多核弱网安全语义视觉回传系统")
        self.assertEqual(payload["mode"]["effective_label"], "仅展示证据")
        self.assertIn("current_status", payload["board"])
        self.assertIn("latest_live_status", payload)
        self.assertIn("PyTorch reference archive", payload["latest_live_status"]["headline"])
        self.assertEqual(payload["latest_live_status"]["baseline"]["completed"], "300 / 300 (archive)")
        self.assertIn("fits", payload)
        self.assertIsInstance(payload["fits"], list)

    def test_health_endpoint_returns_ok_payload(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(state, "GET", "/api/health")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload, {"status": "ok"})

    def test_link_director_status_endpoint_returns_default_scaffold_state(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(state, "GET", "/api/link-director")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload["selected_profile_id"], "normal")
        self.assertEqual(payload["selected_profile_label"], "正常链路")
        self.assertEqual(payload["selected_profile"]["profile_id"], "normal")
        self.assertEqual(payload["backend_binding"], "ui_scaffold_only")
        self.assertEqual(payload["backend_status"], "ui_scaffold_only")
        self.assertEqual(payload["selected_profile"]["evidence_binding"]["mode"], "live_anchor")
        self.assertIn("不执行 tc/netem", payload["summary"])
        self.assertIn("live 控制面与证据读数继续如实显示", payload["truth_note"])

    def test_link_director_profile_endpoint_switches_profile_and_emits_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            status, headers, payload = request_json(
                state,
                "POST",
                "/api/link-director/profile",
                body=json.dumps({"profile_id": "lossy"}).encode("utf-8"),
            )
            current_status, _, current_payload = request_json(state, "GET", "/api/link-director")
            event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=10")
            archive = event_payload["aggregate"]["archive"]
            events_path = Path(archive["events_jsonl"])
            archived_events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertTrue(payload["change_applied"])
        self.assertEqual(payload["previous_profile_id"], "normal")
        self.assertEqual(payload["selected_profile_id"], "lossy")
        self.assertEqual(payload["selected_profile_label"], "高丢包")
        self.assertEqual(payload["selected_profile"]["evidence_binding"]["scenario_id"], "snr10_real_compare")
        self.assertIn("未执行 tc/netem", payload["status_message"])
        self.assertEqual(current_status, 200)
        self.assertEqual(current_payload["selected_profile_id"], "lossy")
        self.assertEqual(event_status, 200)
        self.assertEqual(event_payload["aggregate"]["link_profile"]["selected_profile_id"], "lossy")
        self.assertEqual(event_payload["aggregate"]["link_profile"]["selected_profile_label"], "高丢包")
        event_types = [item["type"] for item in event_payload["recent_events"]]
        self.assertIn("LINK_PROFILE_CHANGED", event_types)
        self.assertIn("ARCHIVE_SNAPSHOT_WRITTEN", event_types)
        link_profile_events = [event for event in archived_events if event["type"] == "LINK_PROFILE_CHANGED"]
        self.assertEqual(len(link_profile_events), 1)
        self.assertEqual(link_profile_events[0]["data"]["profile_id"], "lossy")
        self.assertEqual(link_profile_events[0]["data"]["previous_profile_id"], "normal")

    def test_link_director_profile_endpoint_is_honest_noop_when_profile_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            status, _, payload = request_json(
                state,
                "POST",
                "/api/link-director/profile",
                body=json.dumps({"profile_id": "normal"}).encode("utf-8"),
            )
            event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=10")

        self.assertEqual(status, 200)
        self.assertFalse(payload["change_applied"])
        self.assertEqual(payload["selected_profile_id"], "normal")
        self.assertIn("UI/control-plane scaffold", payload["status_message"])
        self.assertEqual(event_status, 200)
        self.assertEqual(event_payload["aggregate"]["event_count"], 0)
        self.assertEqual(event_payload["recent_events"], [])

    def test_link_director_profile_endpoint_rejects_unsupported_profiles(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(
            state,
            "POST",
            "/api/link-director/profile",
            body=json.dumps({"profile_id": "not-real"}).encode("utf-8"),
        )

        self.assertEqual(status, 400)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload, {"status": "error", "message": "unsupported profile_id"})

    def test_archive_sessions_endpoint_lists_local_archive_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_archive_session(
                temp_dir,
                session_id="session_archive_old",
                events=[
                    archive_event(
                        session_id="session_archive_old",
                        sequence=1,
                        timestamp="2026-03-19T09:00:00+08:00",
                        event_type="JOB_SUBMITTED",
                        message="Old archive session submitted a demo job.",
                    ),
                    archive_event(
                        session_id="session_archive_old",
                        sequence=2,
                        timestamp="2026-03-19T09:00:02+08:00",
                        event_type="ARCHIVE_SNAPSHOT_WRITTEN",
                        plane="archive",
                        mode_scope="demo archive / local event evidence",
                        message="Event spine snapshot written (job_done).",
                        data={"reason": "job_done", "path": f"{temp_dir}/session_archive_old/state_snapshot.json"},
                    ),
                ],
                snapshot={
                    "generated_at": "2026-03-19T09:00:02+08:00",
                    "session_id": "session_archive_old",
                    "reason": "job_done",
                    "mode_boundary_note": server.MODE_BOUNDARY_NOTE,
                    "aggregate": {"session_id": "session_archive_old", "started_at": "2026-03-19T09:00:00+08:00"},
                    "recent_events": [],
                    "extra": {"variant": "current"},
                },
            )
            write_archive_session(
                temp_dir,
                session_id="session_archive_new",
                events=[
                    archive_event(
                        session_id="session_archive_new",
                        sequence=1,
                        timestamp="2026-03-19T11:15:00+08:00",
                        event_type="SAFE_STOP_TRIGGERED",
                        message="Heartbeat timeout triggered SAFE_STOP cleanup.",
                        data={"reason": "heartbeat_timeout_cleanup"},
                    ),
                    archive_event(
                        session_id="session_archive_new",
                        sequence=2,
                        timestamp="2026-03-19T11:15:03+08:00",
                        event_type="ARCHIVE_SNAPSHOT_WRITTEN",
                        plane="archive",
                        mode_scope="demo archive / local event evidence",
                        message="Event spine snapshot written (fault_heartbeat_timeout).",
                        data={"reason": "fault_heartbeat_timeout", "path": f"{temp_dir}/session_archive_new/state_snapshot.json"},
                    ),
                ],
                snapshot={
                    "generated_at": "2026-03-19T11:15:03+08:00",
                    "session_id": "session_archive_new",
                    "reason": "fault_heartbeat_timeout",
                    "mode_boundary_note": server.MODE_BOUNDARY_NOTE,
                    "aggregate": {"session_id": "session_archive_new", "started_at": "2026-03-19T11:15:00+08:00"},
                    "recent_events": [],
                    "extra": {"fault_type": "heartbeat_timeout"},
                },
            )
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            status, headers, payload = request_json(state, "GET", "/api/archive/sessions?limit=10")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload["session_count"], 2)
        self.assertEqual(
            [item["session_id"] for item in payload["sessions"]],
            ["session_archive_new", "session_archive_old"],
        )
        self.assertEqual(payload["sessions"][0]["last_snapshot_reason"], "fault_heartbeat_timeout")
        self.assertTrue(payload["sessions"][0]["has_events"])
        self.assertTrue(payload["sessions"][0]["has_snapshot"])
        self.assertTrue(payload["sessions"][0]["paths"]["events_jsonl"].endswith("session_archive_new/events.jsonl"))

    def test_archive_session_endpoint_replays_recent_events_and_snapshot_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_id = "session_archive_job_done"
            events = [
                archive_event(
                    session_id=session_id,
                    sequence=1,
                    timestamp="2026-03-19T10:00:00+08:00",
                    event_type="JOB_SUBMITTED",
                    message="Current live launch entered the archive session.",
                    job_id="job-42",
                    data={"variant": "current"},
                ),
                archive_event(
                    session_id=session_id,
                    sequence=2,
                    timestamp="2026-03-19T10:00:01+08:00",
                    event_type="JOB_ADMITTED",
                    message="OpenAMP admitted job-42.",
                    job_id="job-42",
                    data={"variant": "current"},
                ),
                archive_event(
                    session_id=session_id,
                    sequence=3,
                    timestamp="2026-03-19T10:00:02+08:00",
                    event_type="JOB_STARTED",
                    plane="data",
                    mode_scope=server.DATA_MODE_SCOPE,
                    message="Reconstruction execution started for job-42.",
                    job_id="job-42",
                    data={"variant": "current"},
                ),
                archive_event(
                    session_id=session_id,
                    sequence=4,
                    timestamp="2026-03-19T10:00:04+08:00",
                    event_type="FRAME_RECON_READY",
                    plane="data",
                    mode_scope=server.DATA_MODE_SCOPE,
                    message="Reconstruction output is ready for job-42.",
                    job_id="job-42",
                    data={"variant": "current"},
                ),
                archive_event(
                    session_id=session_id,
                    sequence=5,
                    timestamp="2026-03-19T10:00:05+08:00",
                    event_type="JOB_DONE",
                    plane="data",
                    mode_scope=server.DATA_MODE_SCOPE,
                    message="Reconstruction job job-42 completed.",
                    job_id="job-42",
                    data={"variant": "current", "total_ms": 128.4},
                ),
                archive_event(
                    session_id=session_id,
                    sequence=6,
                    timestamp="2026-03-19T10:00:06+08:00",
                    event_type="ARCHIVE_SNAPSHOT_WRITTEN",
                    plane="archive",
                    mode_scope="demo archive / local event evidence",
                    message="Event spine snapshot written (job_done).",
                    job_id="job-42",
                    data={"reason": "job_done", "path": f"{temp_dir}/{session_id}/state_snapshot.json"},
                ),
            ]
            write_archive_session(
                temp_dir,
                session_id=session_id,
                events=events,
                snapshot={
                    "generated_at": "2026-03-19T10:00:06+08:00",
                    "session_id": session_id,
                    "reason": "job_done",
                    "mode_boundary_note": server.MODE_BOUNDARY_NOTE,
                    "aggregate": {
                        "session_id": session_id,
                        "started_at": "2026-03-19T10:00:00+08:00",
                        "event_count": 5,
                    },
                    "recent_events": events[-3:],
                    "extra": {"variant": "current", "image_index": 12},
                },
            )
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            status, headers, payload = request_json(
                state,
                "GET",
                f"/api/archive/session?session_id={session_id}&limit=3",
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload["summary"]["session_id"], session_id)
        self.assertEqual(payload["summary"]["event_count"], 6)
        self.assertEqual(payload["summary"]["last_snapshot_reason"], "job_done")
        self.assertEqual(payload["aggregate"]["jobs"]["done_count"], 1)
        self.assertEqual(payload["aggregate"]["frames"]["ready_count"], 1)
        self.assertEqual(payload["snapshot"]["reason"], "job_done")
        self.assertEqual(payload["snapshot"]["extra"]["image_index"], 12)
        self.assertEqual(
            [item["type"] for item in payload["recent_events"]],
            ["ARCHIVE_SNAPSHOT_WRITTEN", "JOB_DONE", "FRAME_RECON_READY"],
        )
        self.assertEqual(payload["timeline"][0]["title"], "ARCHIVE_SNAPSHOT_WRITTEN")
        self.assertEqual(payload["timeline"][1]["lane"], "data")
        self.assertEqual(payload["timeline"][1]["job_id"], "job-42")
        self.assertTrue(payload["paths"]["state_snapshot_json"].endswith(f"{session_id}/state_snapshot.json"))

    def test_archive_session_endpoint_returns_404_for_missing_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            status, headers, payload = request_json(
                state,
                "GET",
                "/api/archive/session?session_id=missing-session",
            )

        self.assertEqual(status, 404)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload, {"status": "error", "message": "archive session not found: missing-session"})

    def test_event_spine_endpoint_tracks_live_inference_completion_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)
            request_json(
                state,
                "POST",
                "/api/session/board-access",
                body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
            )
            live_job = FakeInferenceJob(
                [
                    {
                        "status": "running",
                        "request_state": "running",
                        "status_category": "running",
                        "execution_mode": "live",
                        "variant": "current",
                        "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                        "runner_summary": {},
                        "wrapper_summary": {},
                        "diagnostics": {},
                        "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                        "artifacts": {},
                    },
                    {
                        "status": "success",
                        "request_state": "completed",
                        "status_category": "success",
                        "execution_mode": "live",
                        "variant": "current",
                        "message": "OpenAMP 控制面已完成作业下发、板端执行与结果回收。",
                        "runner_summary": {
                            "load_ms": 3.2,
                            "vm_init_ms": 0.8,
                            "run_median_ms": 128.4,
                            "artifact_sha256": "abcd" * 16,
                        },
                        "wrapper_summary": {"result": "success"},
                        "diagnostics": {},
                        "progress": live_progress_payload("真实在线推进", "completed", 100, "已返回结果"),
                        "artifacts": {},
                    },
                ],
                job_id="m0-event-job-001",
            )

            with (
                patch(
                    "server.query_live_status",
                    return_value={
                        "status": "success",
                        "guard_state": "READY",
                        "active_job_id": 0,
                        "last_fault_code": "NONE",
                        "total_fault_count": 0,
                        "heartbeat_ok": 1,
                        "logs": [],
                    },
                ),
                patch("server.launch_remote_reconstruction_job", return_value=live_job),
            ):
                start_status, start_headers, start_payload = request_json(
                    state,
                    "POST",
                    "/api/run-inference",
                    body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
                )
                progress_status, _, progress_payload = request_json(
                    state,
                    "GET",
                    f"/api/inference-progress?job_id={live_job.job_id}",
                )
                event_status, event_headers, event_payload = request_json(state, "GET", "/api/event-spine?limit=20")

                archive = event_payload["aggregate"]["archive"]
                events_path = Path(archive["events_jsonl"])
                snapshot_path = Path(archive["state_snapshot_json"])
                archived_types = [
                    json.loads(line)["type"]
                    for line in events_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

            self.assertEqual(start_status, 200)
            self.assertEqual(start_headers["content-type"], "application/json; charset=utf-8")
            self.assertEqual(start_payload["request_state"], "running")
            self.assertEqual(progress_status, 200)
            self.assertEqual(progress_payload["request_state"], "completed")
            self.assertEqual(event_status, 200)
            self.assertEqual(event_headers["cache-control"], "no-store")
            self.assertEqual(event_payload["status"], "ok")
            self.assertEqual(event_payload["aggregate"]["jobs"]["done_count"], 1)
            self.assertEqual(event_payload["aggregate"]["frames"]["ready_count"], 1)
            self.assertEqual(event_payload["aggregate"]["heartbeat"]["status"], "ok")
            self.assertTrue(archive["enabled"])
            self.assertTrue(events_path.is_file())
            self.assertTrue(snapshot_path.is_file())
            event_types = [item["type"] for item in event_payload["recent_events"]]
            for expected_type in (
                "JOB_SUBMITTED",
                "JOB_ADMITTED",
                "HEARTBEAT_OK",
                "JOB_STARTED",
                "FRAME_RECON_READY",
                "JOB_DONE",
                "ARCHIVE_SNAPSHOT_WRITTEN",
            ):
                with self.subTest(expected_type=expected_type):
                    self.assertIn(expected_type, event_types)
                    self.assertIn(expected_type, archived_types)

    def test_event_spine_endpoint_tracks_rejected_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)

            run_status, _, run_payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )
            event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=10")

            self.assertEqual(run_status, 200)
            self.assertEqual(run_payload["status"], "fallback")
            self.assertEqual(event_status, 200)
            self.assertEqual(event_payload["aggregate"]["jobs"]["rejected_count"], 1)
            event_types = [item["type"] for item in event_payload["recent_events"]]
            self.assertIn("JOB_SUBMITTED", event_types)
            self.assertIn("JOB_REJECTED", event_types)
            self.assertIn("ARCHIVE_SNAPSHOT_WRITTEN", event_types)

    def test_event_spine_endpoint_tracks_heartbeat_timeout_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)
            request_json(
                state,
                "POST",
                "/api/session/board-access",
                body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
            )

            with patch(
                "server.run_fault_action",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "last_fault_code": "HEARTBEAT_TIMEOUT",
                    "board_response": {
                        "decision": "ALLOW",
                        "fault_code": "HEARTBEAT_TIMEOUT",
                        "guard_state": "READY",
                    },
                    "logs": ["[02:36:22] heartbeat timeout live success"],
                },
            ):
                fault_status, _, fault_payload = request_json(
                    state,
                    "POST",
                    "/api/inject-fault",
                    body=json.dumps({"fault_type": "heartbeat_timeout"}).encode("utf-8"),
                )
                event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=20")

            self.assertEqual(fault_status, 200)
            self.assertEqual(fault_payload["status"], "injected")
            self.assertEqual(event_status, 200)
            self.assertEqual(event_payload["aggregate"]["heartbeat"]["status"], "lost")
            self.assertFalse(event_payload["aggregate"]["safe_stop"]["active"])
            event_types = [item["type"] for item in event_payload["recent_events"]]
            for expected_type in (
                "JOB_SUBMITTED",
                "JOB_ADMITTED",
                "HEARTBEAT_OK",
                "HEARTBEAT_LOST",
                "SAFE_STOP_TRIGGERED",
                "SAFE_STOP_CLEARED",
                "ARCHIVE_SNAPSHOT_WRITTEN",
            ):
                with self.subTest(expected_type=expected_type):
                    self.assertIn(expected_type, event_types)

    def test_job_manifest_gate_preview_endpoint_tracks_preview_only_allow_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)
            request_json(
                state,
                "POST",
                "/api/session/board-access",
                body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
            )

            with (
                patch(
                    "server.describe_demo_admission",
                    return_value={
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Signed manifest v1",
                        "tone": "online",
                        "bundle_path": "/tmp/openamp_demo_signed_admission/current.bundle.json",
                        "public_key_path": "/tmp/openamp_demo_signed_admission/current.public.pem",
                        "manifest_sha256": "a" * 64,
                        "artifact_sha256": "b" * 64,
                        "key_id": "demo-live-20260316",
                        "verified_locally": True,
                        "artifact_match": True,
                        "note": "key_id=demo-live-20260316 | bundle=current.bundle.json",
                    },
                ),
                patch(
                    "server.describe_demo_variant_support",
                    return_value={
                        "variant": "current",
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Current signed live 已支持",
                        "tone": "online",
                        "note": "Current signed-admission live path is supported.",
                        "supported": True,
                        "launch_allowed": True,
                    },
                ),
                patch(
                    "server.query_live_status",
                    return_value={
                        "status": "success",
                        "guard_state": "READY",
                        "active_job_id": 0,
                        "last_fault_code": "NONE",
                        "total_fault_count": 0,
                        "logs": ["[12:00:00] STATUS_RESP: guard=READY / fault=NONE"],
                    },
                ),
            ):
                preview_status, _, preview_payload = request_json(
                    state,
                    "POST",
                    "/api/job-manifest-gate/preview",
                    body=json.dumps({"variant": "current"}).encode("utf-8"),
                )
                event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=10")

        self.assertEqual(preview_status, 200)
        self.assertEqual(preview_payload["status"], "ok")
        self.assertTrue(preview_payload["preview_only"])
        self.assertEqual(preview_payload["gate"]["verdict"], "allow")
        self.assertIn("未发送 JOB_REQ", preview_payload["message"])
        self.assertEqual(event_status, 200)
        self.assertEqual(event_payload["aggregate"]["jobs"]["submitted_count"], 0)
        self.assertEqual(event_payload["aggregate"]["jobs"]["admitted_count"], 0)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_submitted_count"], 1)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_admitted_count"], 1)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_rejected_count"], 0)
        self.assertEqual(event_payload["aggregate"]["heartbeat"]["status"], "unknown")
        event_types = [item["type"] for item in event_payload["recent_events"]]
        self.assertIn("JOB_SUBMITTED", event_types)
        self.assertIn("JOB_ADMITTED", event_types)
        self.assertIn("ARCHIVE_SNAPSHOT_WRITTEN", event_types)
        self.assertNotIn("JOB_STARTED", event_types)
        self.assertNotIn("HEARTBEAT_OK", event_types)

    def test_job_manifest_gate_preview_endpoint_tracks_preview_only_rejection_when_board_busy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)
            request_json(
                state,
                "POST",
                "/api/session/board-access",
                body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
            )

            with (
                patch(
                    "server.describe_demo_admission",
                    return_value={
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Signed manifest v1",
                        "tone": "online",
                        "bundle_path": "/tmp/openamp_demo_signed_admission/current.bundle.json",
                        "public_key_path": "/tmp/openamp_demo_signed_admission/current.public.pem",
                        "manifest_sha256": "a" * 64,
                        "artifact_sha256": "b" * 64,
                        "key_id": "demo-live-20260316",
                        "verified_locally": True,
                        "artifact_match": True,
                        "note": "key_id=demo-live-20260316 | bundle=current.bundle.json",
                    },
                ),
                patch(
                    "server.describe_demo_variant_support",
                    return_value={
                        "variant": "current",
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Current signed live 已支持",
                        "tone": "online",
                        "note": "Current signed-admission live path is supported.",
                        "supported": True,
                        "launch_allowed": True,
                    },
                ),
                patch(
                    "server.query_live_status",
                    return_value={
                        "status": "success",
                        "guard_state": "JOB_ACTIVE",
                        "active_job_id": 8093,
                        "last_fault_code": "DUPLICATE_JOB_ID",
                        "total_fault_count": 1,
                        "logs": ["[12:00:00] STATUS_RESP: guard=JOB_ACTIVE"],
                    },
                ),
            ):
                preview_status, _, preview_payload = request_json(
                    state,
                    "POST",
                    "/api/job-manifest-gate/preview",
                    body=json.dumps({"variant": "current"}).encode("utf-8"),
                )
                event_status, _, event_payload = request_json(state, "GET", "/api/event-spine?limit=10")

        self.assertEqual(preview_status, 200)
        self.assertEqual(preview_payload["status"], "ok")
        self.assertEqual(preview_payload["gate"]["verdict"], "deny")
        self.assertIn("guard_state=JOB_ACTIVE", " ".join(preview_payload["gate"]["reasons"]))
        self.assertIn("未放行", preview_payload["message"])
        self.assertEqual(event_status, 200)
        self.assertEqual(event_payload["aggregate"]["jobs"]["submitted_count"], 0)
        self.assertEqual(event_payload["aggregate"]["jobs"]["rejected_count"], 0)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_submitted_count"], 1)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_admitted_count"], 0)
        self.assertEqual(event_payload["aggregate"]["jobs"]["preview_rejected_count"], 1)
        event_types = [item["type"] for item in event_payload["recent_events"]]
        self.assertIn("JOB_SUBMITTED", event_types)
        self.assertIn("JOB_REJECTED", event_types)
        self.assertNotIn("JOB_ADMITTED", event_types)

    def test_system_status_endpoint_preloads_repo_defaults_without_password(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        expected_env_file = state._board_access.env_file.relative_to(REPO_ROOT).as_posix()

        status, headers, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload["execution_mode"]["label"], "待补全密码")
        self.assertTrue(payload["board_access"]["configured"])
        self.assertFalse(payload["board_access"]["has_password"])
        self.assertEqual(payload["board_access"]["host"], "100.121.87.73")
        self.assertEqual(payload["board_access"]["user"], "user")
        self.assertEqual(payload["board_access"]["port"], 22)
        self.assertEqual(payload["board_access"]["env_file"], expected_env_file)
        self.assertEqual(payload["board_access"]["missing_connection_fields"], ["password"])
        self.assertEqual(payload["board_access"]["missing_inference_fields_by_variant"]["current"], ["password"])
        self.assertEqual(payload["board_access"]["missing_inference_fields_by_variant"]["baseline"], ["password"])
        self.assertEqual(payload["board_access"]["field_sources"]["host"], "preloaded")
        self.assertEqual(payload["board_access"]["field_sources"]["password"], "missing")
        self.assertEqual(
            payload["board_access"]["preloaded_defaults"]["ssh_env_file"],
            "session_bootstrap/config/phytium_pi_login.example.env",
        )
        self.assertEqual(
            payload["board_access"]["preloaded_defaults"]["inference_env_file"],
            expected_env_file,
        )
        self.assertNotIn("password", payload["board_access"])
        self.assertEqual(
            payload["live"]["admission"]["artifact_sha256"],
            payload["live"]["trusted_sha"],
        )
        self.assertEqual(payload["live"]["variant_support"]["baseline"]["mode"], "legacy_sha")
        self.assertEqual(payload["live"]["variant_support"]["baseline"]["label"], "PyTorch live 已支持")
        self.assertIn(
            "expected-SHA admission (legacy_sha)",
            payload["live"]["variant_support"]["baseline"]["note"],
        )
        self.assertTrue(payload["live"]["variant_support"]["baseline"]["launch_allowed"])
        self.assertFalse(payload["active_inference"]["running"])
        self.assertEqual(payload["active_inference"]["queue_depth"], 0)
        self.assertEqual(payload["active_inference"]["progress"]["count_label"], "0 active / 0 queued")
        self.assertEqual(payload["operator_cue"]["mode"], "operator_assist_only")
        self.assertEqual(payload["operator_cue"]["current_scene_id"], "scene1")
        self.assertEqual(payload["operator_cue"]["next_action"]["target_id"], "credentialPanel")
        self.assertIn("Operator-assist only", payload["operator_cue"]["manual_boundary_note"])
        self.assertEqual(payload["operator_cue"]["scenes"][0]["checks"][0]["label"], "会话已录入")
        self.assertFalse(payload["operator_cue"]["scenes"][0]["checks"][0]["ready"])

    def test_system_status_endpoint_exposes_redacted_board_access(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        save_status, _, save_payload = request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "demo-pass",
                    "port": "2202",
                }
            ).encode("utf-8"),
        )
        status, headers, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(save_status, 200)
        self.assertEqual(save_payload["status"], "ok")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertTrue(payload["board_access"]["configured"])
        self.assertEqual(payload["board_access"]["host"], "demo-board")
        self.assertEqual(payload["board_access"]["user"], "demo-user")
        self.assertTrue(payload["board_access"]["has_password"])
        self.assertNotIn("password", payload["board_access"])

    def test_system_status_endpoint_derives_safety_panel_from_live_recover_result(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        state._last_live_probe = live_probe_payload("2026-03-19T18:42:00+0800", "board reachable")
        state._last_control_status = {
            "status": "success",
            "guard_state": "READY",
            "last_fault_code": "HEARTBEAT_TIMEOUT",
            "active_job_id": 0,
            "total_fault_count": 3,
        }
        state._last_fault_result = {
            "fault_type": "recover",
            "status": "recovered",
            "status_category": "success",
            "execution_mode": "live",
            "source_label": "真机 SAFE_STOP 收口",
            "message": "板端已回到 READY；last_fault_code 保留最近故障证据。",
            "guard_state": "READY",
            "last_fault_code": "HEARTBEAT_TIMEOUT",
            "status_lamp": "yellow",
            "log_entries": ["[02:36:22] ◀ STATUS_RESP: READY，last_fault=HEARTBEAT_TIMEOUT"],
        }

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertIn("safety_panel", payload)
        self.assertEqual(payload["safety_panel"]["panel_label"], "SAFE_STOP 已执行")
        self.assertEqual(payload["safety_panel"]["safe_stop_state"], "RECOVERED")
        self.assertEqual(payload["safety_panel"]["latch_state"], "LATCHED")
        self.assertEqual(payload["safety_panel"]["guard_state"], "READY")
        self.assertEqual(payload["safety_panel"]["last_fault_code"], "HEARTBEAT_TIMEOUT")
        self.assertEqual(payload["safety_panel"]["total_fault_count"], 3)
        self.assertTrue(payload["safety_panel"]["board_online"])
        self.assertEqual(payload["safety_panel"]["status_source"], "live_control")
        self.assertEqual(payload["safety_panel"]["status_note"], "已缓存最近一次 RPMsg 控制面读数。")
        self.assertEqual(payload["safety_panel"]["last_fault_result"]["execution_mode"], "live")
        self.assertEqual(payload["safety_panel"]["last_fault_result"]["source_label"], "真机 SAFE_STOP 收口")
        self.assertEqual(
            payload["safety_panel"]["last_fault_result"]["log_tail"],
            "[02:36:22] ◀ STATUS_RESP: READY，last_fault=HEARTBEAT_TIMEOUT",
        )
        self.assertEqual(payload["safety_panel"]["recover_action"]["api_path"], "/api/recover")
        self.assertEqual(payload["safety_panel"]["recover_action"]["method"], "POST")
        self.assertIn(
            "RTOS/Bare Metal owns physical SAFE_STOP/GPIO; Linux UI is mirror/control surface only.",
            payload["safety_panel"]["ownership_note"],
        )

    def test_system_status_endpoint_derives_safety_panel_from_live_status_without_last_fault_result(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        state._last_live_probe = live_probe_payload("2026-03-19T18:45:00+0800", "board reachable")
        state._last_control_status = {
            "status": "success",
            "guard_state": "JOB_ACTIVE",
            "last_fault_code": "NONE",
            "active_job_id": 8093,
            "total_fault_count": 0,
        }

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["safety_panel"]["panel_label"], "无告警")
        self.assertEqual(payload["safety_panel"]["safe_stop_state"], "STANDBY")
        self.assertEqual(payload["safety_panel"]["latch_state"], "CLEAR")
        self.assertEqual(payload["safety_panel"]["guard_state"], "JOB_ACTIVE")
        self.assertEqual(payload["safety_panel"]["last_fault_code"], "NONE")
        self.assertEqual(payload["safety_panel"]["total_fault_count"], 0)
        self.assertEqual(payload["safety_panel"]["last_fault_result"], {})
        self.assertEqual(payload["safety_panel"]["recover_action"]["label"], "SAFE_STOP 收口")
        self.assertIn("不会自动 SAFE_STOP", payload["safety_panel"]["status_note"])

    def test_system_status_endpoint_advances_operator_cue_to_compare_after_current_live_result(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        state._last_live_probe = live_probe_payload("2026-03-19T19:10:00+0800", "board reachable")
        state._last_control_status = {
            "status": "success",
            "guard_state": "READY",
            "last_fault_code": "NONE",
            "active_job_id": 0,
            "total_fault_count": 0,
        }
        state._last_inference_result = {
            "variant": "current",
            "request_state": "completed",
            "status": "success",
            "execution_mode": "live",
            "source_label": "Current live 数据面",
            "message": "Current live 结果已经回到页面。",
            "job_id": "demo-job-compare",
        }

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["job_manifest_gate"]["verdict"], "allow")
        self.assertEqual(payload["operator_cue"]["current_scene_id"], "scene3")
        self.assertEqual(payload["operator_cue"]["status_label"], "第三幕 / Compare 与性能口径")
        self.assertEqual(payload["operator_cue"]["next_action"]["target_id"], "compareViewerShell")
        self.assertEqual(payload["operator_cue"]["next_action"]["act_id"], "act3")
        self.assertIn("4-core", payload["operator_cue"]["boundary_note"])
        self.assertTrue(payload["operator_cue"]["scenes"][2]["checks"][0]["ready"])
        self.assertTrue(payload["operator_cue"]["scenes"][2]["checks"][1]["ready"])

    def test_system_status_endpoint_includes_backend_aircraft_position_contract(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertIn("aircraft_position", payload)
        self.assertEqual(payload["aircraft_position"]["contract_version"], "aircraft_position.v1")
        self.assertEqual(payload["aircraft_position"]["source_api_path"], "/api/aircraft-position")
        self.assertEqual(payload["aircraft_position"]["source_kind"], "backend_stub")
        self.assertEqual(payload["aircraft_position"]["source_status"], "stub")
        self.assertEqual(payload["aircraft_position"]["source_label"], "Backend stub contract")
        self.assertIn("upper-computer/backend contract", payload["aircraft_position"]["ownership_note"])
        self.assertFalse(payload["aircraft_position"]["feed_contract"]["primary_source"]["active"])
        self.assertTrue(payload["aircraft_position"]["feed_contract"]["fallback_source"]["active"])
        self.assertEqual(payload["aircraft_position"]["sample"]["sequence"], 0)

    def test_aircraft_position_endpoint_updates_backend_feed(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, _, payload = request_json(
            state,
            "POST",
            "/api/aircraft-position",
            body=json.dumps(
                {
                    "source_kind": "upper_computer_gps",
                    "source_status": "live",
                    "source_label": "Upper Computer GPS live feed",
                    "position": {"latitude": 31.205, "longitude": 121.551},
                    "kinematics": {"heading_deg": 145.0, "ground_speed_kph": 275.5, "altitude_m": 3201.2},
                    "fix": {"type": "RTK", "confidence_m": 2.1, "satellites": 19},
                    "sample": {
                        "captured_at": "2026-03-20T09:41:00+0800",
                        "sequence": 12,
                        "transport": "backend_http_post",
                        "producer_id": "upper-computer-gps-daemon",
                    },
                }
            ).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["source_kind"], "upper_computer_gps")
        self.assertEqual(payload["source_status"], "live")
        self.assertAlmostEqual(payload["position"]["latitude"], 31.205)
        self.assertAlmostEqual(payload["position"]["longitude"], 121.551)
        self.assertEqual(payload["fix"]["type"], "RTK")
        self.assertEqual(payload["sample"]["sequence"], 12)
        self.assertEqual(payload["sample"]["captured_at"], "2026-03-20T09:41:00+0800")
        self.assertTrue(payload["feed_contract"]["primary_source"]["active"])
        self.assertFalse(payload["feed_contract"]["fallback_source"]["active"])

        status, _, latest = request_json(state, "GET", "/api/aircraft-position")

        self.assertEqual(status, 200)
        self.assertEqual(latest["source_status"], "live")
        self.assertAlmostEqual(latest["kinematics"]["ground_speed_kph"], 275.5)
        self.assertAlmostEqual(latest["kinematics"]["altitude_m"], 3201.2)
        self.assertEqual(latest["sample"]["sequence"], 12)
        self.assertEqual(latest["feed_contract"]["active_source_label"], "Upper Computer GPS")

    def test_aircraft_position_endpoint_auto_sequences_live_samples_when_feed_metadata_is_implicit(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        first_status, _, first_payload = request_json(
            state,
            "POST",
            "/api/aircraft-position",
            body=json.dumps({"position": {"latitude": 31.2, "longitude": 121.5}}).encode("utf-8"),
        )
        second_status, _, second_payload = request_json(
            state,
            "POST",
            "/api/aircraft-position",
            body=json.dumps({"position": {"latitude": 31.21, "longitude": 121.51}}).encode("utf-8"),
        )

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_payload["source_kind"], "upper_computer_gps")
        self.assertEqual(first_payload["source_status"], "live")
        self.assertEqual(first_payload["sample"]["sequence"], 1)
        self.assertEqual(second_payload["sample"]["sequence"], 2)
        self.assertTrue(second_payload["sample"]["captured_at"])
        self.assertIn("Upper Computer GPS", second_payload["feed_contract"]["active_source_label"])

    def test_system_status_endpoint_prioritizes_operator_cue_scene4_when_fault_is_latched(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        state._last_live_probe = live_probe_payload("2026-03-19T19:15:00+0800", "board reachable")
        state._last_control_status = {
            "status": "success",
            "guard_state": "READY",
            "last_fault_code": "HEARTBEAT_TIMEOUT",
            "active_job_id": 0,
            "total_fault_count": 1,
        }

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["operator_cue"]["current_scene_id"], "scene4")
        self.assertEqual(payload["operator_cue"]["next_action"]["target_id"], "act4Panel")
        self.assertEqual(payload["operator_cue"]["next_action"]["act_id"], "act4")
        self.assertIn("SAFE_STOP", payload["operator_cue"]["presenter_line"])
        self.assertEqual(payload["operator_cue"]["scenes"][3]["checks"][1]["label"], "Blackbox timeline")

    def test_system_status_endpoint_exposes_recent_results_for_refresh_hydration(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        baseline_payload = server.build_prerecorded_inference_result(0, "baseline")
        baseline_payload["job_id"] = "baseline-archive-001"
        current_payload = server.build_prerecorded_inference_result(0, "current")
        current_payload.update(
            {
                "status": "success",
                "execution_mode": "live",
                "status_category": "success",
                "source_label": "真实在线推进 + 归档样例图",
                "message": "Current live 结果已经回到页面。",
                "job_id": "demo-job-live-001",
                "request_state": "completed",
                "live_progress": live_progress_payload("真实在线推进", "completed", 100, "已返回结果"),
            }
        )

        state._update_last_inference_summary(baseline_payload, "baseline")
        state._update_last_inference_summary(current_payload, "current")

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["last_inference"]["variant"], "current")
        self.assertEqual(payload["recent_results"]["current"]["job_id"], "demo-job-live-001")
        self.assertEqual(payload["recent_results"]["current"]["execution_mode"], "live")
        self.assertEqual(payload["recent_results"]["current"]["sample"]["label"], current_payload["sample"]["label"])
        self.assertTrue(payload["recent_results"]["current"]["reconstructed_image_b64"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["recent_results"]["baseline"]["job_id"], "baseline-archive-001")
        self.assertEqual(payload["recent_results"]["baseline"]["execution_mode"], "reference")

    def test_operator_readiness_smoke_state_covers_required_page_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = DashboardState(None, 30.0, probe_cache_path=None, event_archive_root=temp_dir)
            request_json(
                state,
                "POST",
                "/api/session/board-access",
                body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
            )
            state._last_live_probe = live_probe_payload("2026-03-19T19:22:00+0800", "board reachable")
            state._last_control_status = {
                "status": "success",
                "guard_state": "READY",
                "last_fault_code": "NONE",
                "active_job_id": 0,
                "total_fault_count": 0,
                "logs": ["[19:22:00] STATUS_RESP: READY / fault=NONE"],
            }

            with (
                patch(
                    "server.describe_demo_admission",
                    return_value={
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Signed manifest v1",
                        "tone": "online",
                        "bundle_path": "/tmp/openamp_demo_signed_admission/current.bundle.json",
                        "public_key_path": "/tmp/openamp_demo_signed_admission/current.public.pem",
                        "manifest_sha256": "a" * 64,
                        "artifact_sha256": "b" * 64,
                        "key_id": "demo-live-20260316",
                        "verified_locally": True,
                        "artifact_match": True,
                        "note": "key_id=demo-live-20260316 | bundle=current.bundle.json",
                    },
                ),
                patch(
                    "server.describe_demo_variant_support",
                    side_effect=[
                        {
                            "variant": "current",
                            "status": "ready",
                            "mode": "signed_manifest_v1",
                            "label": "Current signed live 已支持",
                            "tone": "online",
                            "note": "Current signed-admission live path is supported.",
                            "supported": True,
                            "launch_allowed": True,
                        },
                        {
                            "variant": "baseline",
                            "status": "ready",
                            "mode": "legacy_sha",
                            "label": "PyTorch live 已支持",
                            "tone": "online",
                            "note": "PyTorch live path currently uses expected-SHA admission (legacy_sha).",
                            "supported": True,
                            "launch_allowed": True,
                        },
                        {
                            "variant": "current",
                            "status": "ready",
                            "mode": "signed_manifest_v1",
                            "label": "Current signed live 已支持",
                            "tone": "online",
                            "note": "Current signed-admission live path is supported.",
                            "supported": True,
                            "launch_allowed": True,
                        },
                        {
                            "variant": "baseline",
                            "status": "ready",
                            "mode": "legacy_sha",
                            "label": "PyTorch live 已支持",
                            "tone": "online",
                            "note": "PyTorch live path currently uses expected-SHA admission (legacy_sha).",
                            "supported": True,
                            "launch_allowed": True,
                        },
                    ],
                ),
                patch(
                    "server.query_live_status",
                    return_value={
                        "status": "success",
                        "guard_state": "READY",
                        "active_job_id": 0,
                        "last_fault_code": "NONE",
                        "total_fault_count": 0,
                        "logs": ["[19:22:01] STATUS_RESP: READY / fault=NONE"],
                    },
                ),
            ):
                preview_status, _, preview_payload = request_json(
                    state,
                    "POST",
                    "/api/job-manifest-gate/preview",
                    body=json.dumps({"variant": "current"}).encode("utf-8"),
                )
                link_status, _, link_payload = request_json(
                    state,
                    "POST",
                    "/api/link-director/profile",
                    body=json.dumps({"profile_id": "lossy"}).encode("utf-8"),
                )

                baseline_payload = server.build_prerecorded_inference_result(0, "baseline")
                baseline_payload["job_id"] = "baseline-archive-300"
                current_payload = server.build_prerecorded_inference_result(0, "current")
                current_payload.update(
                    {
                        "status": "success",
                        "execution_mode": "live",
                        "status_category": "success",
                        "source_label": "真实在线推进 + 归档样例图",
                        "message": "Current live 结果已经回到页面。",
                        "job_id": "demo-job-compare-300",
                        "request_state": "completed",
                        "live_progress": live_progress_payload("真实在线推进", "completed", 100, "已返回结果"),
                    }
                )
                state._update_last_inference_summary(baseline_payload, "baseline")
                state._update_last_inference_summary(current_payload, "current")

                status, _, payload = request_json(state, "GET", "/api/system-status")
                archive_list_status, _, archive_list_payload = request_json(state, "GET", "/api/archive/sessions?limit=10")
                current_session_id = archive_list_payload["current_session_id"] or archive_list_payload["sessions"][0]["session_id"]
                archive_status, _, archive_payload = request_json(
                    state,
                    "GET",
                    f"/api/archive/session?session_id={current_session_id}&limit=10",
                )

        self.assertEqual(preview_status, 200)
        self.assertEqual(preview_payload["gate"]["verdict"], "allow")
        self.assertEqual(link_status, 200)
        self.assertEqual(link_payload["selected_profile_id"], "lossy")
        self.assertEqual(status, 200)
        self.assertEqual(payload["operator_cue"]["current_scene_id"], "scene3")
        self.assertEqual(payload["operator_cue"]["next_action"]["target_id"], "compareViewerShell")
        self.assertEqual(payload["link_director"]["selected_profile_id"], "lossy")
        self.assertEqual(payload["job_manifest_gate"]["verdict"], "allow")
        self.assertEqual(payload["recent_results"]["current"]["execution_mode"], "live")
        self.assertEqual(payload["recent_results"]["baseline"]["execution_mode"], "reference")
        self.assertEqual(payload["safety_panel"]["panel_label"], "无告警")
        self.assertEqual(payload["safety_panel"]["safe_stop_state"], "IDLE")
        self.assertGreaterEqual(payload["event_spine"]["event_count"], 4)
        self.assertEqual(archive_list_status, 200)
        self.assertGreaterEqual(archive_list_payload["session_count"], 1)
        self.assertTrue(current_session_id)
        self.assertEqual(archive_status, 200)
        self.assertEqual(archive_payload["summary"]["session_id"], current_session_id)
        self.assertGreaterEqual(archive_payload["summary"]["event_count"], 1)
        self.assertTrue(archive_payload["timeline"])
        self.assertTrue(
            {"JOB_SUBMITTED", "JOB_ADMITTED", "LINK_PROFILE_CHANGED", "ARCHIVE_SNAPSHOT_WRITTEN"}
            & {item["title"] for item in archive_payload["timeline"]}
        )

    def test_system_status_endpoint_includes_demo_admission_summary(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        with (
            patch(
                "server.describe_demo_admission",
                return_value={
                    "status": "ready",
                    "mode": "signed_manifest_v1",
                    "label": "Signed manifest v1",
                    "tone": "online",
                    "bundle_path": "/tmp/openamp_demo_signed_admission/current.bundle.json",
                    "public_key_path": "/tmp/openamp_demo_signed_admission/current.public.pem",
                    "manifest_sha256": "a" * 64,
                    "artifact_sha256": "b" * 64,
                    "key_id": "demo-live-20260316",
                    "verified_locally": True,
                    "artifact_match": True,
                    "note": "key_id=demo-live-20260316 | bundle=current.bundle.json",
                },
            ),
            patch(
                "server.describe_demo_variant_support",
                side_effect=[
                    {
                        "variant": "current",
                        "status": "ready",
                        "mode": "signed_manifest_v1",
                        "label": "Current signed live 已支持",
                        "tone": "online",
                        "note": "Current signed-admission live path is supported.",
                        "supported": True,
                        "launch_allowed": True,
                    },
                    {
                        "variant": "baseline",
                        "status": "ready",
                        "mode": "legacy_sha",
                        "label": "PyTorch live 已支持",
                        "tone": "online",
                        "note": "PyTorch live path currently uses expected-SHA admission (legacy_sha).",
                        "supported": True,
                        "launch_allowed": True,
                    },
                ],
            ),
        ):
            status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["live"]["admission"]["mode"], "signed_manifest_v1")
        self.assertEqual(payload["live"]["admission"]["key_id"], "demo-live-20260316")
        self.assertTrue(payload["live"]["admission"]["verified_locally"])
        self.assertEqual(payload["live"]["variant_support"]["current"]["label"], "Current signed live 已支持")
        self.assertEqual(payload["live"]["variant_support"]["baseline"]["label"], "PyTorch live 已支持")
        self.assertTrue(payload["live"]["variant_support"]["baseline"]["launch_allowed"])
        self.assertEqual(payload["job_manifest_gate"]["admission_mode"], "signed_manifest_v1")
        self.assertEqual(payload["job_manifest_gate"]["variant"], "current")

    def test_job_manifest_gate_endpoint_returns_current_gate_details(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        with (
            patch(
                "server.describe_demo_admission",
                return_value={
                    "status": "ready",
                    "mode": "signed_manifest_v1",
                    "label": "Signed manifest v1",
                    "tone": "online",
                    "bundle_path": "/tmp/openamp_demo_signed_admission/current.bundle.json",
                    "public_key_path": "/tmp/openamp_demo_signed_admission/current.public.pem",
                    "manifest_sha256": "a" * 64,
                    "artifact_sha256": "b" * 64,
                    "key_id": "demo-live-20260316",
                    "verified_locally": True,
                    "artifact_match": True,
                    "note": "key_id=demo-live-20260316 | bundle=current.bundle.json",
                },
            ),
            patch(
                "server.describe_demo_variant_support",
                return_value={
                    "variant": "current",
                    "status": "ready",
                    "mode": "signed_manifest_v1",
                    "label": "Current signed live 已支持",
                    "tone": "online",
                    "note": "Current signed-admission live path is supported.",
                    "supported": True,
                    "launch_allowed": True,
                },
            ),
        ):
            status, _, payload = request_json(state, "GET", "/api/job-manifest-gate")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["gate"]["variant"], "current")
        self.assertEqual(payload["gate"]["admission_mode"], "signed_manifest_v1")
        self.assertEqual(payload["gate"]["verdict"], "hold")
        self.assertTrue(any("missing password" in reason for reason in payload["gate"]["reasons"]))
        self.assertIn("wire schema", payload["gate"]["protocol_boundary_note"])

    def test_system_status_endpoint_surfaces_running_active_inference(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        running_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                    "artifacts": {},
                }
            ],
            job_id="demo-job-active",
        )
        state._inference_jobs[running_job.job_id] = {
            "job": running_job,
            "job_id": running_job.job_id,
            "variant": "current",
            "image_index": 0,
        }

        status, _, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertTrue(payload["active_inference"]["running"])
        self.assertEqual(payload["active_inference"]["job_id"], "demo-job-active")
        self.assertEqual(payload["active_inference"]["variant"], "current")
        self.assertEqual(payload["active_inference"]["queue_depth"], 1)
        self.assertEqual(payload["active_inference"]["progress"]["current_stage"], "板端执行中")

    def test_board_access_endpoint_accepts_password_only_and_keeps_preloaded_defaults(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        expected_env_file = state._board_access.env_file.relative_to(REPO_ROOT).as_posix()

        status, _, payload = request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["board_access"]["host"], "100.121.87.73")
        self.assertEqual(payload["board_access"]["user"], "user")
        self.assertEqual(payload["board_access"]["port"], 22)
        self.assertEqual(payload["board_access"]["env_file"], expected_env_file)
        self.assertTrue(payload["board_access"]["has_password"])
        self.assertTrue(payload["board_access"]["connection_ready"])
        self.assertTrue(payload["board_access"]["inference_ready_variants"]["current"])
        self.assertTrue(payload["board_access"]["inference_ready_variants"]["baseline"])
        self.assertEqual(payload["board_access"]["field_sources"]["password"], "session")

    def test_probe_board_endpoint_updates_snapshot_after_success(self) -> None:
        success = live_probe_payload("2026-03-15T12:00:00+0800", "board reachable")
        state = DashboardState(None, 30.0, probe_cache_path=None)

        with patch("server.run_live_probe", return_value=success):
            probe_status, _, probe_payload = request_json(state, "POST", "/api/probe-board", body=b"{}")
            snapshot_status, _, snapshot_payload = request_json(state, "GET", "/api/snapshot")

        self.assertEqual(probe_status, 200)
        self.assertEqual(probe_payload, success)
        self.assertEqual(snapshot_status, 200)
        self.assertEqual(snapshot_payload["mode"]["effective_label"], "在线读数可用")
        self.assertEqual(snapshot_payload["board"]["current_status"]["label"], "最新只读 SSH 探板")
        self.assertEqual(snapshot_payload["board"]["current_status"]["requested_at"], success["requested_at"])
        self.assertTrue(snapshot_payload["board"]["current_status"]["reachable"])

    def test_probe_board_endpoint_uses_saved_session_access_when_present(self) -> None:
        success = live_probe_payload("2026-03-15T12:00:00+0800", "board reachable")
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "demo-pass",
                    "port": "2202",
                }
            ).encode("utf-8"),
        )

        with (
            patch("server.run_live_probe", return_value=success) as run_probe,
            patch("server.query_live_status", return_value={"status": "error", "message": "skip"}) as query_status,
        ):
            probe_status, _, probe_payload = request_json(state, "POST", "/api/probe-board", body=b"{}")

        self.assertEqual(probe_status, 200)
        self.assertEqual(probe_payload["requested_at"], success["requested_at"])
        run_probe.assert_called_once()
        self.assertEqual(run_probe.call_args.kwargs["env_values"]["REMOTE_HOST"], "demo-board")
        self.assertEqual(run_probe.call_args.kwargs["env_values"]["REMOTE_USER"], "demo-user")
        self.assertEqual(run_probe.call_args.kwargs["env_values"]["REMOTE_PASS"], "demo-pass")
        self.assertEqual(run_probe.call_args.kwargs["env_values"]["REMOTE_SSH_PORT"], "2202")
        query_status.assert_called_once()

    def test_probe_board_endpoint_returns_failure_without_mutating_snapshot(self) -> None:
        failure = failed_probe_payload(
            "2026-03-15T12:05:00+0800",
            "probe failed",
            "ssh timeout",
        )
        state = DashboardState(None, 30.0, probe_cache_path=None)

        with patch("server.run_live_probe", return_value=failure):
            probe_status, _, probe_payload = request_json(state, "POST", "/api/probe-board", body=b"{}")
            snapshot_status, _, snapshot_payload = request_json(state, "GET", "/api/snapshot")

        self.assertEqual(probe_status, 200)
        self.assertEqual(probe_payload, failure)
        self.assertEqual(snapshot_status, 200)
        self.assertEqual(snapshot_payload["mode"]["effective_label"], "仅展示证据")
        self.assertEqual(snapshot_payload["board"]["current_status"]["label"], "暂无在线探板")
        self.assertFalse(snapshot_payload["board"]["current_status"]["reachable"])
        self.assertEqual(snapshot_payload["board"]["current_status"]["requested_at"], "")

    def test_run_inference_endpoint_falls_back_until_password_is_provided(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(
            state,
            "POST",
            "/api/run-inference",
            body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload["execution_mode"], "prerecorded")
        self.assertEqual(payload["variant"], "current")
        self.assertEqual(payload["status"], "fallback")
        self.assertEqual(payload["request_state"], "completed")
        self.assertEqual(payload["status_category"], "config_error")
        self.assertIn("配置不完整或不可用", payload["message"])
        self.assertEqual(payload["live_attempt"]["status"], "config_error")
        self.assertEqual(payload["live_attempt"]["diagnostics"]["missing_fields"], ["password"])
        self.assertEqual(payload["live_progress"]["completed_count"], 0)
        self.assertEqual(payload["live_progress"]["expected_count"], server.DEFAULT_MAX_INPUTS)
        self.assertEqual(payload["live_progress"]["count_label"], f"0 / {server.DEFAULT_MAX_INPUTS}")
        self.assertIn("guided_demo", state.current_snapshot())

    def test_run_inference_endpoint_starts_live_job_with_preloaded_env_after_password_only_save(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        saved_access = state._board_access
        live_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                    "artifacts": {},
                }
            ]
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "active_job_id": 0,
                    "last_fault_code": "NONE",
                    "total_fault_count": 0,
                    "logs": [],
                },
            ),
            patch(
                "server.launch_remote_reconstruction_job",
                return_value=live_job,
            ) as launch_job,
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["request_state"], "running")
        self.assertEqual(payload["job_id"], live_job.job_id)
        access = launch_job.call_args.args[0]
        self.assertIsNot(access, saved_access)
        self.assertEqual(access.host, "100.121.87.73")
        self.assertEqual(access.user, "user")
        self.assertEqual(access.password, "demo-pass")
        self.assertEqual(access.env_file, saved_access.env_file)
        self.assertEqual(
            access.build_env()["INFERENCE_CURRENT_EXPECTED_SHA256"],
            "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1",
        )

    def test_run_inference_endpoint_blocks_when_demo_already_has_running_live_job(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        running_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                    "artifacts": {},
                }
            ],
            job_id="demo-job-001",
        )
        state._inference_jobs[running_job.job_id] = {
            "job": running_job,
            "job_id": running_job.job_id,
            "variant": "current",
            "image_index": 0,
        }

        with patch("server.launch_remote_reconstruction_job") as launch_job:
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "fallback")
        self.assertEqual(payload["status_category"], "board_busy")
        self.assertIn("demo-job-001", payload["message"])
        self.assertEqual(payload["live_attempt"]["status"], "blocked")
        launch_job.assert_not_called()

    def test_run_inference_endpoint_blocks_when_live_status_reports_job_active(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )

        with (
            patch(
                "server.describe_demo_variant_support",
                return_value={
                    "variant": "current",
                    "status": "ready",
                    "mode": "signed_manifest_v1",
                    "label": "Current signed live 已支持",
                    "tone": "online",
                    "note": "Current signed-admission live path is supported.",
                    "supported": True,
                    "launch_allowed": True,
                },
            ),
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "JOB_ACTIVE",
                    "active_job_id": 8093,
                    "last_fault_code": "DUPLICATE_JOB_ID",
                    "logs": ["[02:27:52] STATUS_RESP: guard=JOB_ACTIVE"],
                },
            ),
            patch("server.launch_remote_reconstruction_job") as launch_job,
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "fallback")
        self.assertEqual(payload["status_category"], "board_busy")
        self.assertIn("Current signed-admission live path 已支持", payload["message"])
        self.assertIn("guard_state=JOB_ACTIVE", payload["message"])
        self.assertEqual(payload["live_attempt"]["diagnostics"]["board_status"]["active_job_id"], 8093)
        launch_job.assert_not_called()

    def test_run_inference_endpoint_falls_back_to_runner_only_live_when_status_preflight_fails(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        live_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "Current live 已切到 SSH 兼容模式，界面正在同步板端执行进度。",
                    "control_transport": "none",
                    "control_handshake_complete": False,
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {
                        "control_preflight": {
                            "status": "timeout",
                            "status_category": "timeout",
                        }
                    },
                    "progress": live_progress_payload("真实在线执行（控制面降级）", "running", 76, "板端执行中"),
                    "artifacts": {},
                }
            ],
            job_id="compat-live-001",
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "timeout",
                    "status_category": "timeout",
                    "message": "远端状态查询超时，请确认板卡在线后重试。",
                    "diagnostics": {"error": "STATUS_REQ tx_ok_rx_timeout"},
                    "logs": [],
                },
            ),
            patch("server.launch_remote_reconstruction_job", return_value=live_job) as launch_job,
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["source_label"], "真实在线执行（控制面降级）")
        self.assertIn("SSH 兼容模式", payload["message"])
        self.assertEqual(payload["live_attempt"]["control_transport"], "none")
        self.assertFalse(payload["live_attempt"]["control_handshake_complete"])
        launch_job.assert_called_once()
        _, kwargs = launch_job.call_args
        self.assertEqual(kwargs["control_transport"], "none")
        self.assertEqual(
            kwargs["control_preflight"]["status"],
            "timeout",
        )

    def test_run_baseline_endpoint_starts_pytorch_live_job(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )
        live_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "baseline",
                    "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                    "artifacts": {},
                }
            ],
            job_id="demo-pytorch-001",
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "active_job_id": 0,
                    "last_fault_code": "NONE",
                    "total_fault_count": 0,
                    "logs": [],
                },
            ),
            patch("server.launch_remote_reconstruction_job", return_value=live_job) as launch_job,
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-baseline",
                body=json.dumps({"image_index": 0}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["request_state"], "running")
        self.assertEqual(payload["variant"], "baseline")
        self.assertEqual(payload["job_id"], "demo-pytorch-001")
        self.assertEqual(payload["source_label"], "真实在线推进")
        self.assertIn("OpenAMP 控制面已接管", payload["message"])
        launch_job.assert_called_once()

    def test_inference_progress_endpoint_returns_completed_live_payload(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "demo-pass",
                    "port": "22",
                    "env_file": "session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env",
                }
            ).encode("utf-8"),
        )
        live_job = FakeInferenceJob(
            [
                {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "OpenAMP 控制面已接管本次演示，界面正在同步板端阶段。",
                    "runner_summary": {},
                    "wrapper_summary": {},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "running", 76, "板端执行中"),
                    "artifacts": {},
                },
                {
                    "status": "success",
                    "request_state": "completed",
                    "status_category": "success",
                    "execution_mode": "live",
                    "variant": "current",
                    "message": "OpenAMP 控制面已完成作业下发、板端执行与结果回收。",
                    "runner_summary": {
                        "load_ms": 3.2,
                        "vm_init_ms": 0.8,
                        "run_median_ms": 128.4,
                        "artifact_sha256": "abcd" * 16,
                    },
                    "wrapper_summary": {"result": "success"},
                    "diagnostics": {},
                    "progress": live_progress_payload("真实在线推进", "completed", 100, "已返回结果"),
                    "artifacts": {},
                },
            ]
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "active_job_id": 0,
                    "last_fault_code": "NONE",
                    "total_fault_count": 0,
                    "logs": [],
                },
            ),
            patch(
                "server.launch_remote_reconstruction_job",
                return_value=live_job,
            ) as launch_job,
        ):
            start_status, _, start_payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )
            status, _, payload = request_json(
                state,
                "GET",
                f"/api/inference-progress?job_id={live_job.job_id}",
            )

        self.assertEqual(start_status, 200)
        self.assertEqual(start_payload["request_state"], "running")
        self.assertEqual(status, 200)
        self.assertEqual(payload["request_state"], "completed")
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["source_label"], "真实在线推进 + 归档样例图")
        self.assertAlmostEqual(payload["timings"]["total_ms"], 132.4)
        self.assertEqual(payload["artifact_sha"], "abcd" * 16)
        self.assertEqual(payload["live_progress"]["completed_count"], server.DEFAULT_MAX_INPUTS)
        self.assertEqual(payload["live_progress"]["expected_count"], server.DEFAULT_MAX_INPUTS)
        self.assertEqual(payload["live_progress"]["count_source"], "runner_summary.processed_count")
        launch_job.assert_called_once()
        access = launch_job.call_args.args[0]
        self.assertEqual(
            access.build_env()["INFERENCE_CURRENT_EXPECTED_SHA256"],
            "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1",
        )

    def test_inference_progress_endpoint_returns_not_found_for_unknown_job(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, _, payload = request_json(
            state,
            "GET",
            "/api/inference-progress?job_id=missing-job",
        )

        self.assertEqual(status, 404)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "job not found")

    def test_inference_progress_endpoint_preserves_live_failure_diagnostics_on_fallback(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "placeholder-pass",
                    "port": "22",
                    "env_file": "session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env",
                }
            ).encode("utf-8"),
        )
        live_job = FakeInferenceJob(
            [
                {
                    "status": "error",
                    "request_state": "completed",
                    "status_category": "auth_error",
                    "execution_mode": "fallback",
                    "variant": "current",
                    "message": "远端推理认证失败，请检查板卡用户名、密码或 SSH 端口设置。 当前已回退到预录结果。",
                    "runner_summary": {},
                    "wrapper_summary": {"result": "runner_failed"},
                    "diagnostics": {"stderr": "Permission denied (publickey,password).", "returncode": 255},
                    "progress": live_progress_payload("在线失败已回退", "completed", 100, "已返回结果"),
                    "artifacts": {},
                }
            ]
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "active_job_id": 0,
                    "last_fault_code": "NONE",
                    "total_fault_count": 0,
                    "logs": [],
                },
            ),
            patch(
                "server.launch_remote_reconstruction_job",
                return_value=live_job,
            ),
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "prerecorded")
        self.assertEqual(payload["status"], "fallback")
        self.assertEqual(payload["status_category"], "auth_error")
        self.assertIn("认证失败", payload["message"])
        self.assertNotIn("Permission denied", payload["message"])
        self.assertEqual(payload["live_attempt"]["diagnostics"]["stderr"], "Permission denied (publickey,password).")
        self.assertEqual(payload["live_progress"]["label"], "在线失败已回退")

    def test_inference_timeout_fallback_marks_handshake_incomplete_and_archive_only(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "placeholder-pass",
                    "port": "22",
                    "env_file": "session_bootstrap/config/inference_tvm310_safe.2026-03-10.phytium_pi.env",
                }
            ).encode("utf-8"),
        )
        live_job = FakeInferenceJob(
            [
                {
                    "status": "error",
                    "request_state": "completed",
                    "status_category": "timeout",
                    "execution_mode": "fallback",
                    "variant": "current",
                    "message": (
                        "STATUS_REQ 已写入 RPMsg，但超时前未收到 STATUS_RESP；"
                        "JOB_REQ 已写入 RPMsg，但超时前未收到 JOB_ACK。"
                        "本次板端握手未完成，界面已回退到预录结果。"
                    ),
                    "control_handshake_complete": False,
                    "runner_summary": {},
                    "wrapper_summary": {"result": "denied_by_control_hook"},
                    "diagnostics": {
                        "control_handshake": {
                            "complete": False,
                            "status_req_transport": "tx_ok_rx_timeout",
                            "job_req_transport": "tx_ok_rx_timeout",
                        }
                    },
                    "progress": live_progress_payload("握手未完成，已回退", "completed", 0, "连接失败"),
                    "artifacts": {},
                }
            ]
        )

        with (
            patch(
                "server.query_live_status",
                return_value={
                    "status": "success",
                    "guard_state": "READY",
                    "active_job_id": 0,
                    "last_fault_code": "NONE",
                    "total_fault_count": 0,
                    "logs": [],
                },
            ),
            patch(
                "server.launch_remote_reconstruction_job",
                return_value=live_job,
            ),
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "prerecorded")
        self.assertEqual(payload["status"], "fallback")
        self.assertEqual(payload["status_category"], "timeout")
        self.assertEqual(payload["source_label"], "握手未完成，回退展示（归档样例）")
        self.assertIn("不宣称本次 live 已完成", payload["message"])
        self.assertFalse(payload["live_attempt"]["control_handshake_complete"])
        self.assertEqual(payload["live_progress"]["label"], "握手未完成，已回退")

    def test_inject_fault_endpoint_keeps_live_attempt_diagnostics_on_replay_fallback(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "placeholder-pass",
                    "port": "22",
                }
            ).encode("utf-8"),
        )

        with patch(
            "server.run_fault_action",
            return_value={
                "status": "parse_error",
                "status_category": "auth_error",
                "message": "远端故障注入认证失败，请检查板卡用户名、密码或 SSH 端口设置。",
                "diagnostics": {"stderr": "Permission denied (publickey,password).", "returncode": 255},
                "logs": [],
            },
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/inject-fault",
                body=json.dumps({"fault_type": "wrong_sha"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "replay")
        self.assertEqual(payload["status_category"], "auth_error")
        self.assertIn("认证失败", payload["message"])
        self.assertNotIn("Permission denied", payload["message"])
        self.assertEqual(payload["live_attempt"]["diagnostics"]["stderr"], "Permission denied (publickey,password).")

    def test_inject_fault_endpoint_returns_replay_when_not_configured(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, _, payload = request_json(
            state,
            "POST",
            "/api/inject-fault",
            body=json.dumps({"fault_type": "wrong_sha"}).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "replay")
        self.assertEqual(payload["fit_id"], "FIT-01")
        self.assertIn("回放", payload["source_label"])

    def test_recover_endpoint_keeps_retained_fault_visible_on_live_safe_stop(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps(
                {
                    "host": "demo-board",
                    "user": "demo-user",
                    "password": "placeholder-pass",
                    "port": "22",
                }
            ).encode("utf-8"),
        )

        with patch(
            "server.run_recover_action",
            return_value={
                "status": "success",
                "guard_state": "READY",
                "last_fault_code": "HEARTBEAT_TIMEOUT",
                "board_response": {
                    "decision": "ACK",
                    "fault_code": "HEARTBEAT_TIMEOUT",
                    "guard_state": "READY",
                },
                "logs": ["[02:36:22] ◀ STATUS_RESP: READY，last_fault=HEARTBEAT_TIMEOUT"],
            },
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/recover",
                body=json.dumps({}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["source_label"], "真机 SAFE_STOP 收口")
        self.assertEqual(payload["guard_state"], "READY")
        self.assertEqual(payload["last_fault_code"], "HEARTBEAT_TIMEOUT")
        self.assertEqual(payload["status_lamp"], "yellow")
        self.assertIn("不宣称已清零", payload["message"])

    def test_recover_endpoint_replay_preserves_latest_fault_code(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        state._last_fault_result = {
            "fault_type": "wrong_sha",
            "status": "injected",
            "status_category": "success",
            "execution_mode": "replay",
            "message": "cached replay",
            "guard_state": "READY",
            "last_fault_code": "ARTIFACT_SHA_MISMATCH",
        }

        status, _, payload = request_json(
            state,
            "POST",
            "/api/recover",
            body=json.dumps({}).encode("utf-8"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "replay")
        self.assertEqual(payload["source_label"], "SAFE_STOP 收口回放")
        self.assertEqual(payload["guard_state"], "READY")
        self.assertEqual(payload["last_fault_code"], "ARTIFACT_SHA_MISMATCH")
        self.assertEqual(payload["status_lamp"], "yellow")
        self.assertIn("保留最近 fault code", payload["message"])

    def test_root_serves_dashboard_entry_page(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/")

        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("<title>飞腾多核弱网安全语义视觉回传演示系统</title>", body)
        self.assertIn("飞腾多核弱网安全语义视觉回传系统", body)
        self.assertIn('id="cockpitShell"', body)
        self.assertIn('id="flightStage"', body)
        self.assertIn('id="aircraftVector"', body)
        self.assertIn('id="aircraftContractStrip"', body)
        self.assertIn('id="missionCoreCard"', body)
        self.assertIn('id="comparePeekCard"', body)
        self.assertIn('id="weakNetworkConsole"', body)
        self.assertIn('id="operatorCueShell"', body)
        self.assertIn('id="mainSafetyMirror"', body)
        self.assertIn('id="sessionDrawer"', body)
        self.assertIn('id="compareDrawer"', body)
        self.assertIn('id="safetyDrawer"', body)
        self.assertIn('id="compareViewerBoard"', body)
        self.assertIn('id="compareViewerSampleLabel"', body)
        self.assertIn('id="baselineProgressTitle"', body)
        self.assertIn("PyTorch reference 300 张图", body)
        self.assertIn("运行 PyTorch live 数据面 300 张图", body)
        self.assertIn('<script src="/app.js"></script>', body)

    def test_app_js_serves_dashboard_javascript(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/app.js")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/javascript; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("const state = {", body)
        self.assertIn('fetchJSON("/api/snapshot")', body)
        self.assertIn('fetchJSON("/api/system-status")', body)
        self.assertIn('fetchJSON("/api/link-director")', body)
        self.assertIn('fetchJSON("/api/archive/sessions?limit=25")', body)
        self.assertIn('fetchJSON(`/api/archive/session?session_id=${encodeURIComponent(nextArchiveSessionId)}&limit=25`)', body)
        self.assertIn('fetchJSON("/api/link-director/profile"', body)
        self.assertIn("systemStatus?.aircraft_position", body)
        self.assertIn('document.getElementById("aircraftContractStrip")', body)
        self.assertIn("aircraft.feed_contract?.summary", body)
        self.assertIn("renderCockpitShell", body)
        self.assertIn("openDrawer", body)
        self.assertIn("closeDrawer", body)
        self.assertIn("normalizeOperatorCue", body)
        self.assertIn("renderOperatorCue", body)
        self.assertIn("renderWeakNetworkConsole", body)
        self.assertNotIn("navigator.geolocation", body)
        self.assertIn("hydrateRecentResultsFromSystemStatus", body)
        self.assertIn("systemStatus?.recent_results", body)
        self.assertIn("state.currentResult = recentResults.current;", body)
        self.assertIn("state.baselineResult = recentResults.baseline;", body)
        self.assertIn('document.getElementById("operatorCueShell")', body)
        self.assertIn("systemStatus.operator_cue", body)
        self.assertIn("buildCommandCenterModel", body)
        self.assertIn("resolveWeakNetworkSelection", body)
        self.assertIn("jumpToTarget", body)
        self.assertIn('document.getElementById("missionCoreCard")', body)
        self.assertIn('document.getElementById("weakNetworkConsole")', body)
        self.assertIn('document.getElementById("comparePeekCard")', body)
        self.assertIn("data-jump-target", body)
        self.assertIn("data-open-drawer", body)
        self.assertIn("data-weak-scenario-id", body)
        self.assertIn("effectiveSafetyPanel", body)
        self.assertIn("renderSafetyFrontPanel", body)
        self.assertIn("systemStatus.safety_panel", body)
        self.assertIn('"/api/recover"', body)
        self.assertIn("selectedCompareViewerSample", body)
        self.assertIn('document.getElementById("compareViewerBoard")', body)
        self.assertIn("baselineLiveDisplayLabel", body)
        self.assertIn("PyTorch reference archive", body)
        self.assertIn("PyTorch signed live", body)

    def test_app_css_serves_dashboard_stylesheet(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/app.css")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/css; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn(":root {", body)
        self.assertIn("--accent: #c95d12;", body)
        self.assertIn(".cockpit-shell", body)
        self.assertIn(".flight-stage", body)
        self.assertIn(".details-drawer", body)
        self.assertIn(".aircraft-vector", body)
        self.assertIn(".operator-cue-shell", body)
        self.assertIn(".weak-console-metrics", body)

    def test_docs_endpoint_renders_repo_relative_markdown_document(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        doc_path = "session_bootstrap/demo/openamp_control_plane_demo/README.md"
        expected_line = (REPO_ROOT / doc_path).read_text(encoding="utf-8").splitlines()[0]

        status, headers, body = request_text(state, "GET", f"/docs?path={quote(doc_path, safe='')}")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/html; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn(f"<title>{doc_path}</title>", body)
        self.assertIn(f'<div class="path">{doc_path}</div>', body)
        self.assertIn(html.escape(expected_line), body)

    def test_docs_endpoint_rejects_missing_invalid_and_missing_file_paths(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        cases = (
            ("/docs", 400, "missing path"),
            (f"/docs?path={quote('/etc/passwd', safe='')}", 400, "invalid path"),
            ("/docs?path=session_bootstrap/demo/openamp_control_plane_demo/not-real.md", 404, "file not found"),
        )

        for request_path, expected_status, expected_message in cases:
            with self.subTest(request_path=request_path):
                status, headers, body = request_text(state, "GET", request_path)
                self.assertEqual(status, expected_status)
                self.assertTrue(headers["content-type"].startswith("text/html"))
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertIn(expected_message, body)

    def test_docs_endpoint_pretty_prints_json_documents(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        doc_path = "session_bootstrap/reports/openamp_input_contract_fit_20260315_014542/fit_summary.json"
        raw_json = (REPO_ROOT / doc_path).read_text(encoding="utf-8")
        expected_json = html.escape(json.dumps(json.loads(raw_json), ensure_ascii=False, indent=2))

        status, headers, body = request_text(state, "GET", f"/docs?path={quote(doc_path, safe='')}")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/html; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn(f'<div class="path">{doc_path}</div>', body)
        self.assertIn(expected_json, body)


class DemoHTTPServerSocketSmokeTest(unittest.TestCase):
    def test_health_endpoint_smoke_via_real_localhost_socket(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        try:
            http_server = server.DemoHTTPServer(("127.0.0.1", 0), DemoRequestHandler, state)
        except PermissionError as exc:
            self.skipTest(f"Local socket binding is not permitted in this runtime: {exc}")

        server_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        server_thread.start()

        try:
            host, port = http_server.server_address
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(f"http://{host}:{port}/api/health", timeout=2) as response:
                status = response.status
                headers = dict(response.headers.items())
                payload = json.loads(response.read().decode("utf-8"))
        finally:
            http_server.shutdown()
            http_server.server_close()
            server_thread.join(timeout=2)

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(payload, {"status": "ok"})
        self.assertFalse(server_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
