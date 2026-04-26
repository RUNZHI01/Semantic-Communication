#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 4.4 TVM trusted current 多 SNR 鲁棒性图表 — IEEE 顶刊级严格规范版 (无遮挡精修)
严格遵循：
1. 字体：英文 Times New Roman，中文黑体 (SimHei)
2. 字号：Caption(9pt), 轴/图例(8pt), 刻度/注释(7pt)
3. 布局：1x2 紧凑布局，彻底解决标签干涉，优化留白与呼吸感
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ================= 1. 严格执行字体与字号规范 =================
def setup_ieee_strict_style():
    # 强制字体：英文优先 Times New Roman，中文回退系统黑体 (SimHei)
    plt.rcParams['font.family'] = ['Times New Roman', 'SimHei', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 严格映射字号规范表
    global F_SIZE
    F_SIZE = {
        "caption": 9,   # 图表标题 (8-9 pt，全图最大)
        "label": 8,     # 轴标题/单位 (7-8 pt)
        "legend": 8,    # 图例文本 (7-8 pt)
        "tick": 7,      # 刻度标签 (6-7 pt)
        "note": 7       # 注释/说明 (6-7 pt)
    }
    
    # IEEE 顶刊标准配色 (高对比、灰度打印友好)
    global C
    C = {
        "text": "#000000",        # 纯黑文本
        "latency": "#1A5276",     # 学术深蓝 (左图时延)
        "psnr": "#1A5276",        # 学术深蓝 (右图主轴 PSNR)
        "ssim": "#A93226",        # 砖红色 (右图次轴 SSIM)
        "baseline": "#7F7F7F",    # 中性灰 (基准线)
        "grid": "#EAECEF",        # 浅灰网格线
        "spine": "#000000"        # 坐标轴线
    }
    
    # 线宽与图形全局设置
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.linewidth'] = 0.75      # 细边框更显学术
    plt.rcParams['lines.linewidth'] = 1.25     # 数据线宽
    plt.rcParams['xtick.major.width'] = 0.75
    plt.rcParams['ytick.major.width'] = 0.75
    plt.rcParams['xtick.major.size'] = 3
    plt.rcParams['ytick.major.size'] = 3

# ================= 2. 核心实验数据 =================
SNR_VALS = [1, 4, 7, 10, 13]
LATENCY  = [228.2, 228.6, 233.5, 231.9, 234.0]
PSNR     = [29.15, 31.80, 34.02, 35.66, 36.87]
SSIM     = [0.900, 0.940, 0.961, 0.973, 0.979]

# ================= 3. 辅助学术绘图函数 =================
def format_academic_axes(ax):
    """清理多余边框，添加辅助网格，严格设置刻度字号"""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(C['spine'])
    ax.spines['bottom'].set_color(C['spine'])
    ax.tick_params(axis='both', which='major', labelsize=F_SIZE['tick'], color=C['spine'])
    ax.yaxis.grid(True, linestyle='--', color=C['grid'], linewidth=0.5)
    ax.xaxis.grid(False)

# ================= 4. 主渲染逻辑 =================
def render_figure():
    setup_ieee_strict_style()
    
    # 尺寸控制：7.16 英寸宽（IEEE 跨栏标准），高度 2.8 英寸（增加呼吸感）
    fig, (ax1, ax2_psnr) = plt.subplots(1, 2, figsize=(7.16, 2.8), dpi=600)
    
    # 全局标题 (9pt)
    fig.suptitle("图 4.4 TVM trusted current 的多 SNR 鲁棒性 (300 Images)", 
                 fontsize=F_SIZE['caption'], fontweight='bold', y=1.00)

    # ------------------- 子图 (a): 时延鲁棒性 -------------------
    # 实线 + 圆形标记 (略微放大 marker 至 4.5 提升印刷质感)
    ax1.plot(SNR_VALS, LATENCY, color=C['latency'], linestyle='-', marker='o', 
             markersize=4.5, label="Latency")
    
    # 基准线
    mean_lat = np.mean(LATENCY)
    ax1.axhline(y=mean_lat, color=C['baseline'], linestyle='--', linewidth=1.0, zorder=1)
    
    # 🌟 修复遮挡：将极差说明文本放置于图表右下角天然留白区 (0.95, 0.05)
    max_dev = (max(LATENCY) - min(LATENCY)) / mean_lat * 100
    ax1.text(0.95, 0.05, f"Mean: {mean_lat:.1f} ms\nMax Dev: < {max_dev:.1f}%", 
             transform=ax1.transAxes, ha='right', va='bottom', 
             fontsize=F_SIZE['note'], color=C['text'], 
             bbox=dict(facecolor='white', edgecolor='none', alpha=0.9, pad=1))
    
    ax1.set_ylim(226, 236)
    ax1.set_xticks(SNR_VALS)
    ax1.set_xlabel("SNR (dB)", fontsize=F_SIZE['label'], color=C['text'])
    ax1.set_ylabel("Latency (ms/image)", fontsize=F_SIZE['label'], color=C['text'])
    ax1.set_title("(a) Inference Latency vs. SNR", fontsize=F_SIZE['caption'], pad=8)
    format_academic_axes(ax1)

    # ------------------- 子图 (b): 质量降级双 Y 轴 -------------------
    # 主 Y 轴：PSNR (深蓝实线 + 圆形标记)
    line1 = ax2_psnr.plot(SNR_VALS, PSNR, color=C['psnr'], linestyle='-', marker='o', 
                          markersize=4.5, label='Mean PSNR')
    ax2_psnr.set_xlabel("SNR (dB)", fontsize=F_SIZE['label'], color=C['text'])
    ax2_psnr.set_ylabel("PSNR (dB)", fontsize=F_SIZE['label'], color=C['psnr'])
    ax2_psnr.set_ylim(28, 38)
    ax2_psnr.set_xticks(SNR_VALS)
    format_academic_axes(ax2_psnr)
    
    # 次 Y 轴：SSIM (砖红短虚线 + 三角标记)
    ax2_ssim = ax2_psnr.twinx()
    line2 = ax2_ssim.plot(SNR_VALS, SSIM, color=C['ssim'], linestyle='--', marker='^', 
                          markersize=4.5, label='Mean SSIM')
    ax2_ssim.set_ylabel("SSIM", fontsize=F_SIZE['label'], color=C['ssim'])
    ax2_ssim.set_ylim(0.88, 1.0)
    
    # 次 Y 轴的边框清理
    ax2_ssim.spines['top'].set_visible(False)
    ax2_ssim.spines['left'].set_visible(False)
    ax2_ssim.tick_params(axis='both', which='major', labelsize=F_SIZE['tick'])
    
    ax2_psnr.set_title("(b) Reconstruction Quality vs. SNR", fontsize=F_SIZE['caption'], pad=8)
    
    # 图例 (8pt)：合并双轴图例，因曲线皆向右上延伸，右下角为天然安全区
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax2_psnr.legend(lines, labels, loc='lower right', frameon=False, 
                    fontsize=F_SIZE['legend'], borderaxespad=0.5)
    
    # ------------------- 导出处理 -------------------
    # 略微放宽子图间距，避免左图的极差说明文本与右图的 Y 轴标签发生视觉黏连
    plt.subplots_adjust(wspace=0.32, bottom=0.18) 
    out_path = Path("paper_fig4_4_snr_robustness_strict_ieee_v2.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] 图 4.4 严格规范无遮挡版生成成功: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()