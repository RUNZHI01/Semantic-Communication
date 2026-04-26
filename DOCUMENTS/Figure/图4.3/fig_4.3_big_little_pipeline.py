#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 4.3 异构大小核流水线性能差异 (OpenAMP 三核统一板态) — 终极精修版
优化：
1. 完美解决标签重叠：引入 IEEE 标准的跨度方括号 (Span Bracket)。
2. 顶刊级配色：学术银灰 (基线) + 海军蓝 (优化) + 砖红 (涨幅高亮)。
3. 严格遵循字号与中英文字体映射规范。
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
    
    # IEEE 顶刊经典调色板 (冷暖高对比，黑白打印友好)
    global C
    C = {
        "text": "#000000",        # 纯黑文本
        "serial": "#A6ACAF",      # 学术银灰 (串行/基线，低调退后)
        "pipeline": "#21618C",    # 海军深蓝 (流水线优化，视觉主体)
        "highlight": "#B03A2E",   # 学术砖红 (用于跨度标签，冷暖对比吸睛)
        "grid": "#EAECEF",        # 浅灰网格线
        "spine": "#000000"        # 坐标轴黑线
    }
    
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.linewidth'] = 0.75      # 极细学术边框
    plt.rcParams['xtick.major.width'] = 0.75
    plt.rcParams['ytick.major.width'] = 0.75

# ================= 2. 核心实验数据 =================
# 左图：4-core 性能模式
LEFT_SERIAL_MEDIAN = 231.5
LEFT_PIPELINE_MEDIAN = 134.6
LEFT_SERIAL_THR = 4.33
LEFT_PIPELINE_THR = 6.75
LEFT_SERIAL_TOT = 69.3
LEFT_PIPELINE_TOT = 44.4

# 右图：3-core 演示模式三路线
ROUTES = ['MetaSchedule\n优化', 'MetaSchedule +\n手写算子优化', 'ACL\n单热点探索线']
SERIAL_MS = [360.2, 342.9, 349.4]
PIPELINE_MS = [251.9, 252.6, 258.9]
UPLIFT_PCT = [44.1, 35.5, 34.7]

# ================= 3. 辅助学术绘图函数 =================
def format_academic_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(C['spine'])
    ax.spines['bottom'].set_color(C['spine'])
    ax.tick_params(axis='both', which='major', labelsize=F_SIZE['tick'], color=C['spine'])
    ax.yaxis.grid(True, linestyle='--', color=C['grid'], linewidth=0.5)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

def draw_span_bracket(ax, x_left, x_right, y_height, text, color, fontsize):
    """绘制学术标准的跨度方括号并居中添加文本"""
    tick_len = 6 # 向下的短线长度
    # 画水平主线
    ax.plot([x_left, x_right], [y_height, y_height], color=color, lw=1.0)
    # 画两侧向下短线
    ax.plot([x_left, x_left], [y_height - tick_len, y_height], color=color, lw=1.0)
    ax.plot([x_right, x_right], [y_height - tick_len, y_height], color=color, lw=1.0)
    # 在水平线正上方居中写入文字
    ax.text((x_left + x_right) / 2, y_height + 3, text, 
            ha='center', va='bottom', fontsize=fontsize, fontweight='bold', color=color)

