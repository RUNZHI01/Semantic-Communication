from __future__ import annotations

from pathlib import Path
import sys
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from demo_data import build_prerecorded_inference_result, build_snapshot  # noqa: E402


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
        self.assertEqual(snapshot["mode"]["effective_label"], "在线读数可用")
        self.assertTrue(snapshot["board"]["current_status"]["reachable"])

    def test_cached_live_probe_is_labeled_as_saved(self) -> None:
        snapshot = build_snapshot(
            live_probe={
                "requested_at": "2026-03-15T12:00:00+0800",
                "reachable": True,
                "status": "success",
                "summary": "board reachable",
                "details": {"remoteproc": [{"name": "remoteproc0", "state": "running"}]},
                "_loaded_from_cache": True,
            }
        )
        self.assertIn("恢复最近一次只读 ssh 结果", snapshot["mode"]["summary"].lower())
        self.assertEqual(snapshot["board"]["current_status"]["label"], "保存的只读 SSH 探板")
        self.assertIn("上一次成功探板的保存记录", snapshot["board"]["current_status"]["summary"])

    def test_guided_demo_snapshot_contains_comparison_and_sample_catalog(self) -> None:
        snapshot = build_snapshot()
        guided_demo = snapshot["guided_demo"]

        self.assertIn("comparison", guided_demo)
        self.assertIn("sample_catalog", guided_demo)
        self.assertGreaterEqual(len(guided_demo["sample_catalog"]), 1)
        self.assertAlmostEqual(guided_demo["comparison"]["payload"]["baseline_ms"], 436.722)
        self.assertEqual(guided_demo["comparison"]["baseline_source"]["label"], "PyTorch 参考基线")
        self.assertAlmostEqual(guided_demo["comparison"]["end_to_end"]["current_ms"], 230.339)

    def test_snapshot_surfaces_latest_live_dualpath_status_report(self) -> None:
        snapshot = build_snapshot()
        latest = snapshot["latest_live_status"]

        self.assertEqual(latest["report_date"], "2026-03-17")
        self.assertEqual(latest["valid_instance"], "8115")
        self.assertEqual(latest["current"]["completed"], "300 / 300")
        self.assertEqual(latest["baseline"]["label"], "PyTorch 参考基线")
        self.assertEqual(latest["baseline"]["completed"], "300 / 300 (archive)")
        self.assertEqual(
            latest["report"]["path"],
            "session_bootstrap/reports/openamp_demo_live_dualpath_status_20260317.md",
        )
        self.assertEqual(snapshot["docs"][0]["path"], latest["report"]["path"])
        self.assertEqual(snapshot["docs"][1]["path"], "session_bootstrap/tmp/quality_metrics_inputs_20260312/reference/pytorch_reference_manifest.json")

    def test_prerecorded_baseline_uses_pytorch_reference_manifest(self) -> None:
        payload = build_prerecorded_inference_result(0, "baseline")

        self.assertEqual(payload["execution_mode"], "reference")
        self.assertEqual(payload["source_label"], "PyTorch 参考基线")
        self.assertIn("PyTorch reference manifest", payload["message"])
        self.assertEqual(
            payload["evidence"][0]["path"],
            "session_bootstrap/tmp/quality_metrics_inputs_20260312/reference/pytorch_reference_manifest.json",
        )


if __name__ == "__main__":
    unittest.main()
