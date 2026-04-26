import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import os

# =========================================================
# 1. IEEE顶刊字体与样式规范配置
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

# 字体加载
zh_font = fm.FontProperties(fname=font_path) if font_path else fm.FontProperties(family=['sans-serif'])

FS_CAPTION = 9    # 图表标题/区块标识 (8-9 pt)
FS_AXIS    = 8    # 主体模块文本/轴标题级别 (7-8 pt)
FS_NOTE    = 6.5  # 注释/说明/公式文本/刻度级别 (6-7 pt)

# =========================================================
# 2. IEEE配色方案 (灰度友好)
# =========================================================
C_BG_MAIN   = '#F4F5F7'  
C_EDGE_MAIN = '#ADB5BD'  
C_BG_TRAIN  = '#FAFAFA'  
C_EDGE_TRAIN= '#DEE2E6'  

C_BOX_BG    = '#FFFFFF'  
C_BOX_EDGE  = '#343A40'  
C_BOX_FILL1 = '#F8F9FA'  
C_BOX_FILL2 = '#FDFDFD'  

C_TEXT_MAIN = '#212529'  
C_TEXT_SUB  = '#495057'  
C_LINE      = '#343A40'  

# =========================================================
# 3. 画布初始化 (适配 IEEE 双栏排版宽度，设定为 7.16 英寸)
# =========================================================
fig, ax = plt.subplots(figsize=(7.16, 4.2), dpi=600)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')

# =========================================================
# 4. 绘制底框分组区域 (留出中间布线缝隙)
# =========================================================
# 主链区：高度 3.8, 下边缘在 5.8
main_bg = patches.FancyBboxPatch((0.2, 5.8), 15.6, 3.8, boxstyle="round,pad=0.2,rounding_size=0.2",
                                 linewidth=0.75, edgecolor=C_EDGE_MAIN, facecolor=C_BG_MAIN, zorder=0)
ax.add_patch(main_bg)
ax.text(0.5, 9.3, "部署主链", fontproperties=zh_font, fontsize=FS_CAPTION, color='white', 
        bbox=dict(facecolor='#6C757D', edgecolor='none', boxstyle='round,pad=0.25'))

# 训练区整体左移与主链左侧对齐 (x=0.2)，跨度覆盖全区域
train_bg = patches.FancyBboxPatch((0.2, 0.2), 15.6, 5.4, boxstyle="round,pad=0.2,rounding_size=0.2",
                                  linewidth=0.75, linestyle='--', edgecolor=C_EDGE_TRAIN, facecolor=C_BG_TRAIN, zorder=0)
ax.add_patch(train_bg)
# 标签移至左下角
ax.text(0.5, 0.6, "仅训练阶段启用", fontproperties=zh_font, fontsize=FS_CAPTION, color='white', 
        bbox=dict(facecolor='#868E96', edgecolor='none', boxstyle='round,pad=0.25'))

# =========================================================
# 5. 辅助绘图函数
# =========================================================
def draw_box(x, y, w, h, title, subtitle, bg_color=C_BOX_BG, edge_color=C_BOX_EDGE, zh=False):
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.1",
                                 linewidth=0.75, edgecolor=edge_color, facecolor=bg_color, zorder=2)
    ax.add_patch(box)
    
    if zh:
        ax.text(x + w/2, y + h/2 + 0.1, title, ha='center', va='center', fontproperties=zh_font, fontsize=FS_AXIS, color=C_TEXT_MAIN)
    else:
        ax.text(x + w/2, y + h/2 + 0.1, title, ha='center', va='center', fontsize=FS_AXIS, fontweight='bold', color=C_TEXT_MAIN)
    
    if subtitle:
        ax.text(x + w/2, y + 0.15, subtitle, ha='center', va='bottom', fontproperties=zh_font, fontsize=FS_NOTE, color=C_TEXT_SUB)
    return (x, y+h/2), (x+w, y+h/2), (x+w/2, y), (x+w/2, y+h)

def draw_arrow(start, end, style='-', lw=0.75, color=C_LINE):
    arrow = patches.FancyArrowPatch(start, end, arrowstyle='-|>,head_length=3.5,head_width=2',
                                    linestyle=style, linewidth=lw, color=color, zorder=1)
    ax.add_patch(arrow)

def add_math(x, y, text, ha='center'):
    ax.text(x, y, text, ha=ha, va='center', fontsize=FS_NOTE, color=C_TEXT_MAIN)

# =========================================================
# 6. 核心逻辑模块绘制
# =========================================================
w_main = 2.0  
h_main = 1.0

# --- 主链 X 坐标体系 ---
x_in  = 0.5
x_enc = 3.1
x_pwr = 5.7
x_chn = 8.3
x_gen = 10.9
x_out = 13.5
y_m   = 7.0  

