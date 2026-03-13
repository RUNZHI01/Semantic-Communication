# Phase 5 本地从核 Patch 构建尝试记录

> 日期：2026-03-14  
> 目标：在本机 `/tmp/phytium-standalone-sdk` 上真实应用 `STATUS_REQ/RESP` 从核 patch，并尝试本地编译新的 `openamp_core0.elf`。  
> 范围：本轮只在本机临时 SDK 工作副本上操作，不修改远端飞腾派 firmware。  
> 关联前置：
> - `session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_2026-03-14.patch`
> - `session_bootstrap/runbooks/phytium_openamp_for_linux_status_req_resp_patch_runbook_2026-03-14.md`
> - `session_bootstrap/scripts/prepare_phytium_openamp_patch.sh`
> - `session_bootstrap/reports/openamp_phase5_source_entry_discovery_2026-03-14.md`

## 1. 本轮结论

本轮已经完成了以下关键动作：

1. 已确认 `/tmp/phytium-standalone-sdk` 是干净 git 工作树。
2. 已确认 patch 状态为：
   - `git apply --check` 成功
   - `git apply --reverse --check` 失败
   - 说明 patch **尚未应用但可干净应用**。
3. 已在本地 SDK 工作副本上成功执行：

```bash
git -C /tmp/phytium-standalone-sdk apply \
  /home/tianxing/tvm_metaschedule_execution_project/session_bootstrap/patches/phytium_openamp_for_linux_status_req_resp_2026-03-14.patch
```

4. 已确认 patch 只改了一个官方源码文件：

- `example/system/amp/openamp_for_linux/src/slaver_00_example.c`

5. 已继续尝试本地构建，但构建未成功；当前真实 blocker 已经从“找不到源码”切换成：

**本机缺少 `aarch64-none-elf-gcc` 交叉工具链，导致无法把已打 patch 的 SDK 重新编成新的 `openamp_core0.elf`。**

## 2. patch 应用结果

本地 SDK 工作树状态：

- patch 已应用
- `git -C /tmp/phytium-standalone-sdk diff --stat` 显示：
  - `openamp_for_linux/src/slaver_00_example.c` 被修改
  - 约 `129 insertions(+), 78 deletions(-)`

说明当前的 `STATUS_REQ/RESP` 最小改造已经真实落入 SDK 工作副本，而不是停留在仓库 patch 文件层面。

## 3. 构建尝试过程

### 3.1 `make load_kconfig` 结果

执行：

```bash
cd /tmp/phytium-standalone-sdk/example/system/amp/openamp_for_linux
make load_kconfig LOAD_CONFIG_NAME=pe2204_aarch64_phytiumpi_openamp_core0
```

结果：

- 配置文件已成功复制到本地 `sdkconfig`
- 但后续 `menuconfig_autosave.py` 因 curses/TTY 环境报错而退出

这是一个工具交互问题，不是源码或配置名错误。

### 3.2 `genconfig.py` 结果

第一次直接运行 `genconfig.py` 时，因为 `SDK_DIR` 环境变量未传入，报：

```text
'/standalone.kconfig' not found
```

补上：

- `SDK_DIR=/tmp/phytium-standalone-sdk`
- `STANDALONE_DIR=/tmp/phytium-standalone-sdk`

之后，配置解析阶段可以继续进行。

### 3.3 `make all` 结果

在补齐 `SDK_DIR` / `STANDALONE_DIR` 后继续执行：

```bash
make clean
make all -j"$(nproc)"
```

构建真实失败点为：

```text
/bin/aarch64-none-elf-gcc: not found
```

随后多个对象编译一起失败，例如：

- `aarch64_ram.ld.o`
- `fdrivers_port.o`
- `strto.o`
- `main.o`
- `fboard_init.o`
- `fmmu_table.o`
- `fassert.o`
- `device.o`
- `version.o`
- `fcache.o`

因此，本轮没有生成新的：

- `pe2204_aarch64_phytiumpi_openamp_core0.elf`
- `openamp_core0.elf`

## 4. 当前最小 blocker

当前 blocker 已经非常明确，且比之前更靠后：

### 已经不缺的

- 官方源码入口
- PhytiumPi aarch64 对应配置
- 最小 `STATUS_REQ/RESP` patch
- patch 在官方 SDK 上的可应用性
- patch 在官方 SDK 工作副本上的真实应用

### 当前缺的

- **`aarch64-none-elf-gcc` 交叉编译工具链**

这意味着：

- 现在不再卡在“源码找不到”
- 也不再卡在“补丁设计不出来”
- 而是卡在“本机还不能把补丁编译成新 firmware”

## 5. 建议下一步

建议按优先级走：

1. 在本机安装或接入官方要求的裸机交叉工具链：
   - 目标至少提供 `aarch64-none-elf-gcc`
2. 重新执行：

```bash
cd /tmp/phytium-standalone-sdk/example/system/amp/openamp_for_linux
export SDK_DIR=/tmp/phytium-standalone-sdk
export STANDALONE_DIR=/tmp/phytium-standalone-sdk
make clean
make all -j"$(nproc)"
```

3. 若 ELF 成功产出，再继续：
   - `make image USR_BOOT_DIR=/tmp/phytium_openamp_out`
   - 替换飞腾派 `/lib/firmware/openamp_core0.elf`
   - `stop/start remoteproc0`
   - 用 `openamp_rpmsg_bridge.py` 验证真实 `STATUS_RESP`

## 6. 是否建议现在继续部署远端

当前**不建议**部署远端，因为：

- 还没有新的 `openamp_core0.elf` 产物
- 部署不存在的 firmware 只会制造假进展

因此，本轮的正确收口应该是：

> 从核 patch 已成功进入官方 SDK 工作副本，当前仅缺裸机交叉编译器 `aarch64-none-elf-gcc`，待工具链补齐后再继续生成并部署新 firmware。
