#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 4.6 TVM 主线结果总览 — IEEE 顶刊级学术重构版 (修复遮挡版)
特点：完全去 UI 化、标准学术三线表、严格字号与字体规范、完美解决标签遮挡
"""

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
from pathlib import Path

# ================= 1. 全局字体与学术样式配置 =================
def setup_ieee_style():
    # 字体映射：优先英文 Times New Roman，中文回退到系统黑体 (SimHei)
    plt.rcParams['font.family'] = ['Times New Roman', 'SimHei', 'Noto Sans CJK SC', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 字号映射规范表
    global F_SIZE
    F_SIZE = {
        "caption": 9,     # 图表主标题 (8-9pt)
        "ax_title": 8.5,  # 子图标题
        "label": 8,       # 轴标题/单位 (7-8pt)
        "legend": 8,      # 图例文本 (7-8pt)
        "tick": 7,        # 刻度标签 (6-7pt)
        "note": 7         # 注释/说明 (6-7pt)
    }
    
    # 颜色规范
    global C
    C = {
        "text": "#000000",        # 纯黑文本
        "base": "#7F7F7F",        # 学术中灰
        "tvm": "#000000",         # 纯黑对比
        "pipe": "#1A5276",        # 学术深蓝
        "grid": "#E0E0E0",        # 极浅灰 (网格线)
        "line": "#000000"         # 坐标轴线
    }
    
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.linewidth'] = 0.75
    plt.rcParams['lines.linewidth'] = 1.2
    plt.rcParams['xtick.major.width'] = 0.75
    plt.rcParams['ytick.major.width'] = 0.75

# ================= 2. 核心实验数据 =================
DATA = {
    "payload": {"base": 1829.3, "curr": 152.8, "speedup": 12.0},
    "e2e": {"base": 1850.0, "tvm": 230.3, "pipe": 134.6},
    "throughput": {"serial": 4.33, "pipe": 6.76, "uplift": 56.1},
    "quality": {"psnr_b": 34.42, "psnr_c": 35.66, "ssim_b": 0.9705, "ssim_c": 0.9728},
    "resource": {"artifact": 1.57, "ram": "88.3", "cpu": "32.3 / 9.1 / 58.3 / 0.3"},
    "boundary": [
        ("Output Integrity", "300 / 300 PNG"), 
        ("Artifact Check", "SHA-256 matched"),
        ("Deploy Mode", "4-core Linux (Performance)")
    ]
}

# ================= 3. 辅助学术绘图函数 =================
def format_academic_axes(ax, y_grid=True):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(C['line'])
    ax.spines['bottom'].set_color(C['line'])
    ax.tick_params(axis='both', which='both', labelsize=F_SIZE['tick'], color=C['line'], length=3)
    if y_grid:
        ax.yaxis.grid(True, linestyle='--', color=C['grid'], linewidth=0.5)
    ax.xaxis.grid(False)

def draw_academic_table(ax, title, headers, rows):
    ax.axis('off')
    ax.text(0, 1.0, title, transform=ax.transAxes, ha='left', va='bottom',
            fontsize=F_SIZE['ax_title'], fontweight='bold', color=C['text'])
    
    y_top = 0.85
    y_mid = 0.65
    y_bot = 0.05
    line_args = dict(color=C['text'], transform=ax.transAxes)
    ax.add_line(mlines.Line2D([0, 1], [y_top, y_top], linewidth=1.2, **line_args))
    ax.add_line(mlines.Line2D([0, 1], [y_mid, y_mid], linewidth=0.75, **line_args))
    ax.add_line(mlines.Line2D([0, 1], [y_bot, y_bot], linewidth=1.2, **line_args))
    
    for idx, header in enumerate(headers):
        x_pos = 0.02 if idx == 0 else 0.55
        ax.text(x_pos, (y_top + y_mid)/2, header, transform=ax.transAxes, ha='left', va='center',
                fontsize=F_SIZE['note'], fontweight='bold', color=C['text'])
    
    row_height = (y_mid - y_bot) / len(rows)
    for i, (col1, col2) in enumerate(rows):
        y_pos = y_mid - (i + 0.5) * row_height
        ax.text(0.02, y_pos, col1, transform=ax.transAxes, ha='left', va='center', fontsize=F_SIZE['note'])
        ax.text(0.55, y_pos, col2, transform=ax.transAxes, ha='left', va='center', fontsize=F_SIZE['note'])

# ================= 4. 主渲染逻辑 =================
def render_figure():
    setup_ieee_style()
    
    fig = plt.figure(figsize=(7.16, 4.0), dpi=600)
    fig.suptitle("图 4.6 飞腾多核异构系统 TVM 主线结果总览\n(Fig 4.6 Overview of TVM Mainline Results on Phytium Heterogeneous System)", 
                 fontsize=F_SIZE['caption'], fontweight='bold', y=0.98)

    gs = fig.add_gridspec(2, 6, height_ratios=[1.3, 1], hspace=0.6, wspace=0.8, 
                          top=0.84, bottom=0.10, left=0.08, right=0.98)

    # --- (a) Payload 加速 ---
    ax1 = fig.add_subplot(gs[0, 0:2])
    ax1.hlines(0, DATA['payload']['curr'], DATA['payload']['base'], color=C['base'], linewidth=1.5, zorder=1)
    ax1.scatter(DATA['payload']['base'], 0, color=C['base'], s=40, zorder=2)
    ax1.scatter(DATA['payload']['curr'], 0, color=C['tvm'], s=40, zorder=2)
    
    ax1.text(DATA['payload']['base'], 0.15, f"{DATA['payload']['base']}", ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['base'])
    ax1.text(DATA['payload']['curr'], 0.15, f"{DATA['payload']['curr']}", ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['tvm'])
    ax1.text((DATA['payload']['curr']+DATA['payload']['base'])/2, -0.15, f"{DATA['payload']['speedup']}x", ha='center', va='top', fontsize=F_SIZE['legend'], fontweight='bold')
    
    ax1.set_ylim(-0.6, 0.6)
    ax1.set_yticks([])
    ax1.spines['left'].set_visible(False)
    ax1.set_xlabel("Time (ms)", fontsize=F_SIZE['label'])
    ax1.set_title("(a) Payload Inference", fontsize=F_SIZE['ax_title'], fontweight='bold', loc='left', pad=10)
    format_academic_axes(ax1, y_grid=False)

    # --- (b) E2E 延迟 ---
    ax2 = fig.add_subplot(gs[0, 2:4])
    x_labels = ['Baseline', 'Direct', 'Pipeline']
    y_vals = [DATA['e2e']['base'], DATA['e2e']['tvm'], DATA['e2e']['pipe']]
    colors = [C['base'], C['tvm'], C['pipe']]
    
    bars = ax2.bar(x_labels, y_vals, color=colors, width=0.5, edgecolor=C['line'], linewidth=0.75)
    ax2.set_ylabel("Latency (ms)", fontsize=F_SIZE['label'])
    ax2.set_title("(b) E2E Reconstruction", fontsize=F_SIZE['ax_title'], fontweight='bold', loc='left', pad=10)
    format_academic_axes(ax2)
    
    for bar in bars:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, f"{bar.get_height():.1f}", 
                 ha='center', va='bottom', fontsize=F_SIZE['tick'])

    # --- (c) 异构吞吐量 ---
    ax3 = fig.add_subplot(gs[0, 4:6])
    bars2 = ax3.bar(['Serial', 'Pipeline'], [DATA['throughput']['serial'], DATA['throughput']['pipe']], 
                    color=[C['tvm'], C['pipe']], width=0.4, edgecolor=C['line'], linewidth=0.75)
    ax3.set_ylabel("Throughput (fps)", fontsize=F_SIZE['label'])
    ax3.set_title("(c) Pipeline Throughput", fontsize=F_SIZE['ax_title'], fontweight='bold', loc='left', pad=10)
    format_academic_axes(ax3)
    
    # 绘制基础柱状图标签
    for bar in bars2:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, f"{bar.get_height():.2f}", 
                 ha='center', va='bottom', fontsize=F_SIZE['tick'])
    
    # 🌟 修复遮挡：采用 IEEE 标准对比跨度箭头 (Span Arrow)
    h_y = DATA['throughput']['pipe'] + 1.2  # 箭头水平线的高度 (位于最高柱子加上留白)
    ax3.set_ylim(0, h_y + 1.2)              # 扩展 y 轴，防止文字被切掉
    
    # 水平对比箭头 (从 0 指向 1)
    ax3.annotate('', xy=(1.0, h_y), xytext=(0.0, h_y),
                 arrowprops=dict(arrowstyle="->", color=C['pipe'], lw=0.8))
    # 两侧垂直下沉的虚线辅助线 (连接箭头和柱子)
    ax3.plot([0.0, 0.0], [DATA['throughput']['serial'] + 0.5, h_y], color=C['pipe'], lw=0.6, linestyle='--')
    ax3.plot([1.0, 1.0], [DATA['throughput']['pipe'] + 0.5, h_y], color=C['pipe'], lw=0.6, linestyle='--')
    
    # 居中的涨幅文本
    ax3.text(0.5, h_y + 0.15, f"+{DATA['throughput']['uplift']}%", 
             ha='center', va='bottom', fontsize=F_SIZE['note'], 
             color=C['pipe'], fontweight='bold')

    # --- (d) 质量与资源学术表 ---
    ax4 = fig.add_subplot(gs[1, 0:3])
    rows_d = [
        ("PSNR (Baseline $\\to$ TVM)", f"{DATA['quality']['psnr_b']} $\\to$ {DATA['quality']['psnr_c']} dB"),
        ("SSIM (Baseline $\\to$ TVM)", f"{DATA['quality']['ssim_b']} $\\to$ {DATA['quality']['ssim_c']}"),
        ("Compiled Artifact Size", f"{DATA['resource']['artifact']} MiB"),
        ("Avg CPU (Usr/Sys/Idl/Wait)", f"{DATA['resource']['cpu']} (%)"),
        ("Minimum Free Memory", f"{DATA['resource']['ram']} MB")
    ]
    draw_academic_table(ax4, "(d) Quality & Resource Profile", ["Metric", "Value / Trend"], rows_d)

    # --- (e) 执行边界学术表 ---
    ax5 = fig.add_subplot(gs[1, 3:6])
    rows_e = DATA['boundary']
    rows_e.extend([("Host Disturbance", "AWGN Channel (SNR=10)"), ("Framework Bypass", "MNN (Dynamic Shape)")])
    draw_academic_table(ax5, "(e) Execution Boundaries & Conditions", ["Constraint / Aspect", "Specification"], rows_e)

    # 保存高精度图像
    out_path = Path("paper_fig4_6_tvm_overview_ieee_v3.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] 图表生成成功: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()