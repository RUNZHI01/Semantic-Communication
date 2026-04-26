#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 4.2 关键算子图内性能差异与热点占比（OpenAMP 三核板态） — IEEE 顶刊严格规范版
优化点：
1. 学术级饼图：补齐了 39.09% 的 "Others" 切片，保证面积占比真实客观。
2. 智能刻度对齐：根据是否存在 ACL 数据，动态居中 X 轴的算子名称标签。
3. 完美防重叠：采用 Span Bracket (跨度方括号) 展示算子优化提升比例。
4. 严格规范：1x2 跨栏布局 (7.16英寸)，6-9pt 印刷体映射，中英文字体隔离。
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
    
    # IEEE 顶刊经典调色板
    global C
    C = {
        "text": "#000000",
        "baseline": "#A6ACAF",    # 学术银灰 (MetaSchedule基线)
        "handwritten": "#21618C", # 海军深蓝 (手写优化)
        "acl": "#B03A2E",         # 学术砖红 (ACL)
        "highlight": "#1B9E77",   # 翠绿色 (正向收益高亮)
        "grid": "#EAECEF",        
        "spine": "#000000"        
    }
    
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.linewidth'] = 0.75
    plt.rcParams['xtick.major.width'] = 0.75
    plt.rcParams['ytick.major.width'] = 0.75

# ================= 2. 核心实验数据 =================
# 热点算子占比 (Top 8 + Others 归一化)
HOTSPOT_LABELS = ['transpose1', 'transpose2', 'transpose_add6', 'conv2d3', 
                  'mean4', 'variance4', 'mean3', 'variance3', 'Others (其他算子)']
HOTSPOT_SIZES = [14.60, 12.17, 10.46, 7.10, 6.66, 4.27, 3.50, 2.15]
# 补齐未统计的部分，确保饼图真实面积 = 100%
HOTSPOT_SIZES.append(100.0 - sum(HOTSPOT_SIZES)) 

# 性能对比 (us): (名称, Baseline, Handwritten, ACL)
OPS_COMPARE = [
    ('transpose1', 55016, 48249, 0),
    ('transpose2', 43912, 39143, 0),
    ('transpose_add6', 40916, 34790, 0),
    ('variance3', 3581, 2736, 0),
    ('mean4', 3102, 4648, 11178),
]

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
    tick_len = 1500 # Y轴量级较大，短线设定为 1500 us
    ax.plot([x_left, x_right], [y_height, y_height], color=color, lw=1.0)
    ax.plot([x_left, x_left], [y_height - tick_len, y_height], color=color, lw=1.0)
    ax.plot([x_right, x_right], [y_height - tick_len, y_height], color=color, lw=1.0)
    ax.text((x_left + x_right) / 2, y_height + 800, text, 
            ha='center', va='bottom', fontsize=fontsize, fontweight='bold', color=color)

