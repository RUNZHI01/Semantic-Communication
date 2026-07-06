# USRP292x Analog Latent Test Path

这个目录在 `jscc_tran` 分支里只用于测试 analog latent-IQ 传输路线。接手时先只看这三个文件：

```text
AnalogLatentLink.py
RunAnalogLatentBatch.py
test_analog_latent_link.py
```

## 为什么这里只新增三个文件

原来的 USRP 收发服务不用重写。它们只是发送和捕获 `sc16` 文件，不关心文件里的波形语义。本分支已经包含这些复用文件：

```text
BuildOtaTools.sh
OtaTxPersistentServer.cpp
OtaRxPersistentServer.cpp
OtaTxPersistentServer.sh
OtaRxPersistentServer.sh
OtaTxControl.py
OtaRxControl.py
```

这三个新文件只负责把 LGJSCC latent 变成 analog I/Q，以及把 RX `sc16` 还原成 noisy latent。完整端到端还需要仓库其他位置的兼容修改：

```text
scripts/latent_transport.py
scripts/tvm_inference_helper.py
host_pic_to_latent/jscc/src/test_model.py
```

## 构建和启动复用的 USRP 服务

```bash
cd USRP292x
./BuildOtaTools.sh

# RX host
./OtaRxPersistentServer.sh

# TX host
./OtaTxPersistentServer.sh
```

`BuildOtaTools.sh` 在本分支里只编译 analog 路线需要的两个 persistent server。

## 文件作用

```text
AnalogLatentLink.py
  latent <-> analog sc16 waveform 的核心实现。
  make:  raw float latent -> tx_analog.sc16 + manifest.json
  decode: batch_rx.sc16 + manifest.json -> received_latent.npz + merged_round0.bin
  simulate-channel: 无设备时给 tx_analog.sc16 注入 CFO/AWGN/相位/DC，生成 batch_rx.sc16

RunAnalogLatentBatch.py
  批处理 runner。
  输出 image_*/merged_round0.bin，兼容现有 usrp_runtime.py 的后续扫描。

test_analog_latent_link.py
  普通软件 loopback 测试。
  不需要 USRP，先验证 waveform 和 decode 链路能跑通。
```

## 软件 loopback

```bash
python3 USRP292x/RunAnalogLatentBatch.py \
  --input latent.npz \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id smoke \
  --dry-run
```

## 软件 CFO/AWGN loopback

没有 NI-USRP-2922 时，可以先跑带信道扰动的 dry-run：

```bash
python3 USRP292x/RunAnalogLatentBatch.py \
  --input latent.npz \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id sim_cfo_3k_snr20 \
  --dry-run \
  --sim-cfo-hz 3000 \
  --sim-snr-db 20 \
  --sim-gain 0.85 \
  --sim-phase-deg 25
```

看这些文件：

```text
image_0000/simulate_channel_summary.json
image_0000/decode_summary.json
batch_spool_summary.json
```

`decode_summary.json` 里会记录 `estimated_cfo_hz`、`sync_metric`、`evm_rms`、`estimated_snr_db`、`latent_mse_vs_tx`。这些指标只能证明数字链路和算法能跑通，不能代替线缆/空口实测。

decode 默认开启 robust sync fallback：

```text
--sync-candidates 12
--min-sync-metric 0.25
--robust-cfo-max-hz 8000
--robust-cfo-step-hz 500
```

普通路径失败时会在 CFO grid 内重试同步。离线验证里，`3 kHz CFO + 5 dB SNR` 可以走 `robust-cfo-grid` 恢复；summary 里会记录 `normal_sync_error`、`robust_coarse_cfo_hz`、`robust_residual_cfo_hz`。

## 单文件 make/decode

```bash
python3 USRP292x/AnalogLatentLink.py make \
  --input latent.npz \
  --out-sc16 tx_analog.sc16 \
  --manifest manifest.json

python3 USRP292x/AnalogLatentLink.py decode \
  --rx-sc16 tx_analog.sc16 \
  --manifest manifest.json \
  --out-npz received_latent.npz \
  --out-wire merged_round0.bin \
  --summary-json decode_summary.json
```

## 可选 key-derived scrambling

控制面仍用 ML-KEM + AEAD 保护 manifest/metadata。analog payload 不做 GCM。需要数据面置乱时，只对 latent complex symbols 做 permutation/sign：

```bash
python3 USRP292x/AnalogLatentLink.py make \
  --input latent.npz \
  --out-sc16 tx_analog.sc16 \
  --manifest manifest.json \
  --scramble-key "$SESSION_KEY"

python3 USRP292x/AnalogLatentLink.py decode \
  --rx-sc16 batch_rx.sc16 \
  --manifest manifest.json \
  --out-npz received_latent.npz \
  --out-wire merged_round0.bin \
  --scramble-key "$SESSION_KEY"
```

也可以用 `--scramble-key-hex` 传 ML-KEM 会话材料的十六进制形式。manifest 只保存 fingerprint，不保存明文 key。

## 关键约束

```text
真实 USRP 模式设置 JSCC_CHANNEL_MODE=real-usrp。
不要在 RX 后再次注入软件 AWGN。
不要对 analog payload 做 AES-GCM/SM4-GCM。
不要用原始 latent SHA 判断 analog payload 是否成功。
QPSK/CRC/ARQ 只作为 reliable baseline。
NI-USRP-2922 第一版固定 5 MS/s、sps=4、sc16 amplitude=3000，从低 TX/RX gain 和衰减器开始。
模型侧第一版固定 global RMS，不做 per-channel normalization。
```

完整说明见：

```text
docs/analog_latent_iq_phy_full_proposal.md
docs/analog_latent_iq_phy.md
```
