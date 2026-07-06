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

## 关键约束

```text
真实 USRP 模式设置 JSCC_CHANNEL_MODE=real-usrp。
不要在 RX 后再次注入软件 AWGN。
不要对 analog payload 做 AES-GCM/SM4-GCM。
不要用原始 latent SHA 判断 analog payload 是否成功。
QPSK/CRC/ARQ 只作为 reliable baseline。
```

完整说明见：

```text
docs/analog_latent_iq_phy_full_proposal.md
docs/analog_latent_iq_phy.md
```
