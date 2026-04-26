#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图 3.3 双模式边界与能力解耦图 — IEEE 顶刊级架构图
特点：
1. 双柱镜像布局 (Dual-Pillar Dichotomy)，突出物理隔离与不可混淆的边界。
2. 严谨展示 4 核 Linux 与 3 核 Linux + 1 核 RTOS 的物理拓扑差异。
3. 严格遵循 IEEE 配色规范与灰度打印安全设计。
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
        "title": 11,
        "subtitle": 9,
        "zone_title": 9,
        "cpu": 8,
        "note": 7.5,
        "result_main": 12,
        "result_sub": 8
    }
    
    global C
    C = {
        "perf_theme": "#1A5276",   # 学术蓝 (性能侧)
        "sec_theme": "#2C3E50",    # 灰蓝 (安全控制侧)
        "alert": "#B03A2E",        # 警戒红 (边界与提示)
        "text_main": "#000000",
        "text_muted": "#5D6D7E",
        "bg_light": "#F8F9FA",
        "bg_gray": "#EBEDEF"
    }
    
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'

# ================= 2. 核心绘制工具 =================
def draw_rounded_rect(ax, cx, cy, w, h, facecolor, edgecolor, lw=1.2, ls='-', zorder=1):
    """绘制圆角矩形"""
    rect = patches.FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0,rounding_size=2.5",
        facecolor=facecolor, edgecolor=edgecolor,
        linewidth=lw, linestyle=ls, zorder=zorder
    )
    ax.add_patch(rect)

def draw_cpu_core(ax, cx, cy, label, theme_color, is_detached=False):
    """绘制单个 CPU 核心"""
    w, h = 14, 6
    if is_detached:
        draw_rounded_rect(ax, cx, cy, w, h, "none", C['text_muted'], lw=1, ls='--', zorder=3)
        ax.text(cx, cy, label, ha='center', va='center', fontsize=F_SIZE['cpu'], color=C['text_muted'], style='italic', zorder=4)
    else:
        draw_rounded_rect(ax, cx, cy, w, h, "#FFFFFF", theme_color, lw=1.5, zorder=3)
        ax.text(cx, cy, label, ha='center', va='center', fontsize=F_SIZE['cpu'], fontweight='bold', color=theme_color, zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, color, lw=2, ls='-', head_w=4, head_l=5):
    """绘制连线箭头"""
    arrow = patches.FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=f"-|>,head_length={head_l},head_width={head_w}",
        color=color, linewidth=lw, linestyle=ls, zorder=2
    )
    ax.add_patch(arrow)

def draw_double_arrow(ax, x1, y1, x2, y2, color, lw=2.5):
    """绘制双向通信箭头"""
    arrow = patches.FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=f"<|-|>,head_length=5,head_width=4",
        color=color, linewidth=lw, zorder=2
    )
    ax.add_patch(arrow)

