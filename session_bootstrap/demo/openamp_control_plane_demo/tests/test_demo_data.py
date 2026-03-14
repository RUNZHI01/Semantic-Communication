from __future__ import annotations

from pathlib import Path
import sys
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from demo_data import build_snapshot  # noqa: E402


class DemoDataTest(unittest.TestCase):
    def test_snapshot_contains_expected_verdicts(self) -> None:
        snapshot = build_snapshot()
        self.assertIn("P0", snapshot["project"]["final_verdict"])
        self.assertEqual(snapshot["project"]["trusted_current_sha"], "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1")
        fit_by_id = {fit["fit_id"]: fit for fit in snapshot["fits"]}
        self.assertEqual(fit_by_id["FIT-01"]["status"], "PASS")
        self.assertEqual(fit_by_id["FIT-02"]["status"], "PASS")
        self.assertEqual(fit_by_id["FIT-03"]["status"], "PASS")
        self.assertEqual(fit_by_id["FIT-03"]["history"]["status"], "FAIL")

    def test_snapshot_uses_chunk4_performance_alignment(self) -> None:
        snapshot = build_snapshot()
        performance = snapshot["performance"]
        self.assertEqual(performance["artifact_sha"], snapshot["project"]["trusted_current_sha"])
        self.assertAlmostEqual(performance["micro_summary"]["payload_current_ms"], 130.219)
        self.assertAlmostEqual(performance["micro_summary"]["end_to_end_current_ms"], 230.339)
        self.assertAlmostEqual(performance["micro_summary"]["incremental_speedup_x"], 16.272)

    def test_live_probe_switches_mode(self) -> None:
        snapshot = build_snapshot(
            live_probe={
                "requested_at": "2026-03-15T12:00:00+0800",
                "reachable": True,
                "summary": "board reachable",
                "details": {"remoteproc": [{"name": "remoteproc0", "state": "running"}]},
            }
        )
        self.assertEqual(snapshot["mode"]["effective_label"], "Live cue active")
        self.assertTrue(snapshot["board"]["current_status"]["reachable"])


if __name__ == "__main__":
    unittest.main()
