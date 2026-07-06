# jscc_tran Handoff

这个分支只用于验证一条新的传输路线：

```text
LGJSCC raw float latent -> analog I/Q waveform -> USRP sc16 -> recovered noisy latent -> Generator/TVM
```

仓库里其他历史代码是基线工程内容。接手这条路线时，先只看下面这些文件。

## 必看文件

```text
USRP292x/AnalogLatentLink.py
USRP292x/RunAnalogLatentBatch.py
USRP292x/README.md
docs/analog_latent_iq_phy.md
```

## 为什么 USRP292x 只有三个新文件

不是整个方案只有三个代码文件，而是 USRP 数据面新增代码只有三个文件。

原因是原来的 USRP persistent server 已经是通用 `sc16` 收发器，不关心 `sc16` 里面承载的是 QPSK 还是 analog latent，所以这部分不重写。本分支已把这些复用文件也带上：

```text
USRP292x/BuildOtaTools.sh
USRP292x/OtaTxPersistentServer.cpp
USRP292x/OtaRxPersistentServer.cpp
USRP292x/OtaTxPersistentServer.sh
USRP292x/OtaRxPersistentServer.sh
USRP292x/OtaTxControl.py
USRP292x/OtaRxControl.py
```

`BuildOtaTools.sh` 在本分支里只编译 `OtaTxPersistentServer` 和 `OtaRxPersistentServer`，不再拉入 QPSK decoder。

新增的三个 USRP 文件负责 analog latent 路线：

```text
USRP292x/AnalogLatentLink.py         latent <-> analog sc16 waveform
USRP292x/RunAnalogLatentBatch.py     调用旧 OtaTx/OtaRx 服务并输出 merged_round0.bin
USRP292x/test_analog_latent_link.py  不接 USRP 的软件 loopback 测试
```

所以：

```text
只验证 analog RF 数据面：
  主要看 USRP292x 这三个新增文件

跑完整 Encoder -> USRP -> TVM/Generator：
  还要看 scripts/latent_transport.py
  还要看 scripts/tvm_inference_helper.py
  还要看 host_pic_to_latent/jscc/src/test_model.py
```

## 兼容现有流程的修改

```text
scripts/latent_transport.py
scripts/tvm_inference_helper.py
host_pic_to_latent/jscc/src/test_model.py
```

作用：

```text
latent_transport.py        支持从 .pt 读取 raw float latent
tvm_inference_helper.py    增加 JSCC_CHANNEL_MODE=real-usrp，真实 USRP 模式不再注入软件 AWGN
test_model.py              Encoder 输出同时保存 raw float latent
```

## 测试文件

```text
USRP292x/test_analog_latent_link.py
scripts/test_tvm_inference_channel_mode.py
scripts/test_latent_transport.py
```

## 软件 loopback 快速验证

准备一个包含 `latent` 的 `.npz`，然后运行：

```bash
python3 USRP292x/RunAnalogLatentBatch.py \
  --input latent.npz \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id smoke \
  --dry-run
```

成功后看：

```text
USRP292x/analog_latent_runs/smoke/image_0000/merged_round0.bin
USRP292x/analog_latent_runs/smoke/image_0000/decode_summary.json
USRP292x/analog_latent_runs/smoke/batch_spool_summary.json
```

`merged_round0.bin` 保持和原 `usrp_runtime.py` 后续 decode 扫描逻辑兼容。

## 真实 USRP 测试入口

先启动原有 C++ persistent TX/RX server，然后：

```bash
cd USRP292x
./BuildOtaTools.sh

# RX host
./OtaRxPersistentServer.sh

# TX host
./OtaTxPersistentServer.sh
```

```bash
export JSCC_CHANNEL_MODE=real-usrp
export MLKEM_USRP_RUNNER_SCRIPT=/path/to/USRP292x/RunAnalogLatentBatch.py
export USRP_RUN_ROOT=/path/to/USRP292x/analog_latent_runs

python3 USRP292x/RunAnalogLatentBatch.py \
  --input latent.npz \
  --count 1 \
  --run-root USRP292x/analog_latent_runs \
  --run-id cable_001
```

当前 runner 的真实 RF 模式支持本机 `--rx-capture-mode=local`。两机 remote pull/decode 还没有迁移，后续如果要双机跑，再把旧 QPSK runner 的 SSH/SCP 逻辑迁过来。

## 不要误用的旧链路

旧 QPSK/CRC/ARQ 链路只作为 reliable baseline，不是本分支要验证的主链路。

旧 `mlkem_link/` 里的 ML-KEM / AES-GCM / SM4-GCM 继续用于控制面 metadata，不用于 analog payload。analog payload 是 noisy latent，不做 GCM bit-exact 认证。

本分支的成功标准不是 bit-perfect：

```text
sync_success=true
能恢复出 shape 正确的 noisy latent
Generator/TVM 能重建图像
质量随真实信道平滑退化
```

不要用原始 latent SHA 判断 analog payload 是否传输成功。
