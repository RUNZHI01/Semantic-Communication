from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIGNED_MANIFEST_PATH = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_signed_manifest.py"
WRAPPER_PATH = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_control_wrapper.py"
TRUSTED_ARTIFACTS_PATH = PROJECT_ROOT / "session_bootstrap" / "scripts" / "openamp_trusted_artifacts.py"
FIXTURE_ARTIFACT_PATH = (
    PROJECT_ROOT / "session_bootstrap" / "examples" / "openamp_signed_manifest.fixture.artifact.so"
)
FIXTURE_MANIFEST_PATH = (
    PROJECT_ROOT / "session_bootstrap" / "examples" / "openamp_signed_manifest.fixture.manifest.json"
)
FIXTURE_BUNDLE_PATH = (
    PROJECT_ROOT / "session_bootstrap" / "examples" / "openamp_signed_manifest.fixture.bundle.json"
)
FIXTURE_PUBLIC_KEY_PATH = (
    PROJECT_ROOT / "session_bootstrap" / "examples" / "openamp_signed_manifest.fixture.public.pem"
)
FIXTURE_TRANSPORT_PATH = (
    PROJECT_ROOT / "session_bootstrap" / "examples" / "openamp_signed_manifest.fixture.transport.json"
)


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module {module_name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


signed_manifest = load_module("openamp_signed_manifest_test", SIGNED_MANIFEST_PATH)
trusted_artifacts = load_module("openamp_trusted_artifacts_test_signed", TRUSTED_ARTIFACTS_PATH)
wrapper = load_module("openamp_control_wrapper_test_signed", WRAPPER_PATH)


class SignedManifestToolsTest(unittest.TestCase):
    def generate_keypair(self, temp_dir: Path) -> tuple[Path, Path]:
        private_key = temp_dir / "signing.pem"
        public_key = temp_dir / "signing.pub.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "EC",
                "-pkeyopt",
                "ec_paramgen_curve:P-256",
                "-out",
                str(private_key),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "openssl",
                "pkey",
                "-in",
                str(private_key),
                "-pubout",
                "-out",
                str(public_key),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return private_key, public_key

    def test_build_manifest_records_artifact_sha_and_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_build_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"openamp-signed-manifest-test")

            manifest = signed_manifest.build_manifest(
                artifact_path=artifact_path,
                variant="current",
                key_id="dev-local-20260316",
                publisher_channel="openamp-dev",
                deadline_ms=12345,
                expected_outputs=300,
                job_flags="reconstruction",
            )

        self.assertEqual(
            manifest["artifact"]["sha256"],
            hashlib.sha256(b"openamp-signed-manifest-test").hexdigest(),
        )
        self.assertEqual(manifest["artifact"]["size_bytes"], len(b"openamp-signed-manifest-test"))
        self.assertEqual(manifest["job"]["deadline_ms"], 12345)
        self.assertEqual(manifest["job"]["expected_outputs"], 300)
        self.assertEqual(manifest["job"]["job_flags"], "reconstruction")
        self.assertEqual(manifest["publisher"]["key_id"], "dev-local-20260316")

    def test_sign_and_verify_round_trip_with_openssl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_roundtrip_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"round-trip-artifact")
            private_key, public_key = self.generate_keypair(temp_dir)

            bundle = signed_manifest.build_signed_manifest_bundle(
                artifact_path=artifact_path,
                variant="current",
                key_id="dev-local-20260316",
                publisher_channel="openamp-dev",
                deadline_ms=300000,
                expected_outputs=300,
                job_flags="reconstruction",
                private_key=private_key,
            )

            summary = signed_manifest.verify_signed_manifest_bundle(
                bundle,
                public_key=public_key,
                artifact_path=artifact_path,
            )

        self.assertTrue(summary["verified_locally"])
        self.assertTrue(summary["artifact_match"])
        self.assertEqual(summary["signature_algorithm"], "ecdsa-p256-sha256")
        self.assertEqual(summary["key_id"], "dev-local-20260316")
        self.assertEqual(summary["variant"], "current")

    def test_bundle_command_builds_and_signs_in_one_step(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_bundle_cmd_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"bundle-command-artifact")
            private_key, public_key = self.generate_keypair(temp_dir)
            output_path = temp_dir / "signed_bundle.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SIGNED_MANIFEST_PATH),
                    "bundle",
                    "--artifact",
                    str(artifact_path),
                    "--private-key",
                    str(private_key),
                    "--output",
                    str(output_path),
                    "--variant",
                    "current",
                    "--key-id",
                    "dev-local-20260316",
                    "--publisher-channel",
                    "openamp-dev",
                    "--deadline-ms",
                    "60000",
                    "--expected-outputs",
                    "300",
                    "--job-flags",
                    "reconstruction",
                    "--created-at",
                    "2026-03-16T16:00:00+0800",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            summary = json.loads(result.stdout)
            bundle = signed_manifest.load_signed_manifest_bundle(output_path)
            verify_summary = signed_manifest.verify_signed_manifest_bundle(
                bundle,
                public_key=public_key,
                artifact_path=artifact_path,
            )

        self.assertEqual(summary["command"], "bundle")
        self.assertEqual(summary["output"], str(output_path))
        self.assertEqual(summary["manifest_sha256"], bundle["manifest_sha256"])
        self.assertEqual(bundle["manifest"]["provenance"]["created_at"], "2026-03-16T16:00:00+0800")
        self.assertTrue(verify_summary["verified_locally"])
        self.assertTrue(verify_summary["artifact_match"])

    def test_verify_rejects_tampered_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_tamper_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"tamper-artifact")
            private_key, public_key = self.generate_keypair(temp_dir)

            bundle = signed_manifest.build_signed_manifest_bundle(
                artifact_path=artifact_path,
                variant="current",
                key_id="dev-local-20260316",
                publisher_channel="openamp-dev",
                deadline_ms=300000,
                expected_outputs=300,
                job_flags="reconstruction",
                private_key=private_key,
            )
            bundle["manifest"]["job"]["deadline_ms"] = 300001

            with self.assertRaises(ValueError) as raised:
                signed_manifest.verify_signed_manifest_bundle(
                    bundle,
                    public_key=public_key,
                    artifact_path=artifact_path,
                )

        self.assertIn("manifest_sha256", str(raised.exception))

    def test_wrapper_signed_manifest_mode_uses_manifest_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_wrapper_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"wrapper-artifact")
            private_key, public_key = self.generate_keypair(temp_dir)
            bundle = signed_manifest.build_signed_manifest_bundle(
                artifact_path=artifact_path,
                variant="current",
                key_id="dev-local-20260316",
                publisher_channel="openamp-dev",
                deadline_ms=42000,
                expected_outputs=300,
                job_flags="reconstruction",
                private_key=private_key,
            )
            bundle_path = temp_dir / "signed_bundle.json"
            signed_manifest.write_json(bundle_path, bundle)

            args = SimpleNamespace(
                expected_sha256="",
                trusted_artifact_label="",
                trusted_artifacts_file=str(trusted_artifacts.DEFAULT_TRUSTED_ARTIFACTS_PATH),
                variant="legacy-placeholder",
                admission_mode="signed_manifest_v1",
                signed_manifest_file=str(bundle_path),
                signed_manifest_public_key=str(public_key),
            )

            expected_sha256, trusted_artifact, source, signed_admission = wrapper.resolve_admission_context(args)
            payload = wrapper.build_job_req_payload(
                job_id=7,
                expected_sha256=expected_sha256,
                deadline_ms=int(signed_admission["deadline_ms"]),
                expected_outputs=int(signed_admission["expected_outputs"]),
                job_flags=str(signed_admission["job_flags"]),
                runner_cmd="echo noop",
                trusted_artifact=trusted_artifact,
                signed_admission=signed_admission,
            )

        self.assertEqual(source, "--signed-manifest-file")
        self.assertIsNone(trusted_artifact)
        self.assertIsNotNone(signed_admission)
        assert signed_admission is not None
        self.assertTrue(signed_admission["verified_locally"])
        self.assertEqual(expected_sha256, bundle["manifest"]["artifact"]["sha256"])
        self.assertEqual(signed_admission["variant"], "current")
        self.assertEqual(signed_admission["deadline_ms"], 42000)
        self.assertEqual(payload["signed_manifest"]["manifest_sha256"], bundle["manifest_sha256"])
        self.assertEqual(payload["signed_manifest"]["key_id"], "dev-local-20260316")

    def test_transport_plan_keeps_existing_job_req_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="signed_manifest_transport_") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            artifact_path = temp_dir / "optimized_model.so"
            artifact_path.write_bytes(b"transport-plan-artifact")
            private_key, _ = self.generate_keypair(temp_dir)

            bundle = signed_manifest.build_signed_manifest_bundle(
                artifact_path=artifact_path,
                variant="current",
                key_id="dev-local-20260316",
                publisher_channel="openamp-dev",
                deadline_ms=60000,
                expected_outputs=300,
                job_flags="reconstruction",
                private_key=private_key,
                created_at="2026-03-16T16:10:00+0800",
            )
            plan = signed_manifest.build_signed_admission_transport_plan(
                bundle,
                job_id=7301,
                key_slot=1,
                chunk_size=160,
                seq_start=1,
            )

        self.assertEqual(plan["schema"], "openamp_signed_admission_transport_plan/v1")
        self.assertEqual(plan["frames"][0]["phase"], "SIGNED_ADMISSION_BEGIN")
        self.assertEqual(plan["frames"][-1]["phase"], "JOB_REQ")
        self.assertEqual(plan["expected_job_req_payload_len"], 44)
        self.assertEqual(plan["frames"][-1]["payload_len"], 44)
        self.assertEqual(plan["frames"][-1]["payload"]["job_flags"], "reconstruction")
        self.assertEqual(plan["frames"][-1]["payload"]["flags"], 2)
        chunk_frames = [frame for frame in plan["frames"] if frame["phase"] == "SIGNED_ADMISSION_CHUNK"]
        self.assertGreaterEqual(len(chunk_frames), 1)
        self.assertTrue(all(frame["payload"]["chunk_len"] <= 160 for frame in chunk_frames))

    def test_committed_fixture_bundle_and_transport_plan_match_tool_output(self) -> None:
        manifest = signed_manifest.load_json(FIXTURE_MANIFEST_PATH)
        bundle = signed_manifest.load_signed_manifest_bundle(FIXTURE_BUNDLE_PATH)
        verify_summary = signed_manifest.verify_signed_manifest_bundle(
            bundle,
            public_key=FIXTURE_PUBLIC_KEY_PATH,
            artifact_path=FIXTURE_ARTIFACT_PATH,
        )
        fixture_transport = signed_manifest.load_json(FIXTURE_TRANSPORT_PATH)
        rebuilt_transport = signed_manifest.build_signed_admission_transport_plan(
            bundle,
            job_id=7301,
            key_slot=1,
            chunk_size=160,
            seq_start=1,
        )

        self.assertEqual(manifest, bundle["manifest"])
        self.assertTrue(verify_summary["verified_locally"])
        self.assertTrue(verify_summary["artifact_match"])
        self.assertEqual(fixture_transport, rebuilt_transport)


if __name__ == "__main__":
    unittest.main()
