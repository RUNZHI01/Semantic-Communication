from __future__ import annotations

from pathlib import Path
import unittest

from cockpit_native.qt_app import (
    build_launch_options,
    normalize_map_backend,
    resolve_optional_repo_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class QtAppLaunchOptionsTest(unittest.TestCase):
    def test_normalize_map_backend_accepts_known_values(self) -> None:
        self.assertEqual(normalize_map_backend("svg"), "svg")
        self.assertEqual(normalize_map_backend("QtLocation"), "qtlocation")
        self.assertEqual(normalize_map_backend(" canvas "), "canvas")

    def test_normalize_map_backend_falls_back_to_auto(self) -> None:
        self.assertEqual(normalize_map_backend(None), "auto")
        self.assertEqual(normalize_map_backend("mapbox"), "auto")

    def test_resolve_optional_repo_path_returns_file_uri(self) -> None:
        resolved = resolve_optional_repo_path(
            "cockpit_native/qml/assets/world-map.svg",
            project_root=PROJECT_ROOT,
        )

        self.assertTrue(resolved.startswith("file://"))
        self.assertIn("/cockpit_native/qml/assets/world-map.svg", resolved)

    def test_build_launch_options_reads_map_env(self) -> None:
        options = build_launch_options(
            project_root=PROJECT_ROOT,
            software_render=True,
            env={
                "COCKPIT_NATIVE_MAP_BACKEND": "svg",
                "COCKPIT_NATIVE_WORLD_MAP_BACKDROP": "cockpit_native/qml/assets/world-map.svg",
            },
        )

        self.assertTrue(options["softwareRender"])
        self.assertEqual(options["mapBackend"], "svg")
        self.assertTrue(str(options["worldMapBackdropSource"]).startswith("file://"))


if __name__ == "__main__":
    unittest.main()
