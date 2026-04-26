#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 4.1 TVM 编译优化流水线与反馈闭环 — IEEE 顶刊级架构图 (布局优化版)
修改点：
1. 扩大飞腾验证区 (Phytium-side) 外框，确保文字完全包入。
2. 下移说明文字 (Note)，增加底部留白，消除重合。
3. 优化正交连线逻辑，匹配更宽的布局。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# ================= 1. 严格执行字体与字号规范 =================
def setup_ieee_strict_style():
    plt.rcParams['font.family'] = ['Times New Roman', 'SimHei', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    global F_SIZE
    F_SIZE = {
        "caption": 9,      
        "zone_title": 8.5, 
        "box_title": 8,    
        "box_desc": 7,     
        "note": 8          
    }
    
    global C
    C = {
        "text": "#000000",
        "text_muted": "#404040",
        "host_bg": "#F8F9FA",      
        "phy_bg": "#FDFEFE",       
        "zone_edge": "#BDC3C7",    
        
        "data_fill": "#F2F3F4",    
        "data_edge": "#7F8C8D",    
        "action_edge": "#1A5276",  
        "feedback_edge": "#B03A2E",
        
        "arrow_main": "#1A5276",   
        "arrow_fb": "#B03A2E"      
    }
    
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'

# ================= 2. 核心绘制工具 =================
def draw_node(ax, cx, cy, w, h, title, desc, style='action'):
    """绘制流水线节点"""
    if style == 'data':
        facecolor, edgecolor, ls, lw = C['data_fill'], C['data_edge'], '-', 1.0
    elif style == 'action':
        facecolor, edgecolor, ls, lw = '#FFFFFF', C['action_edge'], '-', 1.2
    elif style == 'constraint':
        facecolor, edgecolor, ls, lw = '#FFFFFF', C['action_edge'], '--', 1.0
    elif style == 'feedback':
        facecolor, edgecolor, ls, lw = '#FFFFFF', C['feedback_edge'], '-', 1.5
    elif style == 'deploy':
        facecolor, edgecolor, ls, lw = '#FFFFFF', C['action_edge'], '-', 1.5
        
    rect = patches.FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0,rounding_size=2",
        facecolor=facecolor, edgecolor=edgecolor,
        linewidth=lw, linestyle=ls, zorder=3
    )
    ax.add_patch(rect)
    
    # 居中写入文本
    ax.text(cx, cy + 1.2, title, ha='center', va='bottom',
            fontsize=F_SIZE['box_title'], fontweight='bold', color=C['text'], zorder=4)
    ax.text(cx, cy - 1.2, desc, ha='center', va='top',
            fontsize=F_SIZE['box_desc'], color=C['text_muted'], zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, style='main'):
    """绘制直线箭头"""
    color = C['arrow_fb'] if style == 'feedback' else C['arrow_main']
    lw = 1.5 if style == 'feedback' else 1.2
    ls = '--' if style == 'dashed' else '-'
    
    arrow = patches.FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>,head_length=5,head_width=3.5",
        color=color, linewidth=lw, linestyle=ls, zorder=2
    )
    ax.add_patch(arrow)

def draw_polyline_arrow(ax, xs, ys, style='main'):
    """绘制正交折线箭头 (Manhattan Routing)"""
    if style == 'feedback':
        color, lw, ls = C['arrow_fb'], 1.5, '-'
    elif style == 'dashed':
        color, lw, ls = C['action_edge'], 1.0, '--'
    else:
        color, lw, ls = C['arrow_main'], 1.2, '-'
        
    ax.plot(xs[:-1], ys[:-1], color=color, linewidth=lw, linestyle=ls, zorder=2)
    arrow = patches.FancyArrowPatch(
        (xs[-2], ys[-2]), (xs[-1], ys[-1]),
        arrowstyle="-|>,head_length=5,head_width=3.5",
        color=color, linewidth=lw, linestyle=ls, zorder=2
    )
    ax.add_patch(arrow)

