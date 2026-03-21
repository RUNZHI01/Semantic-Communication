from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "cockpit_native"


class OffscreenQmlLoadTest(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("PySide6") is not None, "PySide6 is required")
    def test_main_qml_loads_without_optional_context_properties(self) -> None:
        script = textwrap.dedent(
            """
            from __future__ import annotations

            import json
            from pathlib import Path

            from PySide6.QtCore import QTimer, qInstallMessageHandler
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtQml import QQmlApplicationEngine

            messages = []

            def handler(message_type, context, message):
                messages.append(message)

            qInstallMessageHandler(handler)
            app = QGuiApplication([])
            engine = QQmlApplicationEngine()
            engine.load(str(Path("qml/Main.qml").resolve()))
            QTimer.singleShot(0, app.quit)
            app.exec()

            markers = (
                "ReferenceError",
                "TypeError",
                "Cannot anchor to an item that isn't a parent or sibling",
                "Unable to assign [undefined] to QColor",
            )
            errors = [message for message in messages if any(marker in message for marker in markers)]
            print(json.dumps({"root_objects": len(engine.rootObjects()), "errors": errors}))
            """
        )

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["QT_QUICK_BACKEND"] = "software"
        env["QSG_RHI_BACKEND"] = "software"
        env["QT_OPENGL"] = "software"

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PACKAGE_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["root_objects"], 1)
        self.assertEqual(payload["errors"], [], msg="\n".join(payload["errors"]))


if __name__ == "__main__":
    unittest.main()
