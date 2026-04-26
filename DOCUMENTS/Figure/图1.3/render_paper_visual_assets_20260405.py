import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import os

# =========================================================
# 1. IEEE顶刊字体与全局样式规范配置
# =========================================================
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.linewidth'] = 0.75

# 匹配系统黑体
font_path = None
if os.path.exists("C:/Windows/Fonts/simhei.ttf"):
    font_path = "C:/Windows/Fonts/simhei.ttf"
else:
    for f in fm.findSystemFonts():
        if 'simhei' in f.lower() or 'wqy' in f.lower() or 'msyh' in f.lower():
            font_path = f
            break

zh_font = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties(family=['sans-serif'])

FS_CAPTION = 9    # 图表标题/大区块 (8-9 pt)
FS_AXIS    = 8    # 主体模块文本 (7-8 pt)
FS_NOTE    = 6.5  # 注释/说明/公式文本 (6-7 pt)

# =========================================================
# 2. IEEE学术高对比度配色
# =========================================================
C_BG_BASE   = '#F8F9FA'  
C_BG_DEEP   = '#E9ECEF'  
C_EDGE_MAIN = '#6C757D'  
C_BOX_BG    = '#FFFFFF'  
C_BOX_EDGE  = '#212529'  

C_TEXT_MAIN = '#212529'  
C_TEXT_SUB  = '#495057'  
C_LINE      = '#343A40'  

C_BLUE_DARK = '#1565C0'  
C_GREEN_DRK = '#2E7D32'  

# =========================================================
# 3. 画布初始化 (7.16 英寸标准双栏宽)
# =========================================================
fig, ax = plt.subplots(figsize=(7.16, 4.5), dpi=600)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')

# =========================================================
# 4. 核心绘图函数
# =========================================================
def draw_box(x, y, w, h, title, subtitle=None, bg_color=C_BOX_BG, edge_color=C_BOX_EDGE, style='solid', lw=0.75):
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                 linewidth=lw, linestyle=style, edgecolor=edge_color, facecolor=bg_color, zorder=2)
    ax.add_patch(box)
    
    y_text = y + h/2 if not subtitle else y + h/2 + 0.15
    ax.text(x + w/2, y_text, title, ha='center', va='center', fontproperties=zh_font, fontsize=FS_AXIS, color=C_TEXT_MAIN, fontweight='bold')
    if subtitle:
        ax.text(x + w/2, y + h/2 - 0.25, subtitle, ha='center', va='center', fontproperties=zh_font, fontsize=FS_NOTE, color=C_TEXT_SUB)
    return (x, y+h/2), (x+w, y+h/2), (x+w/2, y), (x+w/2, y+h)

def draw_arrow(start, end, style='-', arrowstyle='-|>', lw=0.75, color=C_LINE, ms=10):
    arrow = patches.FancyArrowPatch(start, end, arrowstyle=arrowstyle, mutation_scale=ms,
                                    linestyle=style, linewidth=lw, color=color, zorder=1)
    ax.add_patch(arrow)

def add_label(x, y, text, ha='center', va='center', bg_color=None, text_color=C_TEXT_MAIN, fontsize=FS_NOTE, border=False):
    kwargs = {'ha':ha, 'va':va, 'fontproperties':zh_font, 'fontsize':fontsize, 'color':text_color}
    if bg_color:
        ec = C_EDGE_MAIN if border else 'none'
        kwargs['bbox'] = dict(facecolor=bg_color, edgecolor=ec, boxstyle='round,pad=0.25', linewidth=0.5)
    ax.text(x, y, text, **kwargs)

# =========================================================
# 5. 区块与结构绘制 (释放空间版)
# =========================================================
# --- 象限 1：上位机发送端 ---
x_uc, y_uc, w_uc, h_uc = 0.2, 5.0, 4.4, 4.4
uc_bg = patches.FancyBboxPatch((x_uc, y_uc), w_uc, h_uc, boxstyle="round,pad=0.2,rounding_size=0.2",
                               linewidth=1.0, edgecolor=C_EDGE_MAIN, facecolor=C_BG_BASE, zorder=0)
