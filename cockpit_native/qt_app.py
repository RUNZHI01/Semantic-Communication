from __future__ import annotations

from pathlib import Path
import sys

from .adapter import DemoRepoAdapter
from .availability import is_pyside6_available


def launch_native_cockpit(project_root: Path | None = None) -> int:
    if not is_pyside6_available():
        raise RuntimeError("PySide6 is not available in this environment.")

    from PySide6.QtCore import QObject, Property, Signal, Slot
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    adapter = DemoRepoAdapter(project_root=project_root)

    class CockpitBridge(QObject):
        stateChanged = Signal()

        def __init__(self, repo_adapter: DemoRepoAdapter) -> None:
            super().__init__()
            self._adapter = repo_adapter
            self._state = repo_adapter.load_contract_bundle().ui_state

        @Property("QVariant", notify=stateChanged)
        def state(self) -> dict[str, object]:
            return self._state

        @Slot()
        def reload(self) -> None:
            self._state = self._adapter.load_contract_bundle().ui_state
            self.stateChanged.emit()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Feiteng Native Cockpit Prototype")
    engine = QQmlApplicationEngine()
    bridge = CockpitBridge(adapter)
    engine.rootContext().setContextProperty("cockpitBridge", bridge)

    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(str(qml_path))
    if not engine.rootObjects():
        raise RuntimeError(f"Unable to load QML scene: {qml_path}")
    return app.exec()
