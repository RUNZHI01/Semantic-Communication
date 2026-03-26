# 增强版 TikZ 学术架构图

本目录包含为 **CICC0903540 初赛技术文档** 重绘的高质量学术架构图，严格遵循顶会/顶刊（NeurIPS, CVPR, ICLR, IEEE TPAMI）的审美标准。

---

## 📊 图表列表

### 1. **fig_gan_jscc_enhanced.tex**
- **对应文档章节**：2.2 模型原理介绍
- **内容**：GAN-based JSCC 语义通信结构图
- **亮点**：
  - 拆解 Encoder/Generator 微观结构（Conv-BN-ReLU-ResBlock）
  - 标注张量维度 ($1\times 32\times 32\times 32$)
  - cGAN 损失函数公式（$L_t, L_G, L_D$）
  - 区分训练路径（虚线）与推理路径（实线）

### 2. **fig_system_arch_enhanced.tex**
- **对应文档章节**：1.1 系统概述
- **内容**：端到端语义通信图像传输系统架构
- **亮点**：
  - 上位机硬件配置（i7-13700H + RTX 4060）
  - 飞腾派硬件配置（ARMv8.0 Cortex-A72）
  - OpenSSH 传输细节（AES-128-CTR, SFTP Pool, Window 1GB）
  - 系统工作流程五步标注

### 3. **fig_tvm_pipeline_enhanced.tex**
- **对应文档章节**：4.1 TVM 介绍
- **内容**：TVM 端到端编译流水线
- **亮点**：
  - 模型导入 → Relax IR → TE → MetaSchedule → TIR → 机器码
  - 每阶段微观操作（FuseOps, 循环切分, RPC Runner, LLVM）
  - MetaSchedule 配置细节（baseline-seeded, 500 trials）
  - Target 配置 JSON 格式

### 4. **fig_mnn_arch_enhanced.tex**
- **对应文档章节**：4.3 MNN 介绍
- **内容**：MNN 轻量级推理引擎架构
- **亮点**：
  - Converter（Frontend + Graph Optimizer）
  - Interpreter（Engine + Backend + 几何计算 + 半自动搜索）
  - 算子分类（61原子 + 45转换 + 16复合）
  - 几何计算收益：$O(1954) \to O(1055)$，减少 46%

### 5. **fig_tvm_opt_flow_enhanced.tex**
- **对应文档章节**：4.2.3 从 baseline 到 current 的工程优化演进
- **内容**：TVM 五层演进路径
- **亮点**：
  - 运行时：compat → safe runtime
  - Target：generic + neon → cortex-a72
  - 调优：rebuild-only → 增量调优
  - 评测：payload only → 真实重建
  - 治理：人工确认 → SHA guard

### 6. **fig_perf_comparison_enhanced.tex**
- **对应文档章节**：4.2.2 静态 TVM 的优化效果
- **内容**：性能对比柱状图
- **亮点**：
  - Payload 对比：91.64% 提升（1829 → 153 ms）
  - Current-only：93.85% 提升（2479 → 152 ms）
  - 端到端重建：86.02% 提升（1830 → 256 ms）
  - MNN 动态支持：1.85× 加速（平均 410 ms）

### 7. **fig_geometric_computing_enhanced.tex**
- **对应文档章节**：4.3.1 几何计算机制
- **内容**：MNN 几何计算分解示意图
- **亮点**：
  - 转换/复合算子 → 光栅 + 原子算子
  - region 概念（strides + offsets）
  - 优化工作量对比公式
  - 垂直合并 + 水平合并策略

---

## 🎨 设计规范

### **配色方案（低饱和度马卡龙）**
```latex
\definecolor{mBlue}{HTML}{AEC6CF}    % 编码端/IR层
\definecolor{mPink}{HTML}{FFD1DC}    % Discriminator/Baseline
\definecolor{mGreen}{HTML}{B1D8B7}   % 信道/调优层
\definecolor{mPurple}{HTML}{B39EB5}  % 解码端/代码生成
\definecolor{mYellow}{HTML}{FDFD96}  % 半自动搜索
\definecolor{mGray}{HTML}{E5E4E2}    % 硬件/IO
\definecolor{mDark}{HTML}{4A4A4A}    % 文字/线条
```