ax.add_patch(uc_bg)
add_label(x_uc, y_uc + h_uc + 0.3, "上位机执行范围", ha='left', va='bottom', bg_color=C_EDGE_MAIN, text_color='white', fontsize=FS_CAPTION)

pt_img_l, pt_img_r, pt_img_b, pt_img_t = draw_box(x_uc + 0.4, y_uc + 2.6, 3.6, 1.2, "弱网图像输入", "支持 256x256 或动态尺寸")
pt_enc_l, pt_enc_r, pt_enc_b, pt_enc_t = draw_box(x_uc + 0.4, y_uc + 0.6, 3.6, 1.2, "语义编码与信道扰动", "PyTorch Latent & AWGN 模拟")
draw_arrow(pt_img_b, pt_enc_t)

# --- 象限 2：飞腾核心架构 (向右推，留出 0.4 的间隙) ---
x_phy, y_phy, w_phy, h_phy = 5.4, 0.6, 10.4, 8.8
phy_bg = patches.FancyBboxPatch((x_phy, y_phy), w_phy, h_phy, boxstyle="round,pad=0.2,rounding_size=0.2",
                                linewidth=1.0, edgecolor=C_EDGE_MAIN, facecolor=C_BG_BASE, zorder=0)
ax.add_patch(phy_bg)
add_label(x_phy, y_phy + h_phy + 0.3, "飞腾多核异构双模式架构", ha='left', va='bottom', bg_color=C_EDGE_MAIN, text_color='white', fontsize=FS_CAPTION)

# 2.1 数据面
x_dp, y_dp, w_dp, h_dp = 5.8, 5.6, 6.0, 3.4
dp_bg = patches.FancyBboxPatch((x_dp, y_dp), w_dp, h_dp, boxstyle="round,pad=0.1,rounding_size=0.1",
                               linewidth=1.0, linestyle='--', edgecolor=C_BLUE_DARK, facecolor=C_BG_DEEP, zorder=1)
ax.add_patch(dp_bg)
add_label(x_dp + 0.2, y_dp + h_dp - 0.3, "数据面 (Linux)", ha='left', bg_color=C_BLUE_DARK, text_color='white', fontsize=FS_AXIS)

pt_tvm_l, pt_tvm_r, pt_tvm_b, pt_tvm_t = draw_box(x_dp + 0.4, y_dp + 1.8, 5.2, 1.0, "TVM 极致性能 (4核模式)", "134.6 ms/张 (流水线加速)")
pt_mnn_l, pt_mnn_r, pt_mnn_b, pt_mnn_t = draw_box(x_dp + 0.4, y_dp + 0.4, 5.2, 1.0, "MNN 灵活部署 (动态尺寸)", "混合分辨率原生处理")

# 2.2 控制面
x_cp, y_cp, w_cp, h_cp = 5.8, 1.0, 6.0, 3.0
cp_bg = patches.FancyBboxPatch((x_cp, y_cp), w_cp, h_cp, boxstyle="round,pad=0.1,rounding_size=0.1",
                               linewidth=1.0, linestyle='--', edgecolor=C_GREEN_DRK, facecolor=C_BG_DEEP, zorder=1)
ax.add_patch(cp_bg)
add_label(x_cp + 0.2, y_cp + h_cp - 0.3, "控制面 (RTOS / Bare Metal)", ha='left', bg_color=C_GREEN_DRK, text_color='white', fontsize=FS_AXIS)

pt_ctrl_l, pt_ctrl_r, pt_ctrl_b, pt_ctrl_t = draw_box(x_cp + 0.4, y_cp + 0.6, 5.2, 1.6, "安全作业准入与运行控制", "准入校验 / 心跳监护 / 安全停机")