# ================= 4. 主渲染逻辑 =================
def render_figure():
    setup_ieee_strict_style()
    
    # 尺寸控制：7.16 英寸宽（IEEE跨栏标准），3.0 英寸高
    fig = plt.figure(figsize=(7.16, 3.0), dpi=600)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.45], wspace=0.25)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    
    fig.suptitle("图 4.2 关键算子图内性能差异与热点占比（OpenAMP 三核板态）", 
                 fontsize=F_SIZE['caption'], fontweight='bold', y=1.02)

    # ------------------- 子图 (a): 热点算子占比饼图 -------------------
    # 采用学术级单色系渐变 (蓝灰系列)
    colors_pie = ['#154360', '#1A5276', '#21618C', '#2874A6', 
                  '#2E86C1', '#3498DB', '#5DADE2', '#85C1E9', '#D5D8DC']
    explode = [0.06, 0.04, 0.02, 0, 0, 0, 0, 0, 0] # 仅微小分离 Top 3
    
    wedges, texts, autotexts = ax1.pie(
        HOTSPOT_SIZES, explode=explode, labels=HOTSPOT_LABELS, colors=colors_pie, 
        autopct='%1.1f%%', shadow=False, startangle=90, pctdistance=0.82,
        textprops={'fontsize': F_SIZE['note'], 'color': C['text']}
    )
    
    # 根据底色深浅智能调整百分比文字颜色
    for i, autotext in enumerate(autotexts):
        autotext.set_color('white' if i < 5 else 'black')
        autotext.set_fontsize(F_SIZE['note'])
        autotext.set_fontweight('bold')
        
    ax1.set_title("(a) 热点算子占比分布", fontsize=F_SIZE['caption'], pad=8)

    # ------------------- 子图 (b): 关键算子性能对比 -------------------
    ops_short = [op[0] for op in OPS_COMPARE]
    x = np.arange(len(ops_short))
    width = 0.26
    
    dynamic_xticks = [] # 智能刻度居中记录器
    
    for i, (name, base, hand, aclv) in enumerate(OPS_COMPARE):
        x_base = x[i] - width
        x_hand = x[i]
        
        # 绘制 Baseline 与 Handwritten
        ax2.bar(x_base, base, width, color=C['baseline'], edgecolor=C['spine'], linewidth=0.6)
        ax2.bar(x_hand, hand, width, color=C['handwritten'], edgecolor=C['spine'], linewidth=0.6)
        
        # 顶部数值 (去除无意义的 0 小数位)
        ax2.text(x_base, base + 1200, f"{base}", ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['text'])
        ax2.text(x_hand, hand + 1200, f"{hand}", ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['text'])
        
        # 跨度括号与收益
        improvement = (base - hand) / base * 100
        bracket_y = max(base, hand) + 6000
        color = C['highlight'] if improvement > 0 else C['acl']
        draw_span_bracket(ax2, x_base, x_hand, bracket_y, 
                          f"{improvement:+.1f}%", color, F_SIZE['note'])
        
        # 绘制 ACL (若存在) 并智能记录 Tick 刻度中心
        if aclv > 0:
            x_acl = x[i] + width
            ax2.bar(x_acl, aclv, width, color=C['acl'], edgecolor=C['spine'], linewidth=0.6)
            ax2.text(x_acl, aclv + 1200, f"{aclv}", ha='center', va='bottom', fontsize=F_SIZE['tick'], color=C['text'])
            dynamic_xticks.append(x[i]) # 存在三根柱子，Tick 居中于 x[i]
        else:
            dynamic_xticks.append(x[i] - width/2) # 仅两根柱子，Tick 居中于两者之间
            
    # 设置坐标轴与布局
    ax2.set_ylabel("Latency (us)", fontsize=F_SIZE['label'])
    ax2.set_ylim(0, 72000) # 拔高上限，防止 Bracket 撞顶
    ax2.set_xticks(dynamic_xticks)
    ax2.set_xticklabels(ops_short, fontsize=F_SIZE['tick'])
    ax2.set_title("(b) 关键算子性能路线对比", fontsize=F_SIZE['caption'], pad=8)
    
    # 极简学术图例
    import matplotlib.patches as mpatches
    legend_handles = [
        mpatches.Patch(color=C['baseline'], label='MetaSchedule'),
        mpatches.Patch(color=C['handwritten'], label='Handwritten'),
        mpatches.Patch(color=C['acl'], label='ACL')
    ]
    ax2.legend(handles=legend_handles, loc='upper right', fontsize=F_SIZE['legend'], 
               frameon=False, ncol=1)
    
    format_academic_axes(ax2)

    # ------------------- 导出处理 -------------------
    fig.text(0.5, 0.02, 
             "说明：左图补充了 39.09% 的非热点计算；右图对比了三条工程优化路线，手写优化在主链算子上取得全面正收益。", 
             ha='center', va='top', fontsize=F_SIZE['note'], color='#555555')

    plt.subplots_adjust(bottom=0.18)
    out_path = Path("paper_fig4_2_operator_hotspot_strict_ieee.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] 图 4.2 严格规范版生成成功: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()