### **全局样式**
- **线条**：`thick, draw=mDark`，禁止使用纯黑
- **箭头**：`>=stealth`，统一样式
- **节点**：`rounded corners=3pt`，一致的圆角
- **字体**：`\sffamily`，无衬线字体
- **连线**：强制使用正交连线（`|-` 或 `-|`），禁止斜线

### **信息密度提升**
- 张量维度标注：`\tiny\sffamily, color=mDark!80`
- 微观结构拆解：用 `micro` 样式展示 Conv-BN-ReLU
- 数学公式：在图例中补充关键公式
- 背景分组：用 `fit` + `backgrounds` 库实现层次化

---

## 🔧 编译方法

### **方法 1：使用 XeLaTeX（推荐）**
```bash
xelatex fig_gan_jscc_enhanced.tex
xelatex fig_system_arch_enhanced.tex
xelatex fig_tvm_pipeline_enhanced.tex
xelatex fig_mnn_arch_enhanced.tex
xelatex fig_tvm_opt_flow_enhanced.tex
xelatex fig_perf_comparison_enhanced.tex
xelatex fig_geometric_computing_enhanced.tex
```

### **方法 2：批量编译**
```bash
for file in fig_*_enhanced.tex; do
  xelatex "$file"
done
```

### **方法 3：使用 Makefile**
```bash
cd tikz_figures_enhanced
make all
```

---

## 📝 使用说明

### **在论文中引用**
```latex
\usepackage{graphicx}

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.95\textwidth]{tikz_figures_enhanced/fig_gan_jscc_enhanced.pdf}
  \caption{GAN-based JSCC 语义通信结构图}
  \label{fig:gan_jscc}
\end{figure}
```

### **调整图表大小**
如需调整图表大小，修改 `.tex` 文件中的：
- `border=10pt` → 调整边距
- `minimum width` → 调整节点宽度
- `node distance` → 调整节点间距

---

## ✨ 核心改进

相比原版图表，增强版图表实现了以下改进：

### **1. 审美提升**
- ❌ 禁用 TikZ 默认纯色（red, blue）
- ✅ 使用低饱和度马卡龙配色
- ✅ 统一全局样式（线条、箭头、字体）

### **2. 信息密度**
- ✅ 拆解黑盒：展示 Encoder/Generator 微观结构
- ✅ 张量标注：每条数据流标注维度
- ✅ 数学符号：用 $\oplus$ $\otimes$ 代替"Add""Concat"
- ✅ 公式补全：在图例中添加损失函数、SNR 公式

### **3. 排版引擎**
- ✅ 强制使用 `positioning` 库（禁止绝对坐标）
- ✅ 使用 `fit` + `backgrounds` 实现层次化分组
- ✅ 正交连线（`|-` 或 `-|`），禁止斜线乱飞

### **4. 学术厚重感**
- ✅ 每张图补充技术细节图例（硬件配置、调优参数、性能数据）
- ✅ 层叠效果（ResBlock×2, ResBlock×5）
- ✅ 图例精致化（配色说明 + 技术细节）

---

## 📚 参考文献

本目录图表基于以下文献和技术文档：

1. **CICC0903540 初赛技术文档**（主要参考）
2. Ye D, et al. "Lightweight Generative Joint Source-Channel Coding for Semantic Image Transmission with Compressed Conditional GANs", IEEE/CIC ICCC Workshops 2023
3. Lv C, et al. "Walle: An End-to-End, General-Purpose, and Large-Scale Production System for Device-Cloud Collaborative Machine Learning", OSDI 2022
4. TVM 官方文档：https://tvm.apache.org/
5. MNN 官方文档：https://mnn-docs.readthedocs.io/

---

## 🛠️ 依赖说明

### **LaTeX 包**
- `tikz`：绘图引擎
- `pgfplots`：数据可视化
- `fontspec`：字体支持
- `xeCJK`：中文支持
- TikZ 库：`arrows.meta, positioning, fit, backgrounds, calc, decorations.pathreplacing`

### **字体要求**
- 中文字体：SimHei（黑体）
- 英文字体：默认无衬线字体

如缺少字体，可替换为：
```latex
\setCJKmainfont{STHeiti}  % macOS
\setCJKmainfont{WenQuanYi Zen Hei}  % Linux
```

---

## 📧 联系方式

如有任何问题或改进建议，请通过以下方式联系：

- **队伍名称**：逃离荒岛队
- **队伍编号**：CICC0903540
- **参赛杯赛**：飞腾杯

---

**祝绘图愉快！🎨**
