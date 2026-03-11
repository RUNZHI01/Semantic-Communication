#!/usr/bin/env python3
import argparse
import glob
import hashlib
import json
import logging
import os
import statistics
import time
from pathlib import Path

import numpy as np
import tvm
from tvm import relax

try:
    import torch
except ImportError:
    torch = None

try:
    from PIL import Image
except ImportError:
    Image = None


LOGGER = logging.getLogger("current_real_reconstruction")


def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run current-style real reconstruction over latent inputs and emit benchmark-compatible timing logs."
    )
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--snr", type=float, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--variant", default="current")
    parser.add_argument("--expected-sha256", default="")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_tensor(array: np.ndarray, dev):
    runtime = getattr(tvm, "runtime", None)
    runtime_tensor_fn = getattr(runtime, "tensor", None) if runtime is not None else None
    if runtime_tensor_fn is None and runtime is not None:
        runtime_ndarray = getattr(runtime, "ndarray", None)
        if runtime_ndarray is not None:
            runtime_tensor_fn = lambda arr, device: runtime_ndarray.array(arr, device)
    if runtime_tensor_fn is None:
        raise AttributeError("module tvm.runtime has neither tensor nor ndarray.array")
    return runtime_tensor_fn(array, dev)


def ensure_batched_latent(latent: np.ndarray) -> np.ndarray:
    latent = np.asarray(latent, dtype=np.float32)
    if latent.ndim == 3:
        latent = np.expand_dims(latent, axis=0)
    if latent.ndim != 4:
        raise ValueError(f"expected latent with 3 or 4 dims, got shape={latent.shape}")
    return latent


