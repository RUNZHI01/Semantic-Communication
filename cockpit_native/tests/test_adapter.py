from __future__ import annotations

from pathlib import Path
import unittest

from cockpit_native.adapter import DemoRepoAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DemoRepoAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = DemoRepoAdapter(project_root=PROJECT_ROOT)

    def test_latest_snapshot_path_uses_current_archive(self) -> None:
        snapshot_path = self.adapter.latest_snapshot_path()
        self.assertEqual(snapshot_path.name, "state_snapshot.json")
        self.assertEqual(snapshot_path.parent.name, "session_20260320_235724")

    def test_load_contract_bundle_reads_repo_backed_sources(self) -> None:
        bundle = self.adapter.load_contract_bundle()

        self.assertEqual(bundle.snapshot["aggregate"]["session_id"], "session_20260320_235724")
        self.assertEqual(bundle.snapshot["reason"], "job_fallback")
        self.assertEqual(bundle.aircraft_position["contract_version"], "aircraft_position.v1")
        self.assertEqual(bundle.aircraft_position["source_api_path"], "/api/aircraft-position")
        self.assertEqual(bundle.weak_network["recommended_scenario_id"], "snr10_bestcurrent")
        self.assertEqual(len(bundle.weak_network["scenarios"]), 3)

    def test_ui_state_exposes_expected_zones(self) -> None:
        ui_state = self.adapter.load_contract_bundle().ui_state

        self.assertIn("zones", ui_state)
        self.assertIn("left_status_panel", ui_state["zones"])
        self.assertIn("center_tactical_view", ui_state["zones"])
        self.assertIn("right_weak_network_panel", ui_state["zones"])
        self.assertIn("bottom_action_strip", ui_state["zones"])
        self.assertEqual(
            ui_state["zones"]["center_tactical_view"]["mission_call_sign"],
            "M9-DEMO",
        )


if __name__ == "__main__":
    unittest.main()
