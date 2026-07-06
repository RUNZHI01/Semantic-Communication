#!/usr/bin/env python3
"""Analog latent-IQ PHY for LGJSCC over NI-USRP-2922.

This module maps the continuous LGJSCC latent directly to complex I/Q symbols.
It intentionally does not provide bit-exact payload authentication for the
analog data plane; the output wire blob records the recovered noisy latent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from latent_transport import (  # noqa: E402
    _load_float32_latent,
    decode_transport_payload,
    pack_transport_frame,
    unpack_transport_frame,
)


DEFAULT_RATE = 5_000_000.0
DEFAULT_SPS = 4
DEFAULT_RRC_BETA = 0.35
DEFAULT_RRC_SPAN = 8
DEFAULT_SC16_AMPLITUDE = 3000
DEFAULT_ZERO_GUARD_SAMPLES = 4096
DEFAULT_TAIL_GUARD_SAMPLES = 4096
DEFAULT_CFO_PILOT_SYMBOLS = 1024
DEFAULT_SYNC_PILOT_SYMBOLS = 1024
DEFAULT_DATA_BLOCK_SYMBOLS = 4096
DEFAULT_MID_PILOT_SYMBOLS = 128
DEFAULT_CAPTURE_MARGIN_SAMPLES = 20_000
SAMPLE_BYTES = 4
EPS = 1.0e-12


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_batched_float32(array: np.ndarray) -> np.ndarray:
    arr = np.asarray(array, dtype=np.float32)
    if arr.ndim == 3:
        arr = np.expand_dims(arr, axis=0)
    return arr.astype(np.float32, copy=False)


def load_latent(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Load latent from .npz/.npy/.pt/raw .bin or an existing transport wire blob."""
    p = Path(path)
    if p.suffix == ".bin":
        blob = p.read_bytes()
        try:
            meta, payload_bytes = unpack_transport_frame(blob)
            decoded = decode_transport_payload(meta, payload_bytes, verify_latent_sha=True)
            latent = ensure_batched_float32(decoded.latent)
            return latent, {
                "shape": list(latent.shape),
                "dtype": "float32",
                "source_format": "transport-frame",
                "source_meta": meta,
            }
        except Exception:
            pass

    latent, info = _load_float32_latent(str(p))
    latent = ensure_batched_float32(latent)
    info = dict(info)
    info.setdefault("source_format", p.suffix.lstrip(".") or "raw")
    info["shape"] = list(latent.shape)
    info["dtype"] = "float32"
    return latent, info


def rrc_taps(beta: float, span: int, sps: int) -> np.ndarray:
    if sps < 2:
        raise ValueError("sps must be >= 2")
    if span < 2:
        raise ValueError("rrc span must be >= 2 symbols")
    if beta < 0.0 or beta > 1.0:
        raise ValueError("rrc beta must be in [0, 1]")

    half = span * sps / 2.0
    t = np.arange(-half, half + 1.0, dtype=np.float64) / float(sps)
    taps = np.zeros_like(t, dtype=np.float64)

    for idx, ti in enumerate(t):
        if abs(ti) < 1.0e-12:
            taps[idx] = 1.0 + beta * (4.0 / math.pi - 1.0)
        elif beta > 0.0 and abs(abs(4.0 * beta * ti) - 1.0) < 1.0e-10:
            taps[idx] = (
                beta
                / math.sqrt(2.0)
                * (
                    (1.0 + 2.0 / math.pi) * math.sin(math.pi / (4.0 * beta))
                    + (1.0 - 2.0 / math.pi) * math.cos(math.pi / (4.0 * beta))
                )
            )
        else:
            if beta == 0.0:
                taps[idx] = math.sin(math.pi * ti) / (math.pi * ti)
            else:
                numerator = (
                    math.sin(math.pi * ti * (1.0 - beta))
                    + 4.0 * beta * ti * math.cos(math.pi * ti * (1.0 + beta))
                )
                denominator = math.pi * ti * (1.0 - (4.0 * beta * ti) ** 2)
                taps[idx] = numerator / denominator

    energy = math.sqrt(float(np.sum(np.square(taps))))
    if energy <= 0.0:
        raise ValueError("invalid RRC taps: zero energy")
    return (taps / energy).astype(np.float32)


