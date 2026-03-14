from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from server import DashboardState  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