pt_in_l, pt_in_r, pt_in_b, pt_in_t = draw_box(x_in, y_m, w_main, h_main, "输入图像\n$\mathbf{x}$", "原始 RGB 图像", zh=True)
pt_enc_l, pt_enc_r, pt_enc_b, pt_enc_t = draw_box(x_enc, y_m, w_main, h_main, "Encoder", "语义特征提取", bg_color=C_BOX_FILL1)
pt_pwr_l, pt_pwr_r, pt_pwr_b, pt_pwr_t = draw_box(x_pwr, y_m, w_main, h_main, "功率控制", "归一化与发射功率", zh=True, bg_color=C_BOX_FILL1)
pt_chn_l, pt_chn_r, pt_chn_b, pt_chn_t = draw_box(x_chn, y_m, w_main, h_main, "AWGN 信道", "弱网噪声扰动", zh=True, bg_color=C_BOX_FILL2)
pt_gen_l, pt_gen_r, pt_gen_b, pt_gen_t = draw_box(x_gen, y_m, w_main, h_main, "Generator", "图像重建", bg_color=C_BOX_FILL1)
pt_out_l, pt_out_r, pt_out_b, pt_out_t = draw_box(x_out, y_m, w_main, h_main, "重建图像\n$\mathbf{\hat{x}}$", "飞腾端部署输出", zh=True)

# --- 训练链坐标体系 ---
y_cond = 4.4 
y_disc = 2.5 
y_loss = 0.5 

w_train = 2.0
pt_real_l, pt_real_r, pt_real_b, pt_real_t = draw_box(x_in, y_disc, w_train, h_main, "真实图像\n$\mathbf{x}$", "只在训练路径可见", zh=True)
pt_recon_l, pt_recon_r, pt_recon_b, pt_recon_t = draw_box(x_gen, y_disc, w_train, h_main, "重建图像\n$\mathbf{\hat{x}}$", "由 Generator 产生", zh=True)
pt_cond_l, pt_cond_r, pt_cond_b, pt_cond_t = draw_box(x_pwr, y_cond, w_train, h_main, "条件输入\n$\mathbf{\hat{y}}$", "信道输出作条件", zh=True, bg_color=C_BOX_FILL2)

w_disc = 2.2
x_disc = (x_pwr + w_train/2) - (w_disc/2)
pt_disc_l, pt_disc_r, pt_disc_b, pt_disc_t = draw_box(x_disc, y_disc, w_disc, h_main, "Discriminator", "判别真实/重建一致性", bg_color=C_BOX_FILL2)

# 【修改】：大幅加长 Loss 框宽度至 3.4
w_loss = 3.4
x_loss = (x_pwr + w_train/2) - (w_loss/2)
pt_loss_l, pt_loss_r, pt_loss_b, pt_loss_t = draw_box(x_loss, y_loss, w_loss, h_main, "对抗损失 + 感知损失 + MSE", 
                                                      "$L_t = \lambda L_G + \\alpha L_{MSE} + \\beta L_{LPIPS}$", zh=True)

# =========================================================
# 7. 连线与数学标注 
# =========================================================
y_label = y_m + h_main + 0.4 

draw_arrow(pt_in_r, pt_enc_l)
add_math((pt_in_r[0]+pt_enc_l[0])/2, y_label, "$1 \\times 3 \\times 256 \\times 256$")

draw_arrow(pt_enc_r, pt_pwr_l)
add_math((pt_enc_r[0]+pt_pwr_l[0])/2, y_label, "$\mathbf{y} \in \mathbb{R}^{1 \\times 32 \\times 32 \\times 32}$")

draw_arrow(pt_pwr_r, pt_chn_l)
add_math((pt_pwr_r[0]+pt_chn_l[0])/2, y_label, "$\sqrt{P}\mathbf{y}$")

draw_arrow(pt_chn_r, pt_gen_l)
add_math((pt_chn_r[0]+pt_gen_l[0])/2, y_label, "$\mathbf{\hat{y}} = \sqrt{P}\mathbf{y} + \mathbf{n}$")

draw_arrow(pt_gen_r, pt_out_l)
add_math((pt_gen_r[0]+pt_out_l[0])/2, y_label, "$1 \\times 3 \\times 256 \\times 256$")

# =========================================================
# 完美的垂直向下或水平虚线路由
# =========================================================
draw_arrow(pt_in_b, pt_real_t, style='--')
draw_arrow(pt_gen_b, pt_recon_t, style='--')

y_gap = 5.7
ax.plot([pt_chn_b[0], pt_chn_b[0]], [pt_chn_b[1], y_gap], ls='--', color=C_LINE, lw=0.75)
ax.plot([pt_chn_b[0], pt_cond_t[0]], [y_gap, y_gap], ls='--', color=C_LINE, lw=0.75)
draw_arrow((pt_cond_t[0], y_gap), pt_cond_t, style='--')

draw_arrow(pt_real_r, pt_disc_l, style='--')
draw_arrow(pt_recon_l, pt_disc_r, style='--')
draw_arrow(pt_cond_b, pt_disc_t, style='--')
draw_arrow(pt_disc_b, pt_loss_t, style='--')

# =========================================================
# 8. 无损导出与保存
# =========================================================
plt.tight_layout()
plt.savefig('fig2_1_gan_jscc_ieee_v5.png', format='png', bbox_inches='tight', dpi=600)