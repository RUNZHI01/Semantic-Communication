# Analog-Latent-IQ PHY for LGJSCC over NI-USRP-2922

本文档说明 `jscc_tran` 分支新增的 analog latent-IQ 主链路。目标是把 LGJSCC Encoder 输出的连续 latent 直接映射成 USRP I/Q 波形，让真实无线信道作用在语义 latent 上，而不是把 latent 当作可靠文件做 QPSK/CRC/ARQ 传输。

完整 0-16 Pro 方案见：

```text
docs/analog_latent_iq_phy_full_proposal.md
```

## 数据链路

主链路：

```text
image
 -> LGJSCC Encoder
 -> raw float latent
 -> global RMS normalization
 -> pair real values into complex I/Q symbols
 -> RRC pulse shaping
 -> sc16 waveform
 -> NI-USRP-2922 TX/RX
 -> DC correction from zero guard
 -> matched filter / timing / sync / CFO / complex gain equalization
 -> recovered noisy latent
 -> optional rx post quant-dequant compatibility layer
 -> Generator / TVM reconstruction
```

保留旧 QPSK 文件链路作为可靠 baseline，但 analog latent-IQ 不再使用 CRC/ARQ 判定 payload 成功，也不会用原始 latent SHA 作为 analog payload 成功条件。

## 新增和修改的文件

```text
USRP292x/AnalogLatentLink.py
USRP292x/RunAnalogLatentBatch.py
USRP292x/test_analog_latent_link.py
scripts/latent_transport.py
scripts/tvm_inference_helper.py
scripts/test_tvm_inference_channel_mode.py
host_pic_to_latent/jscc/src/test_model.py
docs/analog_latent_iq_phy.md
```

没有修改 USRP C++ persistent TX/RX 服务。

## 为什么 USRP292x 只新增三个文件

USRP 数据面新增文件只有：

```text
USRP292x/AnalogLatentLink.py
USRP292x/RunAnalogLatentBatch.py
USRP292x/test_analog_latent_link.py
```

这是有意设计，不是漏写。原来的 USRP 服务本身就是通用 `sc16` 收发器，可以继续复用。本分支已包含这些复用文件：

```text
USRP292x/BuildOtaTools.sh
USRP292x/OtaTxPersistentServer.cpp
USRP292x/OtaRxPersistentServer.cpp
USRP292x/OtaTxPersistentServer.sh
USRP292x/OtaRxPersistentServer.sh
USRP292x/OtaTxControl.py
USRP292x/OtaRxControl.py
```

`BuildOtaTools.sh` 在本分支里只编译 analog 路线需要的两个 persistent server，避免把 QPSK decoder 和其他旧工具链一起引入。

完整端到端还需要三处非 USRP 目录修改：

```text
scripts/latent_transport.py              支持 .pt raw float latent
scripts/tvm_inference_helper.py          real-usrp 模式禁用软件 AWGN
host_pic_to_latent/jscc/src/test_model.py 保存 raw latent，并在 real-usrp 模式禁用二次 AWGN
```

因此接手时可以按两层看：

```text
只测试 analog RF 数据面：
  看 USRP292x/AnalogLatentLink.py 和 USRP292x/RunAnalogLatentBatch.py

跑完整 JSCC 端到端：
  再看 latent_transport.py、tvm_inference_helper.py、test_model.py
```

## Encoder latent 输出

`host_pic_to_latent/jscc/src/test_model.py` 现在保存：

```python
{
    "latent": y_cpu.float(),
    "quant": q_tensor,
    "scale": scale,
    "zero_point": zero_point,
    "snr": self.args.snr,
    "config_str": self.args.config_str,
}
```

analog 主链路优先使用 `latent`。`quant/scale/zero_point` 继续保留给旧链路和兼容验证。

## AnalogLatentLink CLI

生成 TX waveform：

```bash
python3 USRP292x/AnalogLatentLink.py make \
  --input latent.npz \
  --out-sc16 tx_analog.sc16 \
  --manifest manifest.json \
  --rate 5000000 \
  --sps 4 \
  --amp 3000
```

解码 RX waveform：

```bash
python3 USRP292x/AnalogLatentLink.py decode \
  --rx-sc16 batch_rx.sc16 \
  --manifest manifest.json \
  --out-npz received_latent.npz \
  --out-wire merged_round0.bin \
  --summary-json decode_summary.json
```

输入支持：