# ================= 3. 主渲染逻辑 =================
def render_figure():
    setup_ieee_strict_style()
    # 尺寸控制：7.16 英寸宽 (IEEE 跨栏标准)
    fig, ax = plt.subplots(figsize=(7.16, 4.8), dpi=600)
    
    # 坐标系 0-100
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # ==================== 1. 中央隔离边界 ====================
    # 物理隔离墙
    ax.plot([50, 50], [0, 85], color=C['alert'], linewidth=1.5, linestyle='--', zorder=0)
    
    # 隔离警告框
    draw_rounded_rect(ax, 50, 92, 60, 12, "#FFFFFF", C['alert'], lw=1.5, zorder=5)
    ax.text(50, 95, "STRICT BOUNDARY (物理隔离边界)", ha='center', va='center', 
            fontsize=F_SIZE['zone_title'], fontweight='bold', color=C['alert'], zorder=6)
    ax.text(50, 91, "remoteproc 独占 1 核，底层硬件拓扑已发生改变", ha='center', va='center', 
            fontsize=F_SIZE['note'], color=C['text_main'], zorder=6)
    ax.text(50, 87.5, "左右两区时延不可直接跨界混写比对", ha='center', va='center', 
            fontsize=F_SIZE['note'], color=C['text_muted'], zorder=6)

    # ==================== 2. 左侧：性能模式 (Performance) ====================
    CX_L = 25
    color_L = C['perf_theme']
    
    # 标题与徽章
    ax.text(CX_L, 82, "4-Core Linux 性能模式", ha='center', va='center', 
            fontsize=F_SIZE['title'], fontweight='bold', color=color_L)
    draw_rounded_rect(ax, CX_L, 77, 34, 5, color_L, color_L, zorder=2)
    ax.text(CX_L, 77, "Goal: Max Throughput (跑得快)", ha='center', va='center', 
            fontsize=F_SIZE['subtitle'], fontweight='bold', color="#FFFFFF", zorder=3)
            
    # OS 域：Linux (4 Cores)
    draw_rounded_rect(ax, CX_L, 57, 42, 28, C['bg_light'], color_L, lw=2, zorder=1)
    ax.text(CX_L, 68, "Linux OS (4 Cores 满配)", ha='center', va='center', 
            fontsize=F_SIZE['zone_title'], fontweight='bold', color=color_L, zorder=2)
            
    # CPU 排布
    draw_cpu_core(ax, CX_L-9, 60, "Cortex-A72", color_L)
    draw_cpu_core(ax, CX_L+9, 60, "Cortex-A72", color_L)
    draw_cpu_core(ax, CX_L-9, 51, "Cortex-A55", color_L)
    draw_cpu_core(ax, CX_L+9, 51, "Cortex-A55", color_L)
    
    # 数据流
    draw_arrow(ax, CX_L, 43, CX_L, 30, color_L, lw=2.5)
    ax.text(CX_L+2, 36.5, "Pure\nData\nPlane", ha='left', va='center', 
            fontsize=F_SIZE['note'], fontweight='bold', color=color_L)
            
    # 结果结论框
    draw_rounded_rect(ax, CX_L, 16, 42, 18, "#FFFFFF", color_L, lw=1.5, zorder=2)
    ax.text(CX_L, 22, "官方性能吞吐主口径", ha='center', va='center', 
            fontsize=F_SIZE['subtitle'], fontweight='bold', color=color_L, zorder=3)
    ax.text(CX_L, 17.5, "big.LITTLE 异构流水线开启", ha='center', va='center', 
            fontsize=F_SIZE['result_sub'], color=C['text_muted'], zorder=3)
    ax.text(CX_L, 11.5, "134.6 ms", ha='center', va='center', 
            fontsize=16, fontweight='bold', color=color_L, zorder=3)
    ax.text(CX_L+13, 11.5, "/ image", ha='left', va='center', 
            fontsize=F_SIZE['result_sub'], fontweight='bold', color=color_L, zorder=3)

    # ==================== 3. 右侧：安全演示模式 (Security) ====================
    CX_R = 75
    color_R = C['sec_theme']
    
    # 标题与徽章
    ax.text(CX_R, 82, "3-Core Linux + RTOS 演示模式", ha='center', va='center', 
            fontsize=F_SIZE['title'], fontweight='bold', color=color_R)
    draw_rounded_rect(ax, CX_R, 77, 36, 5, color_R, color_R, zorder=2)
    ax.text(CX_R, 77, "Goal: Safety & Control (用得稳)", ha='center', va='center', 
            fontsize=F_SIZE['subtitle'], fontweight='bold', color="#FFFFFF", zorder=3)
            
    # OS 域：Linux (3 Cores)
    draw_rounded_rect(ax, CX_R, 61, 42, 20, C['bg_light'], color_R, lw=2, zorder=1)
    ax.text(CX_R, 68, "Linux OS (3 Cores)", ha='center', va='center', 
            fontsize=F_SIZE['zone_title'], fontweight='bold', color=color_R, zorder=2)
            
    # CPU 排布 (Linux)
    draw_cpu_core(ax, CX_R-9, 60, "Cortex-A72", color_R)
    draw_cpu_core(ax, CX_R+9, 60, "Cortex-A72", color_R)
    draw_cpu_core(ax, CX_R-9, 54, "Cortex-A55", color_R)
    draw_cpu_core(ax, CX_R+9, 54, "(Detached)", color_R, is_detached=True)
    
    # OS 域：RTOS (1 Core)
    draw_rounded_rect(ax, CX_R, 38, 42, 12, C['bg_gray'], color_R, lw=1.5, ls='--', zorder=1)
    ax.text(CX_R, 41.5, "RTOS Control Plane (1 Core)", ha='center', va='center', 
            fontsize=F_SIZE['zone_title'], fontweight='bold', color=color_R, zorder=2)
            
    # CPU 排布 (RTOS)
    draw_cpu_core(ax, CX_R, 35.5, "Cortex-A55", color_R)
    
    # 跨核通信 (OpenAMP)
    draw_double_arrow(ax, CX_R, 51, CX_R, 44, C['alert'], lw=3)
    # 遮盖线段中间，写上 OpenAMP
    draw_rounded_rect(ax, CX_R, 47.5, 14, 4.5, "#FFFFFF", C['alert'], lw=1, zorder=4)
    ax.text(CX_R, 47.5, "OpenAMP", ha='center', va='center', 
            fontsize=F_SIZE['note'], fontweight='bold', color=C['alert'], zorder=5)
            
    # 控制消息标注
    ax.text(CX_R-3, 47.5, "JOB_REQ\nSAFE_STOP", ha='right', va='center', 
            fontsize=6.5, fontfamily='monospace', color=color_R)
    ax.text(CX_R+3, 47.5, "JOB_ACK\nHEARTBEAT", ha='left', va='center', 
            fontsize=6.5, fontfamily='monospace', color=color_R)

    # 数据流
    draw_arrow(ax, CX_R, 32, CX_R, 25, color_R, lw=2)

    # 结果结论框
    draw_rounded_rect(ax, CX_R, 16, 42, 18, "#FFFFFF", color_R, lw=1.5, zorder=2)
    ax.text(CX_R, 22, "控制面与安全闭环口径", ha='center', va='center', 
            fontsize=F_SIZE['subtitle'], fontweight='bold', color=color_R, zorder=3)
    ax.text(CX_R, 17.5, "5类消息流转与3项真机注入验证", ha='center', va='center', 
            fontsize=F_SIZE['result_sub'], color=C['text_muted'], zorder=3)
    ax.text(CX_R, 11.5, "FIT-01/02/03 Passed", ha='center', va='center', 
            fontsize=13, fontweight='bold', color=color_R, zorder=3)

    # ==================== 4. 全局图例 ====================
    caption = "图 3.3：双模式物理边界与能力解耦 (左图支撑最高吞吐量结论，右图支撑安全控制闭环结论，两者底层硬件拓扑互斥)"
    ax.text(50, -1, caption, ha='center', va='top', fontsize=F_SIZE['note'], color=C['text_muted'])

    # ==================== 5. 导出处理 ====================
    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.08)
    out_path = Path("paper_fig3_3_dual_mode_boundary.png")
    plt.savefig(out_path, bbox_inches='tight', dpi=600)
    print(f"[OK] Fig 3.3 dual mode boundary generated: {out_path.absolute()}")

if __name__ == "__main__":
    render_figure()