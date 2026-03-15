from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_PATCH_PATH = (
    PROJECT_ROOT
    / "session_bootstrap"
    / "patches"
    / "phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch"
)
PATCH_HELPER_PATH = PROJECT_ROOT / "session_bootstrap" / "scripts" / "prepare_phytium_openamp_patch.sh"

BASELINE_SHA = "9478c8277b013ccbcae9dabaf72dd123efc7908405a359b951d7c85f780b8df8"
CURRENT_SHA = "6f236b07f9b0bf981b6762ddb72449e23332d2d92c76b38acdcadc1d9b536dc1"


class OpenAmpFirmwareAllowlistPatchTest(unittest.TestCase):
    def test_release_patch_uses_multi_sha_allowlist(self) -> None:
        patch_text = RELEASE_PATCH_PATH.read_text(encoding="utf-8")

        self.assertIn("ScTrustedArtifactEntry", patch_text)
        self.assertIn("sc_trusted_artifact_allowlist", patch_text)
        self.assertIn("sc_ctrl_is_trusted_artifact_sha", patch_text)
        self.assertIn(BASELINE_SHA, patch_text)
        self.assertIn(CURRENT_SHA, patch_text)
        self.assertNotIn("sc_trusted_sha256", patch_text)
        self.assertNotIn("memcmp(request.expected_sha256, sc_trusted_sha256", patch_text)

    def test_patch_helper_defaults_to_release_allowlist_patch(self) -> None:
        helper_text = PATCH_HELPER_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "phytium_openamp_for_linux_status_req_resp_release_v1.4.0_2026-03-14.patch",
            helper_text,
        )


if __name__ == "__main__":
    unittest.main()