# ================= 4. 主渲染逻辑 =================
def render_figure():
    setup_ieee_strict_style()
    
    # 尺寸控制：7.16 英寸宽，2.8 英寸高
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 2.8), dpi=600, 
                                   gridspec_kw={'width_ratios': [1, 1.4]})
    
    # 全局标题 (9pt)
    fig.suptitle("图 4.3 加入异构大小核流水线的性能差异", 
                 fontsize=F_SIZE['caption'], fontweight='bold', y=1.02)

    # ------------------- 子图 (a): 4-core Linux -------------------
    categories = ['串行\n(4-core)', '流水线\n(big.LITTLE)']
    medians = [LEFT_SERIAL_MEDIAN, LEFT_PIPELINE_MEDIAN]
    
    bars1 = ax1.bar([0, 1], medians, width=0.45, color=[C['serial'], C['pipeline']], 
                    edgecolor=C['spine'], linewidth=0.6)
    
    # 柱状图顶部数值标注
    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 8,
                 f"{bar.get_height():.1f}", ha='center', va='bottom', 
                 fontsize=F_SIZE['tick'], fontweight='bold', color=C['text'])
    
    # 干净的 Inset 文本
    stats_text = (
        f"Throughput:\n{LEFT_SERIAL_THR} $\\to$ {LEFT_PIPELINE_THR} img/s\n\n"
        f"Total Time (300 img):\n{LEFT_SERIAL_TOT} $\\to$ {LEFT_PIPELINE_TOT} s"
    )
    ax1.text(0.95, 0.90, stats_text, transform=ax1.transAxes,
             fontsize=F_SIZE['note'], va='top', ha='right', color=C['text'], linespacing=1.2)
    
    ax1.set_ylim(0, 300)
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(categories, fontsize=F_SIZE['tick'])
    ax1.set_ylabel("Latency (ms/image)", fontsize=F_SIZE['label'])
    ax1.set_title("(a) 4-Core Performance Mode", fontsize=F_SIZE['caption'], pad=8)
    format_academic_axes(ax1)

    # ------------------- 子图 (b): 3-core 演示模式 -------------------
    x = np.arange(len(ROUTES))
    width = 0.32
    
    bars_serial = ax2.bar(x - width/2, SERIAL_MS, width, label='Serial', 
                          color=C['serial'], edgecolor=C['spine'], linewidth=0.6)
    bars_pipe = ax2.bar(x + width/2, PIPELINE_MS, width, label='big.LITTLE Pipeline', 
                        color=C['pipeline'], edgecolor=C['spine'], linewidth=0.6)
    
    # 数值标注与跨度方括号 (Span Bracket)
    for i in range(len(ROUTES)):
        x_left = x[i] - width/2
        x_right = x[i] + width/2
        
        # 串行数值
        ax2.text(x_left, SERIAL_MS[i] + 5, f"{SERIAL_MS[i]:.1f}",
                 ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['text'])
        # 流水线数值
        ax2.text(x_right, PIPELINE_MS[i] + 5, f"{PIPELINE_MS[i]:.1f}",
                 ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['text'])
        
        # 🌟 修复重叠：计算安全的支架高度，并调用辅助函数绘制
        bracket_y = max(SERIAL_MS[i], PIPELINE_MS[i]) + 25 
        draw_span_bracket(ax2, x_left, x_right, bracket_y, 
                          f"+{UPLIFT_PCT[i]:.1f}%", C['highlight'], F_SIZE['note'])
    
    # 将上限拔高至 460，为跨度方括号和涨幅文字留出充足的安全呼吸空间
    ax2.set_ylim(0, 460)
    ax2.set_xticks(x)
    ax2.set_xticklabels(ROUTES, fontsize=F_SIZE['tick'])
    ax2.set_title("(b) 3-Core Demo Mode: Route Comparison", fontsize=F_SIZE['caption'], pad=8)
    
    # 图例设置：水平排列放置右上角
    ax2.legend(loc='upper right', fontsize=F_SIZE['legend'], frameon=False, 
               ncol=2, borderpad=0)
    format_academic_axes(ax2)

    # ------------------- 导出处理 -------------------
    fig.text(0.5, -0.02, 
             "说明：左图展示 4 核性能模式下的基准吞吐；右图比较 3 核演示模式下三条路线获取流水线收益的稳定性。", 
             ha='center', va='top', fontsize=F_SIZE['note'], color='#555555')

    plt.subplots_adjust(wspace=0.25, bottom=0.20)
    out_path = Path("paper_fig4_3_big_little_pipeline_strict_ieee_v2.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] 图 4.3 严格规范完美防重叠版生成成功: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()