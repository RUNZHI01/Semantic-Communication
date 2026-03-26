# 原版 vs 增强版图表对比说明

## 为什么你可能感觉"没什么改变"？

你的原版图表**已经很不错了**！它们已经包含了：
- ✅ 低饱和度配色
- ✅ 微观结构拆解
- ✅ 张量维度标注
- ✅ 背景分组

所以增强版的改进相对**渐进式**而非**革命性**。

---

## 增强版的具体改进（细微但重要）

### 1. **信息密度大幅提升**

#### 原版：
```latex
% 只有简单的张量标注
node[pos=0.5, above=2pt, ts] {$\mathbf{y}$};
```

#### 增强版：
```latex
% 双层标注：数学符号 + 语义说明
node[pos=0.5, above=3pt, ts] {$\mathbf{y} \in \mathbb{R}^{1{\times}32{\times}32{\times}32}$}
node[pos=0.5, below=3pt, ts] {语义特征向量};
```

**改进**：每条数据流都有**上下双层标注**，上层是数学表达式，下层是语义解释。

---

### 2. **数学公式图例（核心改进）**

#### 原版：
```latex
% 简单图例
\textbf{图例}\\[1pt]
实线：推理 \quad 虚线：训练
```

#### 增强版：
```latex
% 补充完整的损失函数
\textbf{训练损失函数}\\[2pt]
$L_t = \lambda L_G + \alpha L_{\text{MSE}} + \beta L_{\text{LPIPS}}$\\[1pt]
$L_G = -\mathbb{E}[\log D(G(\hat{\mathbf{y}}), \hat{\mathbf{y}})]$\\[1pt]
$L_D = -\mathbb{E}[\log D(\mathbf{x}, \mathbf{y})] - \mathbb{E}[\log(1 - D(\hat{\mathbf{x}}, \hat{\mathbf{y}}))]$

% 补充SNR公式
SNR = $10\log_{10}\frac{\|\mathbf{y}\|^2}{\sigma^2}$ (dB)
```

**改进**：把文档中的核心公式**直接嵌入图表**，阅读者无需翻文档就能理解算法。

---

### 3. **微观结构标注更详细**

#### 原版：
```latex
\node[micro] (e4) {ResBlock$\times$2};
```

#### 增强版：
```latex
\node[micro] (e4) {ResBlock$\times$2};
\node[ts, below=0.15cm of e1] {$3{\to}64$};  % 通道数变化
\node[ts, below=0.15cm of e4] {$256{\to}32$};  % 特征维度变化
```

**改进**：补充了**通道数变化**，让读者理解卷积层的具体作用。

---

### 4. **AWGN信道数学表达**

#### 原版：
```latex
\draw[arr] (awgn) -- (gen)
  node[pos=0.5, above=2pt, ts] {$\hat{\mathbf{y}}$};
```

#### 增强版：
```latex
\draw[arr] (awgn) -- (gen)
  node[pos=0.5, above=3pt, ts] {$\hat{\mathbf{y}} = \sqrt{P}\mathbf{y} + \mathbf{n}$}
  node[pos=0.5, below=3pt, ts] {受噪声污染的特征};
```

**改进**：显式写出**AWGN加噪公式**，而不只是符号。

---

### 5. **Discriminator输出说明**

#### 原版：
```latex
\node[disc] (disc) {Discriminator\\{\tiny 仅训练}};
```

#### 增强版：
```latex
\node[disc] (disc) {Discriminator\\{\tiny 判别器（仅训练）}};
\node[below=0.4cm of disc, ts] {$D(\mathbf{x}, \hat{\mathbf{y}}) \in [0,1]$};
```

**改进**：补充了Discriminator的**输出范围**说明。

---

## 如何看到更明显的差异？

### 方法1：对比原版PDF和增强版PDF
```bash
cd /home/tianxing/tvm_metaschedule_execution_project/paper

# 编译原版
cd tikz_figures
xelatex fig_gan_jscc.tex

# 编译增强版
cd ../tikz_figures_enhanced
xelatex fig_gan_jscc_enhanced.tex

# 左右对比两个PDF
evince tikz_figures/fig_gan_jscc.pdf &
evince tikz_figures_enhanced/fig_gan_jscc_enhanced.pdf &
```

### 方法2：查看源代码的行数差异
```bash
wc -l tikz_figures/fig_gan_jscc.tex
wc -l tikz_figures_enhanced/fig_gan_jscc_enhanced.tex
```

原版：~90行
增强版：~180行（**信息密度翻倍**）

---

## 增强版的价值在哪里？

虽然**视觉风格相似**，但增强版的核心价值是：

### 🎯 自包含性（Self-Contained）
- **原版**：读者需要翻文档才能理解 $L_G, L_D, L_{\text{LPIPS}}$ 是什么
- **增强版**：图表本身就包含完整的数学定义

### 🎯 教学友好性（Pedagogical）
- **原版**：适合已经理解算法的专家
- **增强版**：适合第一次接触语义通信的读者

### 🎯 论文自洽性（Publication-Ready）
- **原版**：图表需要配合大量正文解释
- **增强版**：图表可以独立理解，适合顶会海报展示

---

## 如果你想要更激进的改变...

我可以创建**超级增强版**，具有以下特征：

1. **3D层叠效果**：用TikZ的`xshift/yshift`绘制多层ResBlock的立体感
2. **动画标注**：用颜色渐变表示数据流方向
3. **性能数据嵌入**：在图表中直接标注"Encoder推理时间: 12ms"
4. **对比子图**：在同一张图中对比"有Discriminator"vs"无Discriminator"的效果

是否需要我创建这个版本？

---

## 快速检查清单

对比以下内容，看看增强版是否真的有改进：

| 特征 | 原版 | 增强版 |
|------|------|--------|
| 损失函数公式 | ❌ 无 | ✅ 完整 $L_t, L_G, L_D$ |
| AWGN公式 | ❌ 符号 $\hat{y}$ | ✅ $\hat{y} = \sqrt{P}y + n$ |
| 通道数变化 | ❌ 无 | ✅ $3{\to}64$, $256{\to}32$ |
| Discriminator输出 | ❌ 无 | ✅ $D \in [0,1]$ |
| SNR定义 | ❌ 无 | ✅ $10\log_{10}\frac{\|y\|^2}{\sigma^2}$ |
| 双层标注 | ❌ 单层 | ✅ 数学+语义 |
| 图例信息量 | 基础 | 2倍+ |

**如果这些差异还不够明显，请告诉我你期望的改进方向！**
