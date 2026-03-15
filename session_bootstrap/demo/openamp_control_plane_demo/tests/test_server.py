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
        )
        events: list[str] = []
        fake_app_state = Mock()
        fake_server = Mock()

        def build_state(probe_env: str, probe_timeout_sec: float) -> Mock:
            events.append("state_init")
            self.assertEqual(probe_env, args.probe_env)
            self.assertEqual(probe_timeout_sec, args.probe_timeout_sec)
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

        state_cls.assert_called_once_with(args.probe_env, args.probe_timeout_sec)
        server_cls.assert_called_once_with((args.host, args.port), DemoRequestHandler, fake_app_state)
        fake_app_state.refresh_live_probe.assert_not_called()
        fake_server.serve_forever.assert_called_once_with()
        self.assertEqual(exit_code, 0)
        self.assertEqual(events, ["state_init", "server_init", "serve_forever"])
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "OpenAMP demo dashboard: http://0.0.0.0:8090",
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
        )
        events: list[str] = []
        fake_app_state = Mock()
        fake_server = Mock()

        def build_state(probe_env: str, probe_timeout_sec: float) -> Mock:
            events.append("state_init")
            self.assertEqual(probe_env, args.probe_env)
            self.assertEqual(probe_timeout_sec, args.probe_timeout_sec)
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

        state_cls.assert_called_once_with(args.probe_env, args.probe_timeout_sec)
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
        self.assertEqual(payload["project"]["name"], "TVM MetaSchedule Execution Project")
        self.assertEqual(payload["mode"]["effective_label"], "仅展示证据")
        self.assertIn("current_status", payload["board"])
        self.assertIn("fits", payload)
        self.assertIsInstance(payload["fits"], list)

    def test_health_endpoint_returns_ok_payload(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(state, "GET", "/api/health")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(payload, {"status": "ok"})

    def test_system_status_endpoint_preloads_repo_defaults_without_password(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, payload = request_json(state, "GET", "/api/system-status")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(payload["execution_mode"]["label"], "待补全密码")
        self.assertTrue(payload["board_access"]["configured"])
        self.assertFalse(payload["board_access"]["has_password"])
        self.assertEqual(payload["board_access"]["host"], "100.121.87.73")
        self.assertEqual(payload["board_access"]["user"], "user")
        self.assertEqual(payload["board_access"]["port"], 22)
        self.assertEqual(
            payload["board_access"]["env_file"],
            "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
        )
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
            "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
        )
        self.assertNotIn("password", payload["board_access"])

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

    def test_board_access_endpoint_accepts_password_only_and_keeps_preloaded_defaults(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

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
        self.assertEqual(
            payload["board_access"]["env_file"],
            "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
        )
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
        self.assertEqual(payload["status_category"], "config_error")
        self.assertIn("配置不完整或不可用", payload["message"])
        self.assertEqual(payload["live_attempt"]["status"], "config_error")
        self.assertEqual(payload["live_attempt"]["missing_fields"], ["password"])
        self.assertIn("guided_demo", state.current_snapshot())

    def test_run_inference_endpoint_uses_preloaded_env_after_password_only_save(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)
        request_json(
            state,
            "POST",
            "/api/session/board-access",
            body=json.dumps({"password": "demo-pass"}).encode("utf-8"),
        )

        with patch(
            "server.run_remote_reconstruction",
            return_value={
                "status": "success",
                "execution_mode": "live",
                "variant": "current",
                "message": "live ok",
                "runner_summary": {
                    "load_ms": 3.2,
                    "vm_init_ms": 0.8,
                    "run_median_ms": 128.4,
                    "artifact_sha256": "abcd" * 16,
                },
            },
        ) as run_reconstruction:
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "live")
        access = run_reconstruction.call_args.args[0]
        trusted_current_sha = state.current_snapshot()["project"]["trusted_current_sha"]
        self.assertEqual(access.host, "100.121.87.73")
        self.assertEqual(access.user, "user")
        self.assertEqual(access.password, "demo-pass")
        self.assertEqual(
            access.env_file,
            REPO_ROOT / "session_bootstrap/config/inference_real_reconstruction_compare.2026-03-11.phytium_pi.env",
        )
        self.assertEqual(access.build_env()["INFERENCE_CURRENT_EXPECTED_SHA256"], trusted_current_sha)

    def test_run_inference_endpoint_uses_live_runner_when_available(self) -> None:
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

        with patch(
            "server.run_remote_reconstruction",
            return_value={
                "status": "success",
                "execution_mode": "live",
                "variant": "current",
                "message": "live ok",
                "runner_summary": {
                    "load_ms": 3.2,
                    "vm_init_ms": 0.8,
                    "run_median_ms": 128.4,
                    "artifact_sha256": "abcd" * 16,
                },
            },
        ) as run_reconstruction:
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "live")
        self.assertEqual(payload["source_label"], "在线计时 + 预录图像")
        self.assertAlmostEqual(payload["timings"]["total_ms"], 132.4)
        self.assertEqual(payload["artifact_sha"], "abcd" * 16)
        run_reconstruction.assert_called_once()

    def test_run_inference_endpoint_hides_raw_auth_stderr_in_primary_message(self) -> None:
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

        with patch(
            "server.run_remote_reconstruction",
            return_value={
                "status": "error",
                "status_category": "auth_error",
                "execution_mode": "fallback",
                "variant": "current",
                "message": "远端推理认证失败，请检查板卡用户名、密码或 SSH 端口设置。 当前已回退到预录结果。",
                "missing_fields": [],
                "diagnostics": {"stderr": "Permission denied (publickey,password).", "returncode": 255},
            },
        ):
            status, _, payload = request_json(
                state,
                "POST",
                "/api/run-inference",
                body=json.dumps({"image_index": 0, "mode": "current"}).encode("utf-8"),
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload["execution_mode"], "prerecorded")
        self.assertEqual(payload["status_category"], "auth_error")
        self.assertIn("认证失败", payload["message"])
        self.assertNotIn("Permission denied", payload["message"])
        self.assertEqual(payload["live_attempt"]["diagnostics"]["stderr"], "Permission denied (publickey,password).")

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

    def test_root_serves_dashboard_entry_page(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/")

        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("<title>OpenAMP 四幕交互演示系统</title>", body)
        self.assertIn("OpenAMP 控制面四幕交互演示", body)
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

    def test_app_css_serves_dashboard_stylesheet(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/app.css")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "text/css; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn(":root {", body)
        self.assertIn("--accent: #c95d12;", body)

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
