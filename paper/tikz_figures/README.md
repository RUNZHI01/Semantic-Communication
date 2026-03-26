# CICC 初赛技术文档 - 插图 TikZ 源文件（独立编译）

本目录存放论文插图的 TikZ 源文件，**可单独编译为 PDF**，不依赖主文档。

## 编译

```bash
make          # 编译全部图
make clean    # 清理输出
```

或单独编译：

```bash
xelatex fig_system_arch.tex
```

## 文件列表

| 文件 | 对应图号 | 说明 |
|------|----------|------|
| `fig_system_arch.tex` | 图 1.1 | 系统概述图 |
| `fig_gan_jscc.tex` | 图 1.2 | GAN-based JSCC 结构图 |
| `fig_system_run.tex` | 图 3.1 | 系统运行/测试流程图 |
| `fig_tvm_pipeline.tex` | 图 4.1 | TVM 优化编译器框架转换步骤 |
| `fig_tvm_opt_flow.tex` | 图 4.3 | TVM 优化逻辑流程图 |
| `fig_baseline_current.tex` | 图 4.8 | baseline→current 工程优化演进图 |
| `fig_mnn_arch.tex` | 图 4.5 | MNN 概述示意图 |
| `fig_geometric_computing.tex` | 图 4.10 | 几何计算机制示意 |
| `fig_mnn_dynamic.tex` | 图 4.9 | MNN 动态优化流程 |
| `fig_mnn_resize.tex` | 图 4.7 | resizeTensor/resizeSession 示例 |
| `fig_perf_bar.tex` | 图 4.11 | 综合性能对比柱状图 |

## 依赖

- `_preamble.tex`：公共颜色与 TikZ 库定义
- 使用 `standalone` 文档类，输出为紧凑裁剪的 PDF