```text
.npz with latent
.npy
.pt with latent
.bin raw float32
.bin latent_transport wire blob
```

默认 `rx_post_quantize=true`，可以用 `--no-rx-post-quantize` 对比纯 raw latent 输入 Generator 的效果。

## Batch Runner

`RunAnalogLatentBatch.py` 保持和 `usrp_runtime.py` 兼容的输出目录：

```text
run_dir/
  image_0000/
    tx_analog.sc16
    batch_rx.sc16
    manifest.json
    received_latent.npz
    decode_summary.json
    merged_round0.bin
  batch_spool_summary.json
```

dry-run 软件 loopback：

```bash
python3 USRP292x/RunAnalogLatentBatch.py \
  --input-dir USRP292x/payloads/finalwork_webp5 \
  --pattern '*.bin' \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id smoke \
  --dry-run
```

真实 USRP：

```bash
export MLKEM_USRP_RUNNER_SCRIPT=/path/to/USRP292x/RunAnalogLatentBatch.py
export USRP_RUN_ROOT=/path/to/USRP292x/analog_latent_runs
export JSCC_CHANNEL_MODE=real-usrp

python3 USRP292x/RunAnalogLatentBatch.py \
  --input latent.npz \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id cable_001
```

当前真实 RF runner 支持 `--rx-capture-mode=local`。如需两机 `remote-pull/remote-decode`，建议后续按 QPSK runner 的 SSH/SCP 模式补齐。

## 默认 PHY 参数

```text
sample_rate: 5 MS/s
sps: 4
symbol_rate: 1.25 MSym/s
rrc_beta: 0.35
rrc_span: 8
sc16_amplitude: 3000
zero_guard_samples: 4096
tail_guard_samples: 4096
cfo_pilot_symbols: 1024 repeated twice
sync_pilot_symbols: 1024
data_block_symbols: 4096
mid_pilot_symbols: 128
capture_margin_samples: 20000
rx_post_quantize: true
payload_is_bit_exact: false
```

## TVM / Generator 信道模式

`scripts/tvm_inference_helper.py` 新增：

```bash
--channel-mode sim-awgn|real-usrp|none
```

默认来自环境变量：

```bash
export JSCC_CHANNEL_MODE=real-usrp
```

行为：

```text
sim-awgn: 保持旧行为，推理前注入软件 AWGN
real-usrp: 不注入软件 AWGN，直接使用 USRP 恢复出的 latent
none: 不注入软件 AWGN，供纯链路验证使用
```

`host_pic_to_latent/jscc/src/test_model.py` 也使用同一个环境变量。真实 USRP 模式下不要二次加 AWGN。

## 安全面划分

控制面继续使用已有 ML-KEM + AEAD：

```text
manifest
job_id
nonce / anti-replay
session parameters
```

数据面保持 analog noisy latent：

```text
raw latent -> analog I/Q -> recovered noisy latent
```

不要对 analog I/Q payload 做 AES-GCM/SM4-GCM。GCM 是 bit-exact 认证机制，一个 bit 错就失败；这和 DeepJSCC 允许 noisy latent 平滑退化的目标冲突。后续可以从会话密钥派生 permutation/sign scrambling，但它应作用在 latent symbols 上，而不是把 payload 变回可靠字节加密传输。

## 验证路线

1. 软件 loopback：

```bash
python3 USRP292x/RunAnalogLatentBatch.py --input latent.npz --count 1 --dry-run
```

要求 `sync_success=true`，`merged_round0.bin` 可被现有远端 decode 流程读取。

2. 软件 CFO/AWGN：

在 `batch_rx.sc16` 上注入频偏和噪声，检查 `estimated_cfo_hz`、`sync_metric`、重建图像质量随 SNR 平滑下降。

3. 线缆加衰减器：

TX 到 RX 之间加至少 30 dB 衰减，从低增益开始。记录 clipping、CFO、sync metric、latent MSE、PSNR/MS-SSIM/LPIPS 和 wall time。

4. 近距离空口：

低 TX/RX gain 起步，逐步增加。不要用原始 latent SHA 判断 analog payload 成功。

## 常见坑

```text
不要 RX 后再加软件 AWGN。
不要用整帧均值做 DC correction，只用 zero guard。
不要对 analog payload 做 GCM。
不要把原始 latent SHA 当成功条件。
不要线缆直连高增益，NI-USRP-2922 RX 最大输入功率是 0 dBm。
先用 5 MS/s + sps=4 跑稳，再优化速度。
```
