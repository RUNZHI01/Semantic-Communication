from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from .adapter import DemoRepoAdapter
from .availability import is_pyside6_available


def _env_int(name: str) -> int:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return 0
    try:
        return max(0, int(raw_value))
    except ValueError:
        return 0


def _resolve_safe_area_insets(overrides: Mapping[str, int] | None = None) -> dict[str, int]:
    resolved = {
        "left": _env_int("COCKPIT_NATIVE_SAFE_AREA_LEFT"),
        "top": _env_int("COCKPIT_NATIVE_SAFE_AREA_TOP"),
        "right": _env_int("COCKPIT_NATIVE_SAFE_AREA_RIGHT"),
        "bottom": _env_int("COCKPIT_NATIVE_SAFE_AREA_BOTTOM"),
    }
    if overrides is None:
        return resolved

    for key in resolved:
        raw_amount = overrides.get(key, resolved[key])
        resolved[key] = max(0, int(raw_amount))
    return resolved


SOFTWARE_RENDER_ENV_VARS = {
    "QT_QUICK_BACKEND": "software",
    "QSG_RHI_BACKEND": "software",
    "QT_OPENGL": "software",
}

OFFSCREEN_CAPTURE_ENV_VARS = {
    "QT_QPA_PLATFORM": "offscreen",
}


@dataclass
class QtCockpitRuntime:
    app: Any
    engine: Any
    root_window: Any


def apply_software_renderer_env(target: MutableMapping[str, str] | None = None) -> MutableMapping[str, str]:
    resolved = os.environ if target is None else target
    for key, value in SOFTWARE_RENDER_ENV_VARS.items():
        resolved.setdefault(key, value)
    return resolved


def apply_offscreen_capture_env(target: MutableMapping[str, str] | None = None) -> MutableMapping[str, str]:
    resolved = apply_software_renderer_env(target)
    for key, value in OFFSCREEN_CAPTURE_ENV_VARS.items():
        resolved.setdefault(key, value)
    return resolved


def _configure_renderer(software_render: bool) -> None:
    if not software_render:
        return
    apply_software_renderer_env()


def _create_cockpit_runtime(
    project_root: Path | None = None,
    *,
    software_render: bool = False,
    safe_area_insets: Mapping[str, int] | None = None,
    argv: Sequence[str] | None = None,
) -> QtCockpitRuntime:
    if not is_pyside6_available():
        raise RuntimeError("PySide6 is not available in this environment.")

    software_render = software_render or os.environ.get("COCKPIT_NATIVE_SOFTWARE_FALLBACK_ACTIVE") == "1"
    _configure_renderer(software_render)

    from PySide6.QtCore import QCoreApplication, QObject, Property, Qt, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface

    if software_render and hasattr(Qt, "AA_UseSoftwareOpenGL"):
        QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    if software_render and hasattr(QQuickWindow, "setGraphicsApi"):
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)

    adapter = DemoRepoAdapter(project_root=project_root)

    class CockpitBridge(QObject):
        stateChanged = Signal()

        def __init__(self, repo_adapter: DemoRepoAdapter, publish_state_json: Callable[[str], None]) -> None:
            super().__init__()
            self._adapter = repo_adapter
            self._publish_state_json = publish_state_json
            self._state: dict[str, object] = {}
            self._refresh_state()

        @Property("QVariant", notify=stateChanged)
        def state(self) -> dict[str, object]:
            return self._state

        @Property(str, notify=stateChanged)
        def stateJson(self) -> str:
            return json.dumps(self._state, ensure_ascii=False)

        def _refresh_state(self) -> None:
            self._state = self._adapter.load_contract_bundle().ui_state
            self._publish_state_json(json.dumps(self._state, ensure_ascii=False))

        @Slot()
        def reload(self) -> None:
            self._refresh_state()
            self.stateChanged.emit()

    app_argv = [str(item) for item in (list(argv) if argv is not None else sys.argv[:1])]
    if not app_argv:
        app_argv = ["cockpit_native"]

    app = QGuiApplication(app_argv)
    app.setApplicationName("Feiteng Native Cockpit Prototype")
    app.setOrganizationName("CICC0903540")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("cockpitUiStateJson", "{}")

    def publish_state_json(state_json: str) -> None:
        engine.rootContext().setContextProperty("cockpitUiStateJson", state_json)

    bridge = CockpitBridge(adapter, publish_state_json)
    primary_screen = app.primaryScreen()
    screen_metrics = {"width": 1440, "height": 900, "devicePixelRatio": 1.0}
    if primary_screen is not None:
        available = primary_screen.availableGeometry()
        screen_metrics = {
            "width": int(available.width()),
            "height": int(available.height()),
            "devicePixelRatio": float(primary_screen.devicePixelRatio()),
        }
    engine.rootContext().setContextProperty("cockpitBridge", bridge)
    engine.rootContext().setContextProperty("cockpitBridgeAvailable", True)
    engine.rootContext().setContextProperty("safeAreaInsets", _resolve_safe_area_insets(safe_area_insets))
    engine.rootContext().setContextProperty("screenMetrics", screen_metrics)
    engine.rootContext().setContextProperty("launchOptions", {"softwareRender": bool(software_render)})

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Unable to load QML scene: {qml_path}")
    return QtCockpitRuntime(app=app, engine=engine, root_window=engine.rootObjects()[0])


def launch_native_cockpit(
    project_root: Path | None = None,
    *,
    software_render: bool = False,
    safe_area_insets: Mapping[str, int] | None = None,
) -> int:
    runtime = _create_cockpit_runtime(
        project_root=project_root,
        software_render=software_render,
        safe_area_insets=safe_area_insets,
        argv=sys.argv[:1],
    )
    return runtime.app.exec()


def capture_native_cockpit(
    output_path: Path,
    project_root: Path | None = None,
    *,
    settle_ms: int = 500,
    safe_area_insets: Mapping[str, int] | None = None,
) -> Path:
    apply_offscreen_capture_env()

    runtime = _create_cockpit_runtime(
        project_root=project_root,
        software_render=True,
        safe_area_insets=safe_area_insets,
        argv=["cockpit_native.capture"],
    )
    from PySide6.QtCore import QTimer

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    runtime.root_window.show()

    failure: list[RuntimeError] = []

    def write_capture() -> None:
        image = runtime.root_window.grabWindow()
        if image.isNull():
            failure.append(RuntimeError("Offscreen cockpit capture produced an empty frame."))
        elif not image.save(str(resolved_output)):
            failure.append(RuntimeError(f"Unable to save cockpit capture to {resolved_output}"))
        runtime.app.quit()

    QTimer.singleShot(max(0, int(settle_ms)), write_capture)
    runtime.app.exec()
    if failure:
        raise failure[0]
    return resolved_output
