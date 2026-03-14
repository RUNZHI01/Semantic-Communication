from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from server import DashboardState, DemoRequestHandler  # noqa: E402


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


def request_json(
    state: DashboardState,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], dict[str, object]]:
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
    try:
        return status, headers, json.loads(response_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(response_body.decode("utf-8")) from exc


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


if __name__ == "__main__":
    unittest.main()
