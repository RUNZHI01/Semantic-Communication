#!/usr/bin/env python3
"""Tests for TVM helper channel selection without importing real TVM."""

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = PROJECT_ROOT / "scripts" / "tvm_inference_helper.py"


class _FakeOutput:
    def __init__(self, array):
        self._array = np.asarray(array, dtype=np.float32)

    def numpy(self):
        return self._array


def _load_helper(monkeypatch):
    fake_relax = types.ModuleType("tvm.relax")
    fake_tvm = types.ModuleType("tvm")
    fake_tvm.relax = fake_relax
    fake_tvm.cpu = lambda index=0: ("cpu", index)
    fake_tvm.runtime = types.SimpleNamespace(tensor=lambda array, dev: array)
    monkeypatch.setitem(sys.modules, "tvm", fake_tvm)
    monkeypatch.setitem(sys.modules, "tvm.relax", fake_relax)

    spec = importlib.util.spec_from_file_location("tvm_inference_helper_under_test", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_real_usrp_channel_mode_passes_latent_without_awgn(tmp_path, monkeypatch):
    helper = _load_helper(monkeypatch)
    latent = np.linspace(-1.0, 1.0, num=1 * 4 * 4 * 4, dtype=np.float32).reshape(1, 4, 4, 4)
    input_path = tmp_path / "latent.npz"
    np.savez(input_path, latent=latent)
    seen = []

    def fn(array):
        seen.append(np.asarray(array, dtype=np.float32).copy())
        return _FakeOutput(array)

    result, output = helper.run_inference(
        fn=fn,
        dev=object(),
        input_payload=str(input_path),
        snr=0.0,
        channel_mode="real-usrp",
    )

    assert result["status"] == "ok"
    assert result["channel_mode"] == "real-usrp"
    assert result["awgn_injected"] is False
    np.testing.assert_array_equal(seen[0], latent)
    np.testing.assert_array_equal(output, latent)


def test_sim_awgn_channel_mode_keeps_existing_noise_metrics(tmp_path, monkeypatch):
    helper = _load_helper(monkeypatch)
    latent = np.ones((1, 4, 4, 4), dtype=np.float32)
    input_path = tmp_path / "latent.npz"
    np.savez(input_path, latent=latent)
    seen = []
    np.random.seed(7)

    def fn(array):
        seen.append(np.asarray(array, dtype=np.float32).copy())
        return _FakeOutput(array)

    result, _ = helper.run_inference(
        fn=fn,
        dev=object(),
        input_payload=str(input_path),
        snr=10.0,
        channel_mode="sim-awgn",
    )

    assert result["status"] == "ok"
    assert result["channel_mode"] == "sim-awgn"
    assert result["awgn_injected"] is True
    assert "jscc_realized_awgn_snr_db" in result
    assert not np.array_equal(seen[0], latent)
