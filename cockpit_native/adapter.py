from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class RepoContractPaths:
    project_root: Path
    demo_data_path: Path
    archive_root: Path


@dataclass(frozen=True)
class NativeContractBundle:
    snapshot_path: Path
    snapshot: JsonDict
    aircraft_position: JsonDict
    weak_network: JsonDict
    ui_state: JsonDict

    def as_dict(self) -> JsonDict:
        return {
            "snapshot_path": str(self.snapshot_path),
            "snapshot": self.snapshot,
            "aircraft_position": self.aircraft_position,
            "weak_network": self.weak_network,
            "ui_state": self.ui_state,
        }


class DemoRepoAdapter:
    def __init__(self, project_root: Path | None = None) -> None:
        resolved_root = (project_root or Path(__file__).resolve().parent.parent).resolve()
        self.paths = RepoContractPaths(
            project_root=resolved_root,
            demo_data_path=resolved_root / "session_bootstrap" / "demo" / "openamp_control_plane_demo" / "demo_data.py",
            archive_root=resolved_root
            / "session_bootstrap"
            / "demo"
            / "openamp_control_plane_demo"
            / "runtime"
            / "event_archives",
        )
        self._validate_sources()

    def _validate_sources(self) -> None:
        if not self.paths.demo_data_path.is_file():
            raise FileNotFoundError(f"Missing demo data source: {self.paths.demo_data_path}")
        if not self.paths.archive_root.is_dir():
            raise FileNotFoundError(f"Missing event archive root: {self.paths.archive_root}")

    @lru_cache(maxsize=1)
    def _demo_data_module(self) -> ModuleType:
        module_name = "_cockpit_native_demo_data"
        spec = importlib.util.spec_from_file_location(module_name, self.paths.demo_data_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load demo data module from {self.paths.demo_data_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def latest_snapshot_path(self) -> Path:
        candidates = sorted(self.paths.archive_root.glob("session_*/state_snapshot.json"))
        if not candidates:
            raise FileNotFoundError(f"No archive snapshots found under {self.paths.archive_root}")
        return max(candidates, key=lambda path: (path.parent.name, path.stat().st_mtime_ns))

    def load_snapshot(self) -> tuple[Path, JsonDict]:
        snapshot_path = self.latest_snapshot_path()
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return snapshot_path, payload

    def load_aircraft_position_contract(self) -> JsonDict:
        demo_data = self._demo_data_module()
        return dict(demo_data.build_aircraft_position_snapshot())

    def load_weak_network_contract(self) -> JsonDict:
        demo_data = self._demo_data_module()
        return dict(demo_data.build_weak_network_snapshot())

    def load_contract_bundle(self) -> NativeContractBundle:
        snapshot_path, snapshot = self.load_snapshot()
        aircraft_position = self.load_aircraft_position_contract()
        weak_network = self.load_weak_network_contract()
        ui_state = self._build_ui_state(
            snapshot_path=snapshot_path,
            snapshot=snapshot,
            aircraft_position=aircraft_position,
            weak_network=weak_network,
        )
        return NativeContractBundle(
            snapshot_path=snapshot_path,
            snapshot=snapshot,
            aircraft_position=aircraft_position,
            weak_network=weak_network,
            ui_state=ui_state,
        )

    def _build_ui_state(
        self,
        *,
        snapshot_path: Path,
        snapshot: JsonDict,
        aircraft_position: JsonDict,
        weak_network: JsonDict,
    ) -> JsonDict:
        aggregate = snapshot.get("aggregate") if isinstance(snapshot.get("aggregate"), dict) else {}
        jobs = aggregate.get("jobs") if isinstance(aggregate.get("jobs"), dict) else {}
        heartbeat = aggregate.get("heartbeat") if isinstance(aggregate.get("heartbeat"), dict) else {}
        link_profile = aggregate.get("link_profile") if isinstance(aggregate.get("link_profile"), dict) else {}
        aircraft_track = aircraft_position.get("track") if isinstance(aircraft_position.get("track"), list) else []
        weak_network_scenarios = weak_network.get("scenarios") if isinstance(weak_network.get("scenarios"), list) else []
        live_anchor = weak_network.get("live_anchor") if isinstance(weak_network.get("live_anchor"), dict) else {}
        recent_events = snapshot.get("recent_events") if isinstance(snapshot.get("recent_events"), list) else []
        last_event = recent_events[0] if recent_events else {}

        left_panel = {
            "title": "System / Board",
            "summary": "Read-only normalization of the current OpenAMP demo evidence state.",
            "rows": [
                {"label": "Session", "value": str(aggregate.get("session_id") or "unknown"), "tone": "neutral"},
                {"label": "Last Event", "value": str(aggregate.get("last_event_type") or "unknown"), "tone": "online"},
                {"label": "Last Event At", "value": str(aggregate.get("last_event_at") or ""), "tone": "neutral"},
                {
                    "label": "Jobs",
                    "value": (
                        f"submitted {int(jobs.get('submitted_count') or 0)} / "
                        f"rejected {int(jobs.get('rejected_count') or 0)} / "
                        f"done {int(jobs.get('done_count') or 0)}"
                    ),
                    "tone": "warning" if int(jobs.get("rejected_count") or 0) else "online",
                },
                {
                    "label": "Heartbeat",
                    "value": str(heartbeat.get("status") or "unknown"),
                    "tone": "online" if str(heartbeat.get("status") or "").lower() == "ok" else "warning",
                },
                {
                    "label": "Link Profile",
                    "value": str(link_profile.get("selected_profile_label") or "正常链路"),
                    "tone": "neutral",
                },
                {
                    "label": "Archive Snapshot",
                    "value": str(snapshot.get("reason") or "unknown"),
                    "tone": "warning",
                },
            ],
            "truth_note": str(snapshot.get("mode_boundary_note") or aggregate.get("mode_boundary_note") or ""),
            "snapshot_path": str(snapshot_path.relative_to(self.paths.project_root)),
        }

        center_panel = {
            "title": "Tactical / Aircraft View",
            "mission_call_sign": str(aircraft_position.get("mission_call_sign") or "M9-DEMO"),
            "aircraft_id": str(aircraft_position.get("aircraft_id") or "FT-AIR-01"),
            "source_label": str(aircraft_position.get("source_label") or ""),
            "source_status": str(aircraft_position.get("source_status") or ""),
            "position": dict(aircraft_position.get("position") or {}),
            "kinematics": dict(aircraft_position.get("kinematics") or {}),
            "fix": dict(aircraft_position.get("fix") or {}),
            "track": aircraft_track,
            "control_summary": {
                "link_profile": str(link_profile.get("selected_profile_label") or "正常链路"),
                "last_job_id": str(jobs.get("last_job_id") or ""),
                "last_event_message": str(last_event.get("message") or ""),
            },
        }

        right_panel = {
            "title": "Weak-Network Comparison",
            "summary": str(weak_network.get("summary") or ""),
            "truth_note": str(weak_network.get("truth_note") or ""),
            "recommended_scenario_id": str(weak_network.get("recommended_scenario_id") or ""),
            "live_anchor": live_anchor,
            "scenarios": weak_network_scenarios,
        }

        bottom_actions = {
            "title": "Action Strip",
            "actions": [
                {
                    "action_id": "reload_contracts",
                    "label": "Reload Contracts",
                    "tone": "online",
                    "enabled": True,
                    "note": "Reload repo-backed snapshot and contract builders.",
                },
                {
                    "action_id": "show_snapshot_path",
                    "label": "Show Snapshot",
                    "tone": "neutral",
                    "enabled": False,
                    "note": str(snapshot_path.relative_to(self.paths.project_root)),
                },
                {
                    "action_id": "recommended_link_profile",
                    "label": "Recommended Weak-Net",
                    "tone": "warning",
                    "enabled": False,
                    "note": str(weak_network.get("recommended_scenario_id") or ""),
                },
                {
                    "action_id": "aircraft_contract",
                    "label": "Aircraft Contract",
                    "tone": "neutral",
                    "enabled": False,
                    "note": str(aircraft_position.get("source_api_path") or "/api/aircraft-position"),
                },
            ],
        }

        return {
            "meta": {
                "title": "Feiteng Native Cockpit Prototype",
                "subtitle": "Qt/QML shell driven by the current repo-backed TVM/OpenAMP demo contracts.",
                "project_root": str(self.paths.project_root),
                "snapshot_path": str(snapshot_path),
            },
            "zones": {
                "left_status_panel": left_panel,
                "center_tactical_view": center_panel,
                "right_weak_network_panel": right_panel,
                "bottom_action_strip": bottom_actions,
            },
        }
