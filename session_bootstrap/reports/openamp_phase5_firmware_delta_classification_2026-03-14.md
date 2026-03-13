# Phase 5 OpenAMP 固件剩余大小差分类结论

> 日期：2026-03-14  
> 目标：比较板上官方 `openamp_core0.elf`（`1650448` bytes）与当前最接近的官方原版重建候选 `release_v1.4.0`（`1627224` bytes），判断剩余 `23224` bytes 差值主要来自 debug 区域还是 runtime/resource 区域，并把过程固化到仓库。

## 1. 本轮结论

剩余 `23224` bytes **更像是 `.debug_*` / 符号表 / 其他非装载元数据差异，而不是 runtime/resource section 差异**。

理由很直接：

1. 板上官方 ELF 的 `.debug_*` section 总量为 `1413392` bytes，剩余差值只占其中 **1.64%**。
2. 板上官方 ELF 的 runtime/resource 实际落盘 section 总量只有 `116305` bytes（`.text + .rodata + .data + .resource_table`），剩余差值若主要归因于这里，就要占到 **19.97%**。
3. 从 program header 看，两个 `LOAD` segment 的 FileSiz 总和只有 `118784` bytes，`23224` bytes 相当于 **19.55%** 的 loadable file payload；对“已知最接近”的 `release_v1.4.0` 候选来说，这种 runtime 级别的偏移过大，不像“尾差”。
4. 板上官方 ELF 做 `objcopy --strip-debug` 后仍有 `232136` bytes；如果把 `23224` bytes 解释成 runtime 差异，它仍然相当于整个 debug-stripped 映像的 **10.00%**，仍偏大。把这 `23 KB` 放回 `1.41 MB` 的 DWARF / symbol payload 中则合理得多。

因此，本轮应把剩余差值定性为：

**主要在 debug / 非装载元数据，不是主要卡在 runtime/resource 布局。**

## 2. 板上官方 ELF 的大小构成

原始文件：

- `session_bootstrap/reports/old_fw_compare_20260314/openamp_core0_official.elf`
- 文件大小：`1650448`

基于 `readelf -SW`、`readelf -lW`、`size -A -d` 与临时 `objcopy` 结果，板上官方 ELF 的构成为：

| 项目 | 大小（bytes） | 说明 |
| --- | ---: | --- |
| `.debug_*` 合计 | `1413392` | 主体是 `.debug_info`、`.debug_line`、`.debug_loc` |
| runtime/resource section 落盘合计 | `116305` | `.text=92800`、`.rodata=11217`、`.data=8192`、`.resource_table=4096` |
| `LOAD` segment FileSiz 合计 | `118784` | 比上面多出 `2479` bytes 的段内对齐/填充 |
| 其他非装载元数据 | `34861` | `.symtab`、`.strtab`、`.comment`、`.shstrtab` |
| 其他文件级开销/填充 | `85890` | ELF 头、program header、section header、对齐空洞等 |
| `objcopy --strip-debug` 后大小 | `232136` | 用于估算“去掉 debug 后”的整体量级 |
| `objcopy --strip-all` 后大小 | `201672` | 说明符号/字符串表本身也不是零开销 |

同时还要注意：

- `.bss + .heap + .stack + .le_shell` 的 **内存**总量是 `6659776` bytes
- 但这些 section 是 `NOBITS`，**不计入 ELF 文件大小差值**

所以，“从核运行时占用很大”这件事和“ELF 文件只差 23 KB”不是同一个问题。

## 3. 与 `release_v1.4.0` 候选的剩余差值对比

已知候选：

- 来源：前序离线收敛调查结论
- 版本：`release_v1.4.0`
- 大小：`1627224`

对比结果：

- 板上官方：`1650448`
- 候选重建：`1627224`
- 剩余差值：`23224`

把 `23224` 分别投到官方 ELF 的几个关键桶里看：

| 比较基准 | 占比 |
| --- | ---: |
| 相对 `.debug_*` 总量 `1413392` | `1.64%` |
| 相对 runtime/resource 落盘总量 `116305` | `19.97%` |
| 相对 `LOAD` segment FileSiz 总量 `118784` | `19.55%` |
| 相对 debug-stripped 总大小 `232136` | `10.00%` |

这组比例清楚说明：

- 如果说剩余差值主要在 debug / symbol / 其他非装载元数据，量级上完全合理；
- 如果说剩余差值主要在 runtime/resource，则意味着 runtime payload 还差将近五分之一，这和“`release_v1.4.0` 已经是最接近原版”不匹配。

## 4. 工具与可复现产物

已新增脚本：

- `session_bootstrap/scripts/compare_openamp_firmware_delta.py`

本轮原始产物目录：

- `session_bootstrap/reports/openamp_fw_delta_compare_20260314/`

其中包含：

- `official.readelf_sections.txt`
- `official.readelf_segments.txt`
- `official.size_A_d.txt`
- `comparison_summary.json`
- `candidate_fetch_error.txt`

脚本默认会：

1. 分析本地板上官方 ELF；
2. 优先尝试通过 `ssh_with_password.sh` 拉取远端 `release_v1.4.0` 候选 ELF；
3. 远端可达时做完整 section/segment 对比；
4. 远端不可达时，在保留失败信息的同时回退为“已知候选大小 + 官方 ELF 构成”的 size-only 推断。

## 5. 本轮边界

当前 Codex sandbox 禁止 SSH 建连，因此本轮没有直接把远端候选 ELF 拉到本地；失败信息已经原样记录在：

- `session_bootstrap/reports/openamp_fw_delta_compare_20260314/candidate_fetch_error.txt`

错误为：

- `socket: Operation not permitted`

这意味着：

- 本轮最终结论来自 **板上官方 ELF 的精确 section/segment 分解** 加上 **已知候选大小 `1627224`** 的比例判断；
- 不是一次 live remote `readelf` 对 `readelf` 的逐节 diff。

但就“剩余 23 KB 差值主要落在哪一类区域”这个问题而言，结论已经足够明确：

**剩余差值主要在 debug / 非装载元数据，不是主要在 runtime/resource。**