def make_pilot_symbols(count: int, seed: int) -> np.ndarray:
    if count <= 0:
        return np.zeros(0, dtype=np.complex64)
    rng = np.random.default_rng(int(seed))
    choices = rng.integers(0, 4, size=int(count), dtype=np.int16)
    table = np.asarray(
        [1.0 + 1.0j, 1.0 - 1.0j, -1.0 + 1.0j, -1.0 - 1.0j],
        dtype=np.complex64,
    ) / np.float32(math.sqrt(2.0))
    return table[choices].astype(np.complex64)


def latent_to_complex_symbols(latent: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(latent, dtype=np.float32).reshape(-1)
    n_real = int(x.size)
    real_rms = float(np.sqrt(np.mean(np.square(x, dtype=np.float64)) + 1.0e-8))
    u = x / np.float32(real_rms)
    if u.size % 2:
        u = np.pad(u, (0, 1), mode="constant")
    symbols = (u[0::2].astype(np.float32) + 1j * u[1::2].astype(np.float32)).astype(np.complex64)
    info = {
        "n_real": n_real,
        "n_complex": int(symbols.size),
        "real_rms": real_rms,
    }
    return symbols, info


def complex_symbols_to_latent(symbols: np.ndarray, manifest: dict[str, Any]) -> np.ndarray:
    n_real = int(manifest["n_real"])
    n_complex = int(manifest["n_complex"])
    shape = tuple(int(v) for v in manifest["shape"])
    real_rms = float(manifest["real_rms"])
    symbols = np.asarray(symbols[:n_complex], dtype=np.complex64)
    flat = np.empty(n_complex * 2, dtype=np.float32)
    flat[0::2] = np.real(symbols)
    flat[1::2] = np.imag(symbols)
    flat = flat[:n_real] * np.float32(real_rms)
    return flat.reshape(shape).astype(np.float32, copy=False)


def build_frame_symbols(data_symbols: np.ndarray, manifest: dict[str, Any]) -> np.ndarray:
    cfo = make_pilot_symbols(int(manifest["cfo_pilot_symbols"]), int(manifest["cfo_seed"]))
    sync = make_pilot_symbols(int(manifest["sync_pilot_symbols"]), int(manifest["sync_seed"]))
    mid = make_pilot_symbols(int(manifest["mid_pilot_symbols"]), int(manifest["mid_pilot_seed"]))
    block = int(manifest["data_block_symbols"])

    parts: list[np.ndarray] = [cfo, cfo, sync]
    block_lengths: list[int] = []
    pos = 0
    while pos < len(data_symbols):
        take = min(block, len(data_symbols) - pos)
        parts.append(data_symbols[pos:pos + take])
        block_lengths.append(int(take))
        pos += take
        if pos < len(data_symbols) and len(mid) > 0:
            parts.append(mid)
    manifest["data_block_lengths"] = block_lengths
    manifest["frame_symbols"] = int(sum(len(part) for part in parts))
    return np.concatenate(parts).astype(np.complex64)


def symbols_to_rrc_waveform(symbols: np.ndarray, taps: np.ndarray, sps: int) -> np.ndarray:
    upsampled = np.zeros(len(symbols) * int(sps), dtype=np.complex64)
    upsampled[:: int(sps)] = symbols
    return np.convolve(upsampled, taps.astype(np.float32), mode="full").astype(np.complex64)


def waveform_to_sc16(wave: np.ndarray, amplitude: int) -> tuple[np.ndarray, float, float]:
    peak = float(np.max(np.abs(wave)) + 1.0e-8)
    normalized = wave / np.float32(peak)
    i = np.clip(np.real(normalized) * float(amplitude), -32767, 32767).astype(np.int16)
    q = np.clip(np.imag(normalized) * float(amplitude), -32767, 32767).astype(np.int16)
    interleaved = np.empty(i.size * 2, dtype=np.int16)
    interleaved[0::2] = i
    interleaved[1::2] = q
    clipping_ratio = float(np.mean((np.abs(i) >= 32767) | (np.abs(q) >= 32767)))
    return interleaved, peak, clipping_ratio


def write_sc16(path: Path, interleaved: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved.astype(np.int16, copy=False).tofile(path)


def sc16_to_complex(path: Path, amplitude: int) -> tuple[np.ndarray, float]:
    raw = np.fromfile(path, dtype=np.int16)
    if raw.size % 2:
        raise ValueError(f"sc16 file has odd int16 count: {path}")
    clipping_ratio = float(np.mean((np.abs(raw[0::2]) >= 32767) | (np.abs(raw[1::2]) >= 32767))) if raw.size else 0.0
    complex_rx = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
    return (complex_rx / np.float32(amplitude)).astype(np.complex64), clipping_ratio


def matched_filter(rx: np.ndarray, taps: np.ndarray) -> np.ndarray:
    return np.convolve(rx, np.conj(taps[::-1]), mode="same").astype(np.complex64)


def find_sync(mf: np.ndarray, sync: np.ndarray, sps: int) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    sync_energy = float(np.vdot(sync, sync).real)
    if sync_energy <= 0.0:
        raise ValueError("sync pilot has zero energy")

    for phase in range(int(sps)):
        stream = mf[phase:: int(sps)]
        if stream.size < sync.size:
            continue
        corr = np.abs(np.correlate(stream, sync, mode="valid"))
        if corr.size == 0:
            continue
        idx = int(np.argmax(corr))
        window = stream[idx:idx + sync.size]
        rx_energy = float(np.vdot(window, window).real)
        metric = float(corr[idx] / math.sqrt(max(rx_energy * sync_energy, EPS)))
        candidate = {
            "phase": phase,
            "sync_start": idx,
            "sync_metric": metric,
            "sync_corr": float(corr[idx]),
            "sym_stream": stream,
        }
        if best is None or metric > float(best["sync_metric"]):
            best = candidate

    if best is None:
        raise RuntimeError("sync search failed: capture shorter than sync pilot")
    return best


def estimate_cfo_from_repeated_pilot(sym_stream: np.ndarray, sync_start: int, cfo_len: int, rate: float, sps: int) -> float:
    if cfo_len <= 0 or sync_start < 2 * cfo_len:
        return 0.0
    left = sym_stream[sync_start - 2 * cfo_len:sync_start - cfo_len]
    right = sym_stream[sync_start - cfo_len:sync_start]
    if left.size != cfo_len or right.size != cfo_len:
        return 0.0
    phase = float(np.angle(np.vdot(left, right)))
    symbol_rate = float(rate) / float(sps)
    return phase / (2.0 * math.pi * (float(cfo_len) / symbol_rate))


def correct_cfo(rx: np.ndarray, cfo_hz: float, rate: float) -> np.ndarray:
    if abs(cfo_hz) < 1.0e-9:
        return rx
    n = np.arange(rx.size, dtype=np.float64)
    rot = np.exp(-1j * 2.0 * math.pi * float(cfo_hz) * n / float(rate))
    return (rx * rot.astype(np.complex64)).astype(np.complex64)


def estimate_channel_gain(tx: np.ndarray, rx: np.ndarray) -> complex:
    if tx.size == 0 or rx.size < tx.size:
        return complex(1.0, 0.0)
    numerator = np.vdot(tx, rx[:tx.size])
    denominator = np.vdot(tx, tx)
    if abs(denominator) <= EPS:
        return complex(1.0, 0.0)
    gain = numerator / denominator
    if abs(gain) <= EPS:
        return complex(1.0, 0.0)
    return complex(gain)


def recover_payload_symbols(sym_stream: np.ndarray, sync_start: int, manifest: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    cfo_len = int(manifest["cfo_pilot_symbols"])
    sync_len = int(manifest["sync_pilot_symbols"])
    mid_len = int(manifest["mid_pilot_symbols"])
    cfo = make_pilot_symbols(cfo_len, int(manifest["cfo_seed"]))
    sync = make_pilot_symbols(sync_len, int(manifest["sync_seed"]))
    mid = make_pilot_symbols(mid_len, int(manifest["mid_pilot_seed"]))
    block_lengths = [int(v) for v in manifest["data_block_lengths"]]

    sync_rx = sym_stream[sync_start:sync_start + sync_len]
    if sync_rx.size < sync_len:
        raise RuntimeError("sync pilot extends beyond symbol stream")
    if sync_start >= 2 * cfo_len and cfo_len > 0:
        pilot_tx = np.concatenate([cfo, cfo, sync])
        pilot_rx = sym_stream[sync_start - 2 * cfo_len:sync_start + sync_len]
        current_gain = estimate_channel_gain(pilot_tx, pilot_rx)
    else:
        current_gain = estimate_channel_gain(sync, sync_rx)
    gains = [current_gain]
    payload_blocks: list[np.ndarray] = []
    cursor = sync_start + sync_len

    for block_idx, block_len in enumerate(block_lengths):
        block_rx = sym_stream[cursor:cursor + block_len]
        if block_rx.size < block_len:
            raise RuntimeError(f"payload block {block_idx} extends beyond symbol stream")
        payload_blocks.append((block_rx / np.complex64(current_gain)).astype(np.complex64))
        cursor += block_len
        if block_idx != len(block_lengths) - 1 and mid_len > 0:
            mid_rx = sym_stream[cursor:cursor + mid_len]
            if mid_rx.size < mid_len:
                raise RuntimeError(f"mid pilot {block_idx} extends beyond symbol stream")
            next_gain = estimate_channel_gain(mid, mid_rx)
            current_gain = next_gain if abs(next_gain) > EPS else current_gain
            gains.append(current_gain)
            cursor += mid_len

    payload = np.concatenate(payload_blocks).astype(np.complex64) if payload_blocks else np.zeros(0, dtype=np.complex64)
    metrics = {
        "data_start_symbol": int(sync_start + sync_len),
        "data_end_symbol": int(cursor),
        "channel_gain_real": float(np.real(gains[0])),
        "channel_gain_imag": float(np.imag(gains[0])),
        "channel_gain_abs": float(abs(gains[0])),
        "pilot_gains": [
            {"real": float(np.real(gain)), "imag": float(np.imag(gain)), "abs": float(abs(gain))}
            for gain in gains
        ],
    }
    return payload, metrics


def quantize_dequantize(latent: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    arr = np.asarray(latent, dtype=np.float32)
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    if max_val - min_val <= 1.0e-12:
        scale = 1.0
        zero_point = 0.0
        quant = np.zeros(arr.shape, dtype=np.uint8)
    else:
        scale = float((max_val - min_val) / 255.0)
        zero_point = float(np.clip(np.round(-min_val / scale), 0.0, 255.0))
        quant = np.clip(np.round(arr / scale + zero_point), 0.0, 255.0).astype(np.uint8)
    dequant = (quant.astype(np.float32) - np.float32(zero_point)) * np.float32(scale)
    return dequant.astype(np.float32, copy=False), {
        "quant": quant,
        "scale": np.asarray(scale, dtype=np.float32),
        "zero_point": np.asarray(zero_point, dtype=np.float32),
    }


def pack_received_wire_blob(latent: np.ndarray, manifest: dict[str, Any], summary: dict[str, Any]) -> bytes:
    latent = np.asarray(latent, dtype=np.float32)
    payload_bytes = latent.astype(np.float32, copy=False).tobytes()
    payload_sha = sha256_bytes(payload_bytes)
    meta = {
        "job_id": str(manifest.get("job_id") or "analog_latent"),
        "shape": list(latent.shape),
        "dtype": "float32",
        "payload_codec": "float32-raw",
        "sha256": payload_sha,
        "size": len(payload_bytes),
        "latent_sha256": payload_sha,
        "latent_size": len(payload_bytes),
        "phy": "analog-latent-iq",
        "payload_is_bit_exact": False,
        "rx_post_quantize": bool(manifest.get("rx_post_quantize", True)),
        "sync_success": bool(summary.get("sync_success", False)),
    }
    return pack_transport_frame(meta, payload_bytes)


def make_waveform(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input)
    out_sc16 = Path(args.out_sc16)
    manifest_path = Path(args.manifest)
    latent, source_info = load_latent(input_path)
    data_symbols, latent_info = latent_to_complex_symbols(latent)
    job_id = args.job_id or input_path.stem
    manifest: dict[str, Any] = {
        "version": 1,
        "phy": "analog-latent-iq",
        "job_id": job_id,
        "shape": list(latent.shape),
        "dtype": "float32",
        "normalization": "global_real_rms",
        "sample_rate": float(args.rate),
        "sps": int(args.sps),
        "rrc_beta": float(args.rrc_beta),
        "rrc_span": int(args.rrc_span),
        "sc16_amplitude": int(args.amp),
        "zero_guard_samples": int(args.zero_guard_samples),
        "tail_guard_samples": int(args.tail_guard_samples),
        "cfo_pilot_symbols": int(args.cfo_pilot_symbols),
        "sync_pilot_symbols": int(args.sync_pilot_symbols),
        "data_block_symbols": int(args.data_block_symbols),
        "mid_pilot_symbols": int(args.mid_pilot_symbols),
        "cfo_seed": int(args.cfo_seed),
        "sync_seed": int(args.sync_seed),
        "mid_pilot_seed": int(args.mid_pilot_seed),
        "rx_post_quantize": bool(args.rx_post_quantize),
        "payload_is_bit_exact": False,
        "source_path": str(input_path),
        "source_info": source_info,
        "tx_latent_sha256": sha256_bytes(latent.astype(np.float32, copy=False).tobytes()),
        "payload_symbol_rms": float(np.sqrt(np.mean(np.square(np.abs(data_symbols), dtype=np.float64)))),
        **latent_info,
    }

    frame_symbols = build_frame_symbols(data_symbols, manifest)
    taps = rrc_taps(float(args.rrc_beta), int(args.rrc_span), int(args.sps))
    shaped = symbols_to_rrc_waveform(frame_symbols, taps, int(args.sps))
    guarded = np.concatenate(
        [
            np.zeros(int(args.zero_guard_samples), dtype=np.complex64),
            shaped,
            np.zeros(int(args.tail_guard_samples), dtype=np.complex64),
        ]
    )
    interleaved, peak, clipping_ratio = waveform_to_sc16(guarded, int(args.amp))
    write_sc16(out_sc16, interleaved)

    waveform_samples = int(interleaved.size // 2)
    manifest.update({
        "rrc_tap_count": int(taps.size),
        "tx_waveform_samples": waveform_samples,
        "waveform_samples": waveform_samples,
        "capture_nsamps": int(waveform_samples + int(args.capture_margin_samples)),
        "capture_margin_samples": int(args.capture_margin_samples),
        "tx_peak": peak,
        "tx_clipping_ratio": clipping_ratio,
        "airtime_ms": float(1000.0 * waveform_samples / float(args.rate)),
        "symbol_rate": float(args.rate) / float(args.sps),
        "out_sc16": str(out_sc16),
    })
    write_json(manifest_path, manifest)
    return manifest


def decode_waveform(args: argparse.Namespace) -> dict[str, Any]:
    rx_sc16 = Path(args.rx_sc16)
    manifest = read_json(Path(args.manifest))
    out_npz = Path(args.out_npz)
    out_wire = Path(args.out_wire) if args.out_wire else None
    summary_path = Path(args.summary_json) if args.summary_json else None

    rate = float(manifest["sample_rate"])
    sps = int(manifest["sps"])
    amp = int(manifest["sc16_amplitude"])
    zero_guard = int(manifest["zero_guard_samples"])
    sync = make_pilot_symbols(int(manifest["sync_pilot_symbols"]), int(manifest["sync_seed"]))
    cfo_len = int(manifest["cfo_pilot_symbols"])
    taps = rrc_taps(float(manifest["rrc_beta"]), int(manifest["rrc_span"]), sps)

    rx, rx_clipping_ratio = sc16_to_complex(rx_sc16, amp)
    if rx.size == 0:
        raise RuntimeError(f"empty RX sc16 file: {rx_sc16}")
    dc_window = rx[:min(max(zero_guard, 1), rx.size)]
    dc = complex(np.mean(dc_window))
    rx_dc = (rx - np.complex64(dc)).astype(np.complex64)

    mf0 = matched_filter(rx_dc, taps)
    sync0 = find_sync(mf0, sync, sps)
    estimated_cfo_hz = estimate_cfo_from_repeated_pilot(
        sync0["sym_stream"],
        int(sync0["sync_start"]),
        cfo_len,
        rate,
        sps,
    )
    if abs(estimated_cfo_hz) < 5.0:
        estimated_cfo_hz = 0.0
    rx_corr = correct_cfo(rx_dc, estimated_cfo_hz, rate)
    mf = matched_filter(rx_corr, taps)
    sync_final = find_sync(mf, sync, sps)

    payload_symbols, payload_metrics = recover_payload_symbols(
        sync_final["sym_stream"],
        int(sync_final["sync_start"]),
        manifest,
    )
    n_complex = int(manifest["n_complex"])
    if payload_symbols.size < n_complex:
        raise RuntimeError(f"recovered {payload_symbols.size} symbols, expected {n_complex}")
    expected_symbol_rms = float(manifest.get("payload_symbol_rms") or 0.0)
    recovered_symbol_rms = float(np.sqrt(np.mean(np.square(np.abs(payload_symbols[:n_complex]), dtype=np.float64))))
    symbol_rms_gain = 1.0
    if expected_symbol_rms > 0.0 and recovered_symbol_rms > 0.0:
        symbol_rms_gain = expected_symbol_rms / recovered_symbol_rms
        payload_symbols = (payload_symbols * np.float32(symbol_rms_gain)).astype(np.complex64)

    latent_hat = complex_symbols_to_latent(payload_symbols[:n_complex], manifest)
    rx_post_quantize = bool(manifest.get("rx_post_quantize", True))
    npz_items: dict[str, Any]
    if rx_post_quantize:
        latent_out, quant_items = quantize_dequantize(latent_hat)
        npz_items = {"latent": latent_out, **quant_items}
    else:
        latent_out = latent_hat.astype(np.float32, copy=False)
        npz_items = {"latent": latent_out}

    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_npz, **npz_items)

    summary: dict[str, Any] = {
        "status": "ok",
        "phy": "analog-latent-iq",
        "sync_success": True,
        "payload_is_bit_exact": False,
        "rx_sc16": str(rx_sc16),
        "out_npz": str(out_npz),
        "out_wire": str(out_wire) if out_wire else "",
        "sample_rate": rate,
        "sps": sps,
        "sync_phase": int(sync_final["phase"]),
        "sync_start_symbol": int(sync_final["sync_start"]),
        "sync_metric": float(sync_final["sync_metric"]),
        "initial_sync_metric": float(sync0["sync_metric"]),
        "estimated_cfo_hz": float(estimated_cfo_hz),
        "dc_real": float(np.real(dc)),
        "dc_imag": float(np.imag(dc)),
        "rx_clipping_ratio": rx_clipping_ratio,
        "rx_post_quantize": rx_post_quantize,
        "received_latent_sha256": sha256_bytes(latent_out.astype(np.float32, copy=False).tobytes()),
        "payload_symbol_rms": expected_symbol_rms,
        "recovered_symbol_rms": recovered_symbol_rms,
        "symbol_rms_gain": float(symbol_rms_gain),
        "n_real": int(manifest["n_real"]),
        "n_complex": int(manifest["n_complex"]),
        "recovered_complex_symbols": int(payload_symbols.size),
        "latent_shape": list(latent_out.shape),
        "detected_airtime_ms": float(1000.0 * int(manifest["tx_waveform_samples"]) / rate),
    }
    summary.update(payload_metrics)

    if out_wire is not None:
        out_wire.parent.mkdir(parents=True, exist_ok=True)
        out_wire.write_bytes(pack_received_wire_blob(latent_out, manifest, summary))
    if summary_path is not None:
        write_json(summary_path, summary)
    return summary


def add_common_phy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE)
    parser.add_argument("--sps", type=int, default=DEFAULT_SPS)
    parser.add_argument("--rrc-beta", type=float, default=DEFAULT_RRC_BETA)
    parser.add_argument("--rrc-span", type=int, default=DEFAULT_RRC_SPAN)
    parser.add_argument("--amp", type=int, default=DEFAULT_SC16_AMPLITUDE)
    parser.add_argument("--zero-guard-samples", type=int, default=DEFAULT_ZERO_GUARD_SAMPLES)
    parser.add_argument("--tail-guard-samples", type=int, default=DEFAULT_TAIL_GUARD_SAMPLES)
    parser.add_argument("--cfo-pilot-symbols", type=int, default=DEFAULT_CFO_PILOT_SYMBOLS)
    parser.add_argument("--sync-pilot-symbols", type=int, default=DEFAULT_SYNC_PILOT_SYMBOLS)
    parser.add_argument("--data-block-symbols", type=int, default=DEFAULT_DATA_BLOCK_SYMBOLS)
    parser.add_argument("--mid-pilot-symbols", type=int, default=DEFAULT_MID_PILOT_SYMBOLS)
    parser.add_argument("--cfo-seed", type=int, default=1001)
    parser.add_argument("--sync-seed", type=int, default=1002)
    parser.add_argument("--mid-pilot-seed", type=int, default=1003)
    parser.add_argument("--capture-margin-samples", type=int, default=DEFAULT_CAPTURE_MARGIN_SAMPLES)
    parser.add_argument("--rx-post-quantize", dest="rx_post_quantize", action="store_true", default=True)
    parser.add_argument("--no-rx-post-quantize", dest="rx_post_quantize", action="store_false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analog latent-IQ PHY for USRP292x sc16 files.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    make = sub.add_parser("make")
    make.add_argument("--input", required=True)
    make.add_argument("--out-sc16", required=True)
    make.add_argument("--manifest", required=True)
    make.add_argument("--job-id", default="")
    add_common_phy_args(make)

    decode = sub.add_parser("decode")
    decode.add_argument("--rx-sc16", required=True)
    decode.add_argument("--manifest", required=True)
    decode.add_argument("--out-npz", required=True)
    decode.add_argument("--out-wire", default="")
    decode.add_argument("--summary-json", default="")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cmd == "make":
        manifest = make_waveform(args)
        print(json.dumps({
            "status": "ok",
            "manifest": args.manifest,
            "out_sc16": args.out_sc16,
            "tx_waveform_samples": manifest["tx_waveform_samples"],
            "capture_nsamps": manifest["capture_nsamps"],
        }, ensure_ascii=False))
        return 0
    if args.cmd == "decode":
        summary = decode_waveform(args)
        print(json.dumps({
            "status": "ok",
            "summary_json": args.summary_json,
            "sync_metric": summary["sync_metric"],
            "estimated_cfo_hz": summary["estimated_cfo_hz"],
        }, ensure_ascii=False))
        return 0
    raise RuntimeError(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