def load_pt_quantized(path: Path) -> np.ndarray:
    if torch is None:
        raise RuntimeError(f"torch is required to load .pt latent inputs: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    required_keys = {"quant", "scale", "zero_point"}
    if not isinstance(payload, dict) or not required_keys.issubset(payload):
        raise KeyError(f"{path} is missing required keys: {sorted(required_keys)}")
    quant = np.asarray(payload["quant"], dtype=np.float32)
    scale = np.asarray(payload["scale"], dtype=np.float32)
    zero_point = np.asarray(payload["zero_point"], dtype=np.float32)
    latent = (quant - zero_point) * scale
    return ensure_batched_latent(latent)


def load_npz_latent(path: Path) -> np.ndarray:
    with np.load(path) as payload:
        if "latent" in payload:
            return ensure_batched_latent(payload["latent"])
        required_keys = {"quant", "scale", "zero_point"}
        if not required_keys.issubset(payload.files):
            raise KeyError(f"{path} is missing required keys: {sorted(required_keys)}")
        quant = np.asarray(payload["quant"], dtype=np.float32)
        scale = np.asarray(payload["scale"], dtype=np.float32)
        zero_point = np.asarray(payload["zero_point"], dtype=np.float32)
        latent = (quant - zero_point) * scale
        return ensure_batched_latent(latent)


def load_latent(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".pt":
        return load_pt_quantized(path)
    if suffix == ".npz":
        return load_npz_latent(path)
    if suffix == ".npy":
        return ensure_batched_latent(np.load(path))
    raise ValueError(f"unsupported input file type: {path}")


def awgn_channel(latent: np.ndarray, snr: float) -> np.ndarray:
    latent = np.asarray(latent, dtype=np.float32)
    power = np.mean(np.square(latent), axis=(-3, -2, -1), keepdims=True) * 2.0
    noise_power = power * (10.0 ** (-snr / 10.0))
    noise = np.sqrt(noise_power / 2.0) * np.random.standard_normal(latent.shape).astype(np.float32)
    return latent + noise


def normalize_image(output: np.ndarray) -> np.ndarray:
    array = np.asarray(output)
    if array.ndim == 4 and array.shape[0] == 1:
        array = array[0]
    if array.ndim == 3 and array.shape[0] in (1, 3, 4):
        array = np.transpose(array, (1, 2, 0))
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[:, :, 0]
    if array.ndim not in (2, 3):
        raise ValueError(f"cannot convert output with shape={array.shape} to image")
    array = np.clip(array, 0.0, 1.0)
    return (array * 255.0 + 0.5).astype(np.uint8)


def save_reconstruction(output: np.ndarray, output_stem: Path) -> Path:
    if Image is not None:
        image_array = normalize_image(output)
        save_path = output_stem.with_suffix(".png")
        Image.fromarray(image_array).save(save_path, format="PNG")
        return save_path
    save_path = output_stem.with_suffix(".npy")
    np.save(save_path, np.asarray(output))
    return save_path


def build_summary(
    args,
    artifact_path: Path,
    artifact_sha256: str,
    load_ms: float,
    vm_init_ms: float,
    run_samples_ms,
    processed_count: int,
    total_inputs: int,
    reconstructions_dir: Path,
    output_dtype: str,
    output_shape,
):
    summary = {
        "variant": args.variant,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "artifact_sha256_expected": args.expected_sha256 or None,
        "artifact_sha256_match": None
        if not args.expected_sha256
        else artifact_sha256 == args.expected_sha256.lower(),
        "input_dir": args.input_dir,
        "output_dir": str(reconstructions_dir),
        "output_count": len(list(reconstructions_dir.glob("*"))),
        "processed_count": processed_count,
        "input_count": total_inputs,
        "load_ms": round(load_ms, 3),
        "vm_init_ms": round(vm_init_ms, 3),
        "run_count": len(run_samples_ms),
        "run_samples_ms": [round(value, 3) for value in run_samples_ms],
        "run_median_ms": round(statistics.median(run_samples_ms), 3) if run_samples_ms else None,
        "run_mean_ms": round(sum(run_samples_ms) / len(run_samples_ms), 3) if run_samples_ms else None,
        "run_min_ms": round(min(run_samples_ms), 3) if run_samples_ms else None,
        "run_max_ms": round(max(run_samples_ms), 3) if run_samples_ms else None,
        "run_variance_ms2": round(statistics.pvariance(run_samples_ms), 6) if len(run_samples_ms) > 1 else 0.0,
        "output_shape": output_shape,
        "output_dtype": output_dtype,
        "snr": args.snr,
        "batch_size": args.batch_size,
        "save_format": "png" if Image is not None else "npy",
    }
    return summary


def main():
    configure_logging()
    args = parse_args()

    artifact_path = Path(args.artifact_path)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    reconstructions_dir = output_dir / "reconstructions"

    if not artifact_path.is_file():
        raise SystemExit(f"ERROR: artifact not found: {artifact_path}")
    if not input_dir.is_dir():
        raise SystemExit(f"ERROR: input dir not found: {input_dir}")

    expected_sha256 = args.expected_sha256.strip().lower()
    artifact_sha256 = file_sha256(artifact_path)
    if expected_sha256 and artifact_sha256 != expected_sha256:
        raise SystemExit(
            "ERROR: artifact sha256 mismatch "
            f"path={artifact_path} expected={expected_sha256} actual={artifact_sha256}"
        )

    reconstructions_dir.mkdir(parents=True, exist_ok=True)

    input_patterns = ("*.pt", "*.npz", "*.npy")
    input_files = []
    for pattern in input_patterns:
        input_files.extend(Path(path) for path in glob.glob(str(input_dir / pattern)))
    input_files = sorted({path.resolve(): path for path in input_files}.values())
    if not input_files:
        raise SystemExit(f"ERROR: no supported latent files found in {input_dir}")

    dev = tvm.cpu(0)
    load_t0 = time.perf_counter()
    lib = tvm.runtime.load_module(str(artifact_path))
    load_t1 = time.perf_counter()
    vm = relax.VirtualMachine(lib, dev)
    load_t2 = time.perf_counter()
    fn = vm["main"]
    LOGGER.info("TVM 模型加载成功")

    run_samples_ms = []
    processed_count = 0
    last_output = None

    for input_path in input_files:
        base_name = input_path.stem.split("_latent")[0]
        try:
            sample_t0 = time.perf_counter()
            latent = load_latent(input_path)
            noisy = awgn_channel(latent, args.snr).astype(np.float32)
            output = fn(runtime_tensor(noisy, dev))
            output_np = output.numpy() if hasattr(output, "numpy") else np.asarray(output)
            save_path = save_reconstruction(output_np, reconstructions_dir / f"{base_name}_recon")
            sample_t1 = time.perf_counter()
            elapsed_ms = (sample_t1 - sample_t0) * 1000.0
            LOGGER.info("批量推理时间（1 个样本）: %.6f 秒", elapsed_ms / 1000.0)
            LOGGER.info("重构图像保存至: %s", save_path)
            run_samples_ms.append(elapsed_ms)
            processed_count += 1
            last_output = output_np
        except Exception as err:  # pragma: no cover - exercised through runtime smoke.
            LOGGER.error("处理文件失败 %s: %s", input_path, err)

    LOGGER.info("处理完成: %s/%s 文件成功", processed_count, len(input_files))

    output_shape = None
    output_dtype = None
    if last_output is not None:
        output_shape = list(np.asarray(last_output).shape)
        output_dtype = str(np.asarray(last_output).dtype)

    summary = build_summary(
        args=args,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        load_ms=(load_t1 - load_t0) * 1000.0,
        vm_init_ms=(load_t2 - load_t1) * 1000.0,
        run_samples_ms=run_samples_ms,
        processed_count=processed_count,
        total_inputs=len(input_files),
        reconstructions_dir=reconstructions_dir,
        output_dtype=output_dtype,
        output_shape=output_shape,
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