# ================= 3. 主渲染逻辑 =================
def render_figure():
    setup_ieee_strict_style()
    # 保持 7.16 英寸宽度，高度微增以容纳下移的说明文字
    fig, ax = plt.subplots(figsize=(7.16, 3.8), dpi=600)
    ax.set_xlim(0, 100)
    ax.set_ylim(-10, 100) # 扩展坐标系底部，为 Note 留出空间
    ax.axis('off')
    
    # ------------------- 1. 物理区域背景 -------------------
    # 上位机域 (适当收紧)
    host_zone = patches.FancyBboxPatch(
        (1.5, 6), 62.5, 88, boxstyle="round,pad=0,rounding_size=3",
        facecolor=C['host_bg'], edgecolor=C['zone_edge'], linestyle='--', linewidth=0.8, zorder=1
    )
    ax.add_patch(host_zone)
    ax.text(3, 91, "Host-side Compilation & Tuning (上位机高算力编译区)", 
            ha='left', va='center', fontsize=F_SIZE['zone_title'], fontweight='bold', color=C['text_muted'])
    
    # [重构] 飞腾部署域：扩大宽度从 32 -> 34.5，确保覆盖所有内容
    phy_zone = patches.FancyBboxPatch(
        (65.0, 6), 33.5, 88, boxstyle="round,pad=0,rounding_size=3",
        facecolor=C['phy_bg'], edgecolor=C['zone_edge'], linestyle='--', linewidth=0.8, zorder=1
    )
    ax.add_patch(phy_zone)
    ax.text(66.5, 91, "Phytium-side Deployment (飞腾板端验证区)", 
            ha='left', va='center', fontsize=F_SIZE['zone_title'], fontweight='bold', color=C['text_muted'])

    # ------------------- 2. 节点排布 -------------------
    H = 12
    # 主线 (Y = 50)
    draw_node(ax, 8,  50, 12, H, "PyTorch Model", "(原始语义解码器)", style='data')
    draw_node(ax, 23, 50, 14, H, "静态 ONNX 规范化", "(常量折叠 / 图化简)", style='action')
    draw_node(ax, 38, 50, 12, H, "Relax IR", "(高级中间表示)", style='data')
    draw_node(ax, 54, 50, 16, H, "MetaSchedule 调优", "(500 trials 增量搜索)", style='action')
    
    draw_node(ax, 73, 50, 13, H, "优化 Artifact", "(1.57 MiB 端侧产物)", style='deploy')
    draw_node(ax, 90.5, 50, 16.5, H, "端到端重建", "(串行230ms / 流水134.6ms)", style='action')
    
    # 约束条件 (Y = 78)
    draw_node(ax, 54, 78, 16, H, "编译目标收敛", "(cortex-a72 + neon)", style='constraint')
    draw_node(ax, 82, 78, 15, H, "安全运行时重构", "(规避 libc10.so 阻塞)", style='constraint')
    
    # 反馈闭环 (Y = 22)
    draw_node(ax, 82, 22, 14, H, "图内 Profiling", "(定位热点 family)", style='feedback')
    draw_node(ax, 54, 22, 16, H, "TIR 算子手写改写", "(消除缓冲 / 向量归约)", style='feedback')

    # ------------------- 3. 数据流连线 -------------------
    # 主流水线
    draw_arrow(ax, 14, 50, 16,   50)
    draw_arrow(ax, 30, 50, 32,   50)
    draw_arrow(ax, 44, 50, 46,   50)
    draw_arrow(ax, 62, 50, 66.5, 50) 
    draw_arrow(ax, 79.5, 50, 82.2, 50)
    
    # 约束注入 (Manhattan)
    draw_arrow(ax, 54, 72, 54, 56, style='dashed')
    draw_polyline_arrow(ax, [82, 82, 73, 73], [72, 64, 64, 56], style='dashed')
    
    # 物理调优闭环 (The Tuning Loop)
    draw_polyline_arrow(ax, [75, 75, 82, 82], [44, 36, 36, 28], style='feedback')
    draw_arrow(ax, 75, 22, 62, 22, style='feedback')
    draw_polyline_arrow(ax, [54, 54, 71, 71], [28, 36, 36, 44], style='feedback')

    # ------------------- 4. 全局标题与说明 -------------------
    fig.suptitle("图 4.1 TVM 编译器级端到端优化与算子级手写改写流水线", 
                 fontsize=F_SIZE['caption'], fontweight='bold', y=0.96)
    
    # [修正] 下移说明文字位置，避免与图框重叠
    note_text = "说明：蓝色实线代表静态图转换与编译主数据流；虚线代表环境与物理目标的先验约束；\n红色高亮折线代表基于飞腾真机 Profiling 的热点算子反馈与重新编译闭环 (Tuning Loop)。"
    ax.text(1.5, -6, note_text, ha='left', va='bottom', fontsize=F_SIZE['note'], color=C['text_muted'])

    # ------------------- 5. 导出 -------------------
    # [修正] 增加底部边缘距离，确保 Note 不被裁剪
    plt.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.15)
    out_path = Path("paper_fig4_1_tvm_opt_flow_strict_ieee_v3.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] Fig 4.1 layout optimized: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()