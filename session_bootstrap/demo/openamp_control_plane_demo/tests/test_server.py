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

        self.assertEqual(snapshot["mode"]["effective_label"], "Live cue active")
        self.assertEqual(snapshot["board"]["current_status"]["label"], "Saved read-only SSH probe")
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
        self.assertEqual(payload["mode"]["effective_label"], "Fallback evidence mode")
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

    def test_probe_board_endpoint_updates_snapshot_after_success(self) -> None:
        success = live_probe_payload("2026-03-15T12:00:00+0800", "board reachable")
        state = DashboardState(None, 30.0, probe_cache_path=None)

        with patch("server.run_live_probe", return_value=success):
            probe_status, _, probe_payload = request_json(state, "POST", "/api/probe-board", body=b"{}")
            snapshot_status, _, snapshot_payload = request_json(state, "GET", "/api/snapshot")

        self.assertEqual(probe_status, 200)
        self.assertEqual(probe_payload, success)
        self.assertEqual(snapshot_status, 200)
        self.assertEqual(snapshot_payload["mode"]["effective_label"], "Live cue active")
        self.assertEqual(snapshot_payload["board"]["current_status"]["label"], "Fresh read-only SSH probe")
        self.assertEqual(snapshot_payload["board"]["current_status"]["requested_at"], success["requested_at"])
        self.assertTrue(snapshot_payload["board"]["current_status"]["reachable"])

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
        self.assertEqual(snapshot_payload["mode"]["effective_label"], "Fallback evidence mode")
        self.assertEqual(snapshot_payload["board"]["current_status"]["label"], "No fresh live probe")
        self.assertFalse(snapshot_payload["board"]["current_status"]["reachable"])
        self.assertEqual(snapshot_payload["board"]["current_status"]["requested_at"], "")

    def test_root_serves_dashboard_entry_page(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/")

        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("<title>OpenAMP Control Plane Demo</title>", body)
        self.assertIn("OpenAMP control-plane status, FIT evidence, and performance in one place.", body)
        self.assertIn('<script src="/app.js"></script>', body)

    def test_app_js_serves_dashboard_javascript(self) -> None:
        state = DashboardState(None, 30.0, probe_cache_path=None)

        status, headers, body = request_text(state, "GET", "/app.js")

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/javascript; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("const state = {", body)
        self.assertIn('fetch("/api/snapshot"', body)

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
