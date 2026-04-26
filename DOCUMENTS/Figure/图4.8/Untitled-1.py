#!/usr/bin/env python3
import matplotlib
# 使用 Agg backend，确保在没有图形界面的服务器环境下也能正常生成图片
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path

# --- 独立运行环境配置 ---
# 直接将输出路径指向当前运行脚本所在的同级目录
OUT_MNN = Path("fig_mnn_benchmark_optimized.png")

def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def apply_style():
    """精简版的基础样式配置，脱离对特定本地包的依赖"""
    plt.style.use("default") 
    sns.set_theme(style="ticks")
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["text.color"] = "#333333"
    plt.rcParams["xtick.color"] = "#333333"
    plt.rcParams["ytick.color"] = "#333333"


# --- 您的核心绘图代码 ---
def render_mnn_benchmark() -> None:
    apply_style()
    ensure_dir(OUT_MNN)

    # 1. 采用 IEEE 偏好的学术配色
    ACADEMIC_BLUE = "#1F77B4"  
    MUTED_GRAY = "#999999"     
    LIGHT_GRAY = "#CCCCCC"     

    # 【优化点 3：专业质感】全局强制指定英文和数字使用 Times New Roman 字体
    plt.rcParams["font.family"] = "Times New Roman"
    # 顺手把数学符号的字体也匹配上，确保风格统一
    plt.rcParams["mathtext.fontset"] = "stix" 

    configs = [
        {"label": "1I / 1T / FP32\n(Baseline)", "total_s": 140.7, "color": LIGHT_GRAY},
        {"label": "2I / 2T / FP32", "total_s": 101.3, "color": MUTED_GRAY},
        {"label": "2I / 1T / low", "total_s": 99.1, "color": MUTED_GRAY},
        {"label": "2I / 1T / FP32\n(Optimized)", "total_s": 98.2, "color": ACADEMIC_BLUE},
    ]
    
    configs.sort(key=lambda x: x["total_s"], reverse=True)

    labels = [c["label"] for c in configs]
    totals = [c["total_s"] for c in configs]
    colors = [c["color"] for c in configs]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=300)

    y = np.arange(len(labels))
    
    # 【优化点 2：视觉张力】将柱体高度（厚度）由 0.55 提至 0.68，使其更加丰满紧凑
    bars = ax.barh(y, totals, color=colors, height=0.68, edgecolor="none")

    labels_text = [f" {t:.1f} s | {t * 1000 / 300:.1f} ms/image" for t in totals]
    
    # 【优化点 4：呼吸感】增大 padding 参数至 10，让数据标签远离柱体边缘
    ax.bar_label(bars, labels=labels_text, padding=10, fontsize=10, color="#333333")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("Total Latency for 300 Images (s)", fontsize=11, weight="bold")
    
    # 保持适当的 x 轴延伸，确保最长柱体的标签有充足显示空间
    ax.set_xlim(0, max(totals) * 1.35) 

    top_ax = ax.secondary_xaxis("top", functions=(lambda s: s * 1000 / 300, lambda ms: ms * 300 / 1000))
    top_ax.set_xlabel("Average Latency (ms/image)", fontsize=11, weight="bold")

    best_s = min(totals)
    baseline_s = max(totals)
    uplift = baseline_s / best_s

    # 【优化点 1：避免重叠】移至右上角安全区 (0.98, 0.95)，并增加半透明白色底层 bbox 防粘连
    ax.text(
        0.98, 0.95,
        f"Performance Uplift: {uplift:.2f}x",
        transform=ax.transAxes,
        ha="right", va="top",
        fontsize=12, fontweight="bold", color=ACADEMIC_BLUE,
        bbox=dict(facecolor='white', alpha=0.85, edgecolor='none', pad=4)
    )

    sns.despine(ax=ax, top=False, right=True, left=True, bottom=False)
    sns.despine(ax=top_ax, top=False, right=True, left=True, bottom=False)
    ax.tick_params(axis="y", length=0) 

    fig.tight_layout()
    fig.savefig(OUT_MNN, bbox_inches="tight")
    
    # 成功提示与路径打印
    print(f"✅ 图片已成功生成并保存至: {OUT_MNN.absolute()}")
    plt.close(fig)

if __name__ == "__main__":
    render_mnn_benchmark()