# 2.3 终端演示输出 (缩小并向右推，拉长连线)
x_out, y_out, w_out, h_out = 12.8, 3.6, 2.6, 2.6
pt_out_l, pt_out_r, pt_out_b, pt_out_t = draw_box(x_out, y_out, w_out, h_out, "演示界面展示", "Electron UI\n本地落盘")

# --- 象限 3：系统状态机展示面板 ---
x_stat, y_stat, w_stat, h_stat = 0.2, 0.5, 4.4, 4.0
stat_bg = patches.FancyBboxPatch((x_stat, y_stat), w_stat, h_stat, boxstyle="round,pad=0.2,rounding_size=0.2",
                               linewidth=1.0, edgecolor=C_EDGE_MAIN, facecolor=C_BG_BASE, zorder=0)
ax.add_patch(stat_bg)
add_label(x_stat, y_stat + h_stat + 0.3, "控制面核心机制验证", ha='left', va='bottom', bg_color=C_EDGE_MAIN, text_color='white', fontsize=FS_CAPTION)

sm_bg = patches.FancyBboxPatch((x_stat + 0.3, y_stat + 1.4), 3.8, 2.0, boxstyle="round,pad=0.1,rounding_size=0.15",
                                 linewidth=0.75, edgecolor=C_BOX_EDGE, facecolor=C_BOX_BG, zorder=2)
ax.add_patch(sm_bg)
ax.text(x_stat + 2.2, y_stat + 3.15, "确定性有限状态机 (FSM)", ha='center', va='center', fontproperties=zh_font, fontsize=FS_AXIS, color=C_TEXT_MAIN, fontweight='bold')

b_w, b_h = 0.85, 0.45
r_b = patches.FancyBboxPatch((x_stat + 0.5, y_stat + 2.3), b_w, b_h, boxstyle="round,pad=0.05", lw=0.75, ec=C_BOX_EDGE, fc=C_BOX_BG, zorder=3)
c_b = patches.FancyBboxPatch((x_stat + 1.75, y_stat + 2.3), b_w, b_h, boxstyle="round,pad=0.05", lw=0.75, ec=C_BOX_EDGE, fc=C_BOX_BG, zorder=3)
ru_b= patches.FancyBboxPatch((x_stat + 3.0, y_stat + 2.3), b_w, b_h, boxstyle="round,pad=0.05", lw=0.75, ec=C_BOX_EDGE, fc=C_BOX_BG, zorder=3)
s_b = patches.FancyBboxPatch((x_stat + 1.75, y_stat + 1.6), b_w, b_h, boxstyle="round,pad=0.05", lw=0.75, ec=C_BOX_EDGE, fc=C_BOX_BG, zorder=3)
ax.add_patch(r_b); ax.add_patch(c_b); ax.add_patch(ru_b); ax.add_patch(s_b)

ax.text(x_stat + 0.925, y_stat + 2.525, "READY", ha='center', va='center', fontsize=FS_NOTE, color=C_TEXT_MAIN)
ax.text(x_stat + 2.175, y_stat + 2.525, "CHECKING", ha='center', va='center', fontsize=FS_NOTE, color=C_TEXT_MAIN)
ax.text(x_stat + 3.425, y_stat + 2.525, "RUNNING", ha='center', va='center', fontsize=FS_NOTE, color=C_TEXT_MAIN)
ax.text(x_stat + 2.175, y_stat + 1.825, "SAFE_STOP", ha='center', va='center', fontsize=FS_NOTE, color=C_TEXT_MAIN)

