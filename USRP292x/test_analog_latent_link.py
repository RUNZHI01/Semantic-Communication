#!/usr/bin/env python3
"""Regression tests for the analog latent-IQ USRP path."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALOG_LINK = PROJECT_ROOT / "USRP292x" / "AnalogLatentLink.py"
ANALOG_BATCH = PROJECT_ROOT / "USRP292x" / "RunAnalogLatentBatch.py"


def test_make_decode_clean_sc16_loopback_recovers_float_latent(tmp_path):
    rng = np.random.default_rng(123)
    latent = rng.standard_normal((1, 4, 8, 8)).astype(np.float32)
    input_path = tmp_path / "latent.npz"
    tx_sc16 = tmp_path / "tx_analog.sc16"
    manifest = tmp_path / "manifest.json"
    out_npz = tmp_path / "received_latent.npz"
    out_wire = tmp_path / "merged_round0.bin"
    summary = tmp_path / "decode_summary.json"
    np.savez(input_path, latent=latent)

    subprocess.run(
        [
            sys.executable,
            str(ANALOG_LINK),
            "make",
            "--input",
            str(input_path),
            "--out-sc16",
            str(tx_sc16),
            "--manifest",
            str(manifest),
            "--rate",
            "5000000",
            "--sps",
            "4",
            "--amp",
            "3000",
            "--cfo-pilot-symbols",
            "128",
            "--sync-pilot-symbols",
            "128",
            "--data-block-symbols",
            "256",
            "--mid-pilot-symbols",
            "32",
            "--zero-guard-samples",
            "256",
            "--tail-guard-samples",
            "256",
            "--no-rx-post-quantize",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )
    subprocess.run(
        [
            sys.executable,
            str(ANALOG_LINK),
            "decode",
            "--rx-sc16",
            str(tx_sc16),
            "--manifest",
            str(manifest),
            "--out-npz",
            str(out_npz),
            "--out-wire",
            str(out_wire),
            "--summary-json",
            str(summary),
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    with np.load(out_npz) as payload:
        recovered = payload["latent"]
    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))

    assert summary_data["sync_success"] is True
    assert summary_data["payload_is_bit_exact"] is False
    assert manifest_data["payload_is_bit_exact"] is False
    assert recovered.shape == latent.shape
    assert out_wire.is_file()
    assert float(np.mean(np.square(recovered - latent))) < 5.0e-4


def test_batch_runner_dry_run_writes_usrp_runtime_compatible_outputs(tmp_path):
    latent = np.linspace(-0.5, 0.5, num=1 * 4 * 4 * 4, dtype=np.float32).reshape(1, 4, 4, 4)
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    np.savez(input_dir / "case0.npz", latent=latent)
    run_root = tmp_path / "runs"

    subprocess.run(
        [
            sys.executable,
            str(ANALOG_BATCH),
            "--input-dir",
            str(input_dir),
            "--pattern",
            "*.npz",
            "--count",
            "1",
            "--run-root",
            str(run_root),
            "--run-id",
            "dry",
            "--dry-run",
            "--cfo-pilot-symbols",
            "128",
            "--sync-pilot-symbols",
            "128",
            "--data-block-symbols",
            "256",
            "--mid-pilot-symbols",
            "32",
            "--zero-guard-samples",
            "256",
            "--tail-guard-samples",
            "256",
            "--no-rx-post-quantize",
        ],
        check=True,
        cwd=PROJECT_ROOT,
    )

    image_dir = run_root / "dry" / "image_0000"
    summary = json.loads((run_root / "dry" / "batch_spool_summary.json").read_text(encoding="utf-8"))
    assert (image_dir / "tx_analog.sc16").is_file()
    assert (image_dir / "batch_rx.sc16").is_file()
    assert (image_dir / "manifest.json").is_file()
    assert (image_dir / "decode_summary.json").is_file()
    assert (image_dir / "merged_round0.bin").is_file()
    assert summary["phy"] == "analog-latent-iq"
    assert summary["images"][0]["passed"] is True
