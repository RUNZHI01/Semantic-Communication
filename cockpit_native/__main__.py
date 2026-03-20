from __future__ import annotations

import argparse
import json
import sys

from .adapter import DemoRepoAdapter
from .availability import availability_report, is_pyside6_available
from .qt_app import launch_native_cockpit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native Qt/QML cockpit prototype for the current repo-backed demo.")
    parser.add_argument(
        "--smoke-import-check",
        action="store_true",
        help="Load the adapter layer and emit a JSON health summary without requiring PySide6.",
    )
    parser.add_argument(
        "--dump-ui-state",
        action="store_true",
        help="Print the normalized UI state as JSON and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter = DemoRepoAdapter()

    if args.smoke_import_check:
        bundle = adapter.load_contract_bundle()
        report = availability_report()
        report.update(
            {
                "snapshot_path": str(bundle.snapshot_path),
                "session_id": str((bundle.snapshot.get("aggregate") or {}).get("session_id") or ""),
                "aircraft_contract": str(bundle.aircraft_position.get("contract_version") or ""),
                "recommended_scenario_id": str(bundle.weak_network.get("recommended_scenario_id") or ""),
            }
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.dump_ui_state:
        print(json.dumps(adapter.load_contract_bundle().ui_state, ensure_ascii=False, indent=2))
        return 0

    if not is_pyside6_available():
        print(
            "PySide6 is not installed. Run `python3 -m cockpit_native --smoke-import-check` "
            "or install PySide6 to launch the QML shell.",
            file=sys.stderr,
        )
        return 2

    return launch_native_cockpit()


if __name__ == "__main__":
    raise SystemExit(main())