# 正交折线连接 FSM
draw_arrow((x_stat + 1.35, y_stat + 2.525), (x_stat + 1.75, y_stat + 2.525), arrowstyle='-|>', lw=0.75, ms=8)
draw_arrow((x_stat + 2.6, y_stat + 2.525), (x_stat + 3.0, y_stat + 2.525), arrowstyle='-|>', lw=0.75, ms=8)
ax.plot([x_stat + 3.425, x_stat + 3.425], [y_stat + 2.3, y_stat + 1.825], ls='-', color=C_LINE, lw=0.75, zorder=1)
draw_arrow((x_stat + 3.425, y_stat + 1.825), (x_stat + 2.6, y_stat + 1.825), arrowstyle='-|>', lw=0.75, ms=8)
ax.plot([x_stat + 0.925, x_stat + 0.925], [y_stat + 2.3, y_stat + 1.825], ls='-', color=C_LINE, lw=0.75, zorder=1)
draw_arrow((x_stat + 0.925, y_stat + 1.825), (x_stat + 1.75, y_stat + 1.825), arrowstyle='-|>', lw=0.75, ms=8)

pt_fit_l, pt_fit_r, pt_fit_b, pt_fit_t = draw_box(x_stat + 0.3, y_stat + 0.2, 3.8, 1.0, "FIT 故障注入真机验证", "工件验签拦截 / 参数越限 / 心跳超时")

# =========================================================
# 6. 数据流向连线 (拉长连线版)
# =========================================================
# 上位机 -> 数据面
y_mid_enc = pt_enc_r[1]
draw_arrow(pt_enc_r, (x_dp, y_mid_enc), lw=1.0)
add_label((pt_enc_r[0] + x_dp)/2, y_mid_enc + 0.25, "安全通信链路", ha='center', va='bottom', bg_color=C_BG_BASE)
add_label((pt_enc_r[0] + x_dp)/2, y_mid_enc - 0.25, "32x32x32 Latent", ha='center', va='top')

# 数据面 -> 输出
y_dp_out = y_dp + h_dp/2
x_elbow = 12.4
draw_arrow((x_dp + w_dp, y_dp_out), (x_elbow, y_dp_out), lw=1.0)
ax.plot([x_elbow, x_elbow], [y_dp_out, pt_out_t[1]], ls='-', color=C_LINE, lw=1.0)
draw_arrow((x_elbow, pt_out_t[1]), pt_out_t, lw=1.0)
add_label((x_dp + w_dp + x_elbow)/2, y_dp_out + 0.2, "重建图像流", ha='center', va='bottom', bg_color=C_BG_BASE)

# 控制面 -> 输出
y_cp_out = y_cp + h_cp/2
draw_arrow((x_cp + w_cp, y_cp_out), (x_elbow, y_cp_out), style='--', lw=1.0)
ax.plot([x_elbow, x_elbow], [y_cp_out, pt_out_b[1]], ls='--', color=C_LINE, lw=1.0)
draw_arrow((x_elbow, pt_out_b[1]), pt_out_b, style='--', lw=1.0)
add_label((x_cp + w_cp + x_elbow)/2, y_cp_out - 0.2, "系统遥测日志", ha='center', va='top', bg_color=C_BG_BASE)

# 数据面 <-> 控制面 (OpenAMP 双向直连心跳)
x_mid = x_dp + w_dp/2
draw_arrow((x_mid - 0.5, y_dp), (x_mid - 0.5, y_cp + h_cp), arrowstyle='<|-|>', lw=1.5, color=C_BLUE_DARK, ms=12)
add_label(x_mid - 0.6, (y_dp + y_cp + h_cp)/2, "OpenAMP\nRPMsg", ha='right', va='center', text_color=C_BLUE_DARK)

# ★ 状态机验证 -> 控制面 (拉直的中轴虚线箭头，消除歧义)
draw_arrow((x_stat + w_stat, 2.5), (x_cp, 2.5), style='--', lw=1.0)
add_label((x_stat + w_stat + x_cp)/2, 2.65, "状态机逻辑映射", ha='center', va='bottom', bg_color=C_BG_BASE)

# =========================================================
# 7. 保存与输出
# =========================================================
plt.tight_layout()
plt.savefig('paper_fig_cover_summary_cn_20260405_ieee_v6.png', format='png', bbox_inches='tight', dpi=600)