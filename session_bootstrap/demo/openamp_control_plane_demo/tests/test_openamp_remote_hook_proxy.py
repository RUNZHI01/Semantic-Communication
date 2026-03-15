from __future__ import annotations

import base64
import gzip
import io
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace
import unittest


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from openamp_remote_hook_proxy import build_bridge_bundle_base64, build_remote_command  # noqa: E402


class OpenampRemoteHookProxyTest(unittest.TestCase):
    def test_build_bridge_bundle_contains_bridge_runtime_files(self) -> None:
        bundle = base64.b64decode(build_bridge_bundle_base64())
        with gzip.GzipFile(fileobj=io.BytesIO(bundle), mode="rb") as gzip_file:
            with tarfile.open(fileobj=gzip_file, mode="r:") as archive:
                names = sorted(member.name for member in archive.getmembers())
                self.assertEqual(
                    names,
                    [
                        "openamp_mock/__init__.py",
                        "openamp_mock/protocol.py",
                        "session_bootstrap/scripts/openamp_rpmsg_bridge.py",
                    ],
                )
                bridge_source = archive.extractfile("session_bootstrap/scripts/openamp_rpmsg_bridge.py")
                protocol_source = archive.extractfile("openamp_mock/protocol.py")
                assert bridge_source is not None
                assert protocol_source is not None
                bridge_text = bridge_source.read().decode("utf-8")
                protocol_text = protocol_source.read().decode("utf-8")

        self.assertIn("def parse_args()", bridge_text)
        self.assertIn("class MessageType(IntEnum):", protocol_text)

    def test_build_remote_command_stages_bundle_without_remote_repo_lookup(self) -> None:
        args = SimpleNamespace(
            remote_output_root="/tmp/openamp_demo_hook",
            rpmsg_ctrl="/dev/rpmsg_ctrl0",
            rpmsg_dev="/dev/rpmsg0",
        )

        command = build_remote_command(args, phase="JOB_REQ", job_id=123)

        self.assertIn('STAGE_ROOT="$(mktemp -d /tmp/openamp_demo_bridge.XXXXXX)"', command)
        self.assertIn('STAGE_ROOT="$STAGE_ROOT" python3 - <<\'PY\'', command)
        self.assertIn('bundle = base64.b64decode(', command)
        self.assertIn(
            'python3 "$STAGE_ROOT/session_bootstrap/scripts/openamp_rpmsg_bridge.py"',
            command,
        )
        self.assertIn("OUTPUT_DIR=/tmp/openamp_demo_hook/123/job_req", command)
        self.assertNotIn("remote_project_root_missing", command)
        self.assertNotIn('cd "$PROJECT_ROOT"', command)


if __name__ == "__main__":
    unittest.main()
