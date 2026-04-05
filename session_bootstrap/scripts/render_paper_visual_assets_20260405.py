#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import seaborn as sns
import scienceplots  # noqa: F401
from PIL import Image, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "session_bootstrap" / "reports" / "figures"
TIKZ_DIR = ROOT / "paper" / "tikz_figures_enhanced"


@dataclass(frozen=True)
class PdfAsset:
    source: Path
    target: Path
    scale: float = 2.8


PDF_ASSETS = [
    PdfAsset(
        source=TIKZ_DIR / "fig_system_arch_CLEAN.pdf",
        target=FIG_DIR / "paper_fig_system_arch_cn_20260405.png",
        scale=3.0,
    ),
    PdfAsset(
        source=TIKZ_DIR / "fig_gan_jscc_CLEAN.pdf",
        target=FIG_DIR / "paper_fig_gan_jscc_cn_20260405.png",
        scale=3.0,
    ),
    PdfAsset(
        source=TIKZ_DIR / "fig_system_workflow_enhanced.pdf",
        target=FIG_DIR / "paper_fig_demo_workflow_cn_20260405.png",
        scale=3.0,
    ),
    PdfAsset(
        source=TIKZ_DIR / "fig_tvm_opt_flow_enhanced.pdf",
        target=FIG_DIR / "paper_fig_tvm_opt_flow_cn_20260405.png",
        scale=3.0,
    ),
    PdfAsset(
        source=TIKZ_DIR / "fig_mnn_arch_enhanced.pdf",
        target=FIG_DIR / "paper_fig_mnn_arch_cn_20260405.png",
        scale=3.0,
    ),
]

PROJECT_TIMELINE = [
    ("03-01", "基础打通", "飞腾派 TVM 推理首次成功"),
    ("03-08~10", "运行时重建", "TVM 0.24 安全运行时与 A72 目标收敛"),
    ("03-11~13", "性能突破", "端到端 1850 ms 降至 230 ms"),
    ("03-14~15", "控制面闭环", "OpenAMP 五类消息 + 三项 FIT 收证"),
    ("03-18", "异构加速", "big.LITTLE 流水线吞吐提升 56.1%"),
    ("03-17~30", "演示集成", "current live 300/300 与界面收口"),
]

PERFORMANCE_LADDER = [
    {
        "title": "初始端到端",
        "value": "1850.0",
        "unit": "ms/image",
        "note": "旧执行链路 / 4-core Linux",
        "color": "#7A8794",
    },
    {
        "title": "TVM 主线优化后",
        "value": "230.3",
        "unit": "ms/image",
        "note": "固定形状端到端",
        "color": "#2D6A4F",
    },
    {
        "title": "big.LITTLE 流水线",
        "value": "134.6",
        "unit": "ms/image",
        "note": "4-core 吞吐主口径",
        "color": "#1B9E77",
    },
]

TVM_RESULT_SUMMARY = [
    ("端到端直通", "230.3", "ms/image", "4-core Linux / 固定形状"),
    ("异构流水线", "134.6", "ms/image", "big.LITTLE 吞吐主口径"),
    ("Throughput Uplift", "+56.1%", "", "vs serial current"),
    ("Quality", "35.66 / 0.9728", "PSNR / SSIM", "优化未牺牲重建质量"),
    ("Integrity", "300 / 300", "PNG outputs", "完整真实重建链路"),
    ("Footprint", "1.57 MiB", "artifact size", "min free mem 88,340 KB"),
]

EVIDENCE_BUNDLE_CARDS = [
    {
        "title": "总判定 / 覆盖矩阵",
        "color": "#335C81",
        "lines": [
            "summary_report.md",
            "coverage_matrix.md",
            "P0 / P1 闭环与边界总入口",
        ],
    },
    {
        "title": "live 状态收口",
        "color": "#1B9E77",
        "lines": [
            "openamp_demo_live_dualpath_status_20260317.md",
            "current 300/300 / valid instance 8115",
            "TC-002 live reconstruction 证据",
        ],
    },
    {
        "title": "FIT 安全验证",
        "color": "#D95F02",
        "lines": [
            "FIT-01 wrong SHA",
            "FIT-02 input contract",
            "FIT-03 heartbeat timeout / watchdog",
        ],
    },
    {
        "title": "性能与质量",
        "color": "#6A4C93",
        "lines": [
            "230.339 / 134.617 / 327.3 ms",
            "PSNR 35.66 / SSIM 0.9728",
            "resource profile / compare reports",
        ],
    },
    {
        "title": "演示与话术",
        "color": "#1F7A8C",
        "lines": [
            "operator runbook / rehearsal result",
            "mode boundary / defense talk track",
            "证据驱动，不做现场临时排障",
        ],
    },
]


OPENAMP_STATES = {
    "READY": (0.15, 0.72),
    "CHECKING": (0.42, 0.72),
    "RUNNING": (0.72, 0.72),
    "SAFE_STOP": (0.72, 0.30),
    "FAULT": (0.42, 0.30),
}

OPENAMP_LABELS = {
    "READY": "READY\n空闲待命",
    "CHECKING": "CHECKING\n工件/参数校验",
    "RUNNING": "RUNNING\n心跳监护激活",
    "SAFE_STOP": "SAFE_STOP\n安全停机与收敛",
    "FAULT": "FAULT\n故障留痕",
}

OPENAMP_COLORS = {
    "READY": "#1F7A8C",
    "CHECKING": "#6A4C93",
    "RUNNING": "#1B9E77",
    "SAFE_STOP": "#D95F02",
    "FAULT": "#C1121F",
}

MNN_BENCHMARK = {
    "基线\n1I/1T/FP32": 140.7,
    "正式最优\n2I/1T/FP32": 98.2,
    "低精度\n2I/1T/low": 99.1,
    "多线程\n2I/2T/FP32": 101.3,
}

FRAMEWORK_POSITIONING = [
    {
        "label": "TVM big.LITTLE",
        "value": 134.6,
        "color": "#1B9E77",
        "tag": "4-core / 固定形状 / 吞吐",
    },
    {
        "label": "TVM serial",
        "value": 230.3,
        "color": "#2D6A4F",
        "tag": "4-core / 固定形状 / 端到端",
    },
    {
        "label": "MNN dynamic",
        "value": 327.3,
        "color": "#335C81",
        "tag": "混合尺寸 / 无需预缩放 / 灵活部署",
    },
    {
        "label": "PyTorch ref",
        "value": 484.2,
        "color": "#7A8794",
        "tag": "reference baseline",
    },
]

PERF_QUALITY_POINTS = [
    {
        "label": "初始版本",
        "latency": 1850.0,
        "psnr": 34.42,
        "color": "#7A8794",
        "note": "旧执行链路 / 4-core Linux",
    },
    {
        "label": "TVM direct",
        "latency": 230.3,
        "psnr": 35.66,
        "color": "#2D6A4F",
        "note": "固定形状端到端",
    },
    {
        "label": "TVM pipeline",
        "latency": 134.6,
        "psnr": 35.66,
        "color": "#1B9E77",
        "note": "big.LITTLE 吞吐主口径",
    },
]

SNR_POINTS = np.array([1, 4, 7, 10, 13], dtype=float)
SNR_LAT_MS = np.array([228.223, 228.595, 233.509, 231.893, 234.018], dtype=float)
SNR_PSNR = np.array([29.1452, 31.8047, 34.0185, 35.6644, 36.8695], dtype=float)
SNR_SSIM = np.array([0.900039, 0.939559, 0.961243, 0.972735, 0.978757], dtype=float)

QUALITY_ROOT = ROOT / "session_bootstrap" / "tmp" / "quality_metrics_inputs_20260312" / "reference" / "reconstructions"
SNR_ROOT = ROOT / "session_bootstrap" / "tmp" / "snr_sweep_current_chunk4_20260330_152054"
RECON_SAMPLES = [
    "Places365_val_00000317_recon.png",
    "Places365_val_00000437_recon.png",
]


def choose_font() -> fm.FontProperties:
    candidates = [
        Path("/home/tianxing/.local/share/fonts/windows/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return fm.FontProperties(fname=str(path))
    return fm.FontProperties()


FONT_PROP = choose_font()


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def render_pdf(asset: PdfAsset) -> None:
    ensure_dir(asset.target)
    doc = fitz.open(asset.source)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(asset.scale, asset.scale), alpha=False)
    pix.save(asset.target)
    doc.close()


def apply_plot_style() -> None:
    plt.style.use(["science", "no-latex", "grid"])
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = FONT_PROP.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "#FFFFFF"
    plt.rcParams["axes.facecolor"] = "#FFFFFF"
    plt.rcParams["grid.color"] = "#D9E1E8"
    plt.rcParams["axes.edgecolor"] = "#AAB8C4"
    plt.rcParams["axes.labelcolor"] = "#173A5E"
    plt.rcParams["text.color"] = "#13263A"
    plt.rcParams["xtick.color"] = "#13263A"
    plt.rcParams["ytick.color"] = "#13263A"


def add_rounded_box(
    ax: plt.Axes,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
    color: str,
    text: str,
) -> None:
    box = patches.FancyBboxPatch(
        (center_x - width / 2.0, center_y - height / 2.0),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=2.0,
        edgecolor=color,
        facecolor="#F8FBFD",
    )
    ax.add_patch(box)
    ax.text(
        center_x,
        center_y,
        text,
        ha="center",
        va="center",
        fontsize=15,
        fontproperties=FONT_PROP,
        color="#13263A",
        linespacing=1.5,
        weight="bold",
    )


def add_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str,
    color: str = "#5B6D80",
    curve: float = 0.0,
    text_offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    arrow = patches.FancyArrowPatch(
        start,
        end,
        connectionstyle=f"arc3,rad={curve}",
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=2.0,
        color=color,
    )
    ax.add_patch(arrow)
    mid_x = (start[0] + end[0]) / 2.0 + text_offset[0]
    mid_y = (start[1] + end[1]) / 2.0 + text_offset[1]
    ax.text(
        mid_x,
        mid_y,
        label,
        ha="center",
        va="center",
        fontsize=12,
        fontproperties=FONT_PROP,
        color=color,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFFFFF", edgecolor="none", alpha=0.92),
    )


def render_openamp_state_machine(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)
    fig, ax = plt.subplots(figsize=(11.5, 7.2), dpi=220)
    ax.set_xlim(0.02, 0.98)
    ax.set_ylim(0.06, 0.94)
    ax.axis("off")

    for name, (x, y) in OPENAMP_STATES.items():
        add_rounded_box(ax, x, y, 0.18, 0.14, OPENAMP_COLORS[name], OPENAMP_LABELS[name])

    add_arrow(ax, (0.24, 0.72), (0.33, 0.72), "JOB_REQ", curve=0.0, text_offset=(0.0, 0.04))
    add_arrow(ax, (0.51, 0.72), (0.63, 0.72), "JOB_ACK(ALLOW)", curve=0.0, text_offset=(0.0, 0.04))
    add_arrow(ax, (0.42, 0.65), (0.23, 0.65), "JOB_ACK(DENY)\nSHA/参数非法", curve=0.15, text_offset=(0.0, 0.05))
    add_arrow(ax, (0.72, 0.65), (0.72, 0.39), "SAFE_STOP / 心跳超时", curve=0.0, text_offset=(0.08, 0.0))
    add_arrow(ax, (0.66, 0.72), (0.23, 0.74), "JOB_DONE(success)", curve=-0.16, text_offset=(0.0, 0.08))
    add_arrow(ax, (0.63, 0.30), (0.51, 0.30), "STATUS_REQ\n仅查询", curve=0.0, text_offset=(0.0, 0.05))
    add_arrow(ax, (0.42, 0.37), (0.15, 0.65), "故障记录落盘后\n回到 READY", curve=-0.25, text_offset=(-0.03, 0.02))

    ax.text(
        0.03,
        0.93,
        "OpenAMP 控制状态机与消息转移",
        fontsize=22,
        fontproperties=FONT_PROP,
        weight="bold",
        color="#173A5E",
        va="top",
    )
    ax.text(
        0.03,
        0.87,
        "RTOS 从核用五状态有限状态机约束 JOB_REQ、HEARTBEAT、SAFE_STOP 与 JOB_DONE 的合法转移。",
        fontsize=13,
        fontproperties=FONT_PROP,
        color="#5B6D80",
        va="top",
    )
    ax.text(
        0.03,
        0.11,
        "说明：SAFE_STOP 与 FAULT 在论文中都被设计成“可观测安全态”，Linux 侧可通过 STATUS_REQ 查询最后一次 fault_code 与 heartbeat 状态。",
        fontsize=11.5,
        fontproperties=FONT_PROP,
        color="#5B6D80",
        va="bottom",
    )
    fig.tight_layout(pad=1.1)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_control_message_sequence(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)
    fig, ax = plt.subplots(figsize=(12.0, 6.8), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    left_x, right_x = 0.26, 0.74
    top_y, bottom_y = 0.76, 0.12

    ax.text(left_x, 0.82, "Linux 主核 / Runner", ha="center", va="center", fontsize=15.5, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.text(right_x, 0.82, "RTOS / Bare Metal 从核", ha="center", va="center", fontsize=15.5, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.plot([left_x, left_x], [top_y, bottom_y], color="#AAB8C4", linewidth=2.0, linestyle="--")
    ax.plot([right_x, right_x], [top_y, bottom_y], color="#AAB8C4", linewidth=2.0, linestyle="--")

    steps = [
        (0.78, left_x, right_x, "STATUS_REQ", "#335C81"),
        (0.72, right_x, left_x, "STATUS_RESP\nREADY / last_fault_code", "#335C81"),
        (0.62, left_x, right_x, "JOB_REQ\nartifact_hash + param_digest", "#6A4C93"),
        (0.56, right_x, left_x, "JOB_ACK(ALLOW / DENY)", "#6A4C93"),
        (0.44, left_x, right_x, "HEARTBEAT (周期上报)", "#1B9E77"),
        (0.36, left_x, right_x, "JOB_DONE(success)", "#1B9E77"),
        (0.24, left_x, right_x, "SAFE_STOP\n或 heartbeat timeout", "#D95F02"),
        (0.18, right_x, left_x, "STATUS_RESP\nSAFE_STOP / FAULT 可观测", "#D95F02"),
    ]

    for y, x0, x1, label, color in steps:
        arrow = patches.FancyArrowPatch(
            (x0, y),
            (x1, y),
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=2.2,
            color=color,
        )
        ax.add_patch(arrow)
        ax.text(
            0.5,
            y + 0.025,
            label,
            ha="center",
            va="center",
            fontsize=12.0,
            fontproperties=FONT_PROP,
            color=color,
            bbox=dict(boxstyle="round,pad=0.24", facecolor="#FFFFFF", edgecolor="none", alpha=0.94),
        )

    ax.text(
        left_x,
        0.50,
        "ALLOW 后进入\n推理执行 + 监护",
        ha="center",
        va="center",
        fontsize=11.5,
        fontproperties=FONT_PROP,
        color="#1B9E77",
        bbox=dict(boxstyle="round,pad=0.28", facecolor="#F0F8F3", edgecolor="#1B9E77", linewidth=1.0),
    )
    ax.text(
        right_x,
        0.30,
        "若 heartbeat 丢失\n则转入 SAFE_STOP/FAULT",
        ha="center",
        va="center",
        fontsize=11.3,
        fontproperties=FONT_PROP,
        color="#D95F02",
        bbox=dict(boxstyle="round,pad=0.28", facecolor="#FFF4ED", edgecolor="#D95F02", linewidth=1.0),
    )
    ax.text(
        0.03,
        0.965,
        "控制协议与消息时序",
        fontsize=20,
        fontproperties=FONT_PROP,
        weight="bold",
        color="#173A5E",
        va="top",
    )
    ax.text(
        0.03,
        0.89,
        "STATUS_REQ/JOB_REQ/HEARTBEAT/SAFE_STOP/JOB_DONE 五类消息在 Linux 主核与 RTOS 从核之间形成可观测闭环。",
        fontsize=11.6,
        fontproperties=FONT_PROP,
        color="#5B6D80",
        va="top",
    )
    ax.text(
        0.03,
        0.06,
        "说明：大体量图像数据不经过该通道；控制面只传输作业状态、校验信息与故障码，从而保持轻载和可审计。",
        fontsize=11.2,
        fontproperties=FONT_PROP,
        color="#5B6D80",
        va="bottom",
    )
    fig.tight_layout(pad=1.0)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_project_timeline(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)
    fig, ax = plt.subplots(figsize=(12.8, 4.6), dpi=220)
    ax.set_xlim(-0.3, len(PROJECT_TIMELINE) - 0.7)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.plot([0, len(PROJECT_TIMELINE) - 1], [0.5, 0.5], color="#9FB3C8", linewidth=3.0, zorder=1)
    colors = ["#335C81", "#6A4C93", "#1B9E77", "#D95F02", "#1F7A8C", "#C1121F"]

    for idx, ((date_label, title, desc), color) in enumerate(zip(PROJECT_TIMELINE, colors)):
        y = 0.68 if idx % 2 == 0 else 0.32
        ax.plot([idx, idx], [0.5, y], color="#C6D3E0", linewidth=2.0, zorder=1)
        ax.scatter([idx], [0.5], s=170, color=color, zorder=3, edgecolors="#FFFFFF", linewidths=2.2)
        box = patches.FancyBboxPatch(
            (idx - 0.5, y - 0.12),
            1.0,
            0.22,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            linewidth=1.2,
            edgecolor="#D6E0EA",
            facecolor="#FFFFFF",
            zorder=2,
        )
        ax.add_patch(box)
        ax.text(idx - 0.42, y + 0.05, date_label, fontproperties=FONT_PROP, fontsize=10.5, color=color, weight="bold", zorder=4)
        ax.text(idx - 0.42, y + 0.0, title, fontproperties=FONT_PROP, fontsize=12.2, color="#173A5E", weight="bold", zorder=4)
        ax.text(idx - 0.42, y - 0.055, desc, fontproperties=FONT_PROP, fontsize=10.1, color="#5B6D80", zorder=4)

    fig.suptitle("项目开发时间线与关键收口节点", fontproperties=FONT_PROP, fontsize=20, color="#173A5E", y=0.98)
    fig.text(
        0.08,
        0.9,
        "从首次飞腾端推理成功到 OpenAMP 控制面闭环、big.LITTLE 提速与演示集成，项目在 2026 年 3 月完成了由点到面的系统收口。",
        ha="left",
        va="center",
        fontsize=11.8,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )
    fig.subplots_adjust(top=0.82, bottom=0.1, left=0.04, right=0.98)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_mnn_benchmark(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)
    labels = list(MNN_BENCHMARK.keys())
    values = list(MNN_BENCHMARK.values())
    palette = ["#7A8794", "#1B9E77", "#D95F02", "#6A4C93"]

    fig, ax = plt.subplots(figsize=(10.8, 6.2), dpi=220)
    bars = ax.bar(labels, values, color=palette, width=0.62)
    fig.suptitle("MNN 动态尺寸路线关键配置对比", fontproperties=FONT_PROP, fontsize=21, color="#173A5E", y=0.98)
    fig.text(
        0.08,
        0.915,
        "300 张不同尺寸图像，单位为总耗时（秒）。当前正式最优仍为 2 interpreters + 1 thread/session + FP32(normal)。",
        ha="left",
        va="center",
        fontsize=12.2,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )
    ax.set_ylabel("300 张总耗时（s）", fontproperties=FONT_PROP, fontsize=13)
    ax.set_ylim(0, 165)
    for tick in ax.get_xticklabels():
        tick.set_fontproperties(FONT_PROP)
        tick.set_fontsize(12)
    for tick in ax.get_yticklabels():
        tick.set_fontproperties(FONT_PROP)
        tick.set_fontsize(11)

    best_value = min(values)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            value + 2.6,
            f"{value:.1f}s",
            ha="center",
            va="bottom",
            fontsize=12,
            fontproperties=FONT_PROP,
            color="#13263A",
            weight="bold",
        )
        if value == best_value:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                value / 2.0,
                "正式最优",
                ha="center",
                va="center",
                fontsize=12.5,
                fontproperties=FONT_PROP,
                color="#FFFFFF",
                weight="bold",
            )

    baseline = MNN_BENCHMARK["基线\n1I/1T/FP32"]
    best = MNN_BENCHMARK["正式最优\n2I/1T/FP32"]
    uplift = baseline / best
    ax.text(
        0.98,
        0.94,
        f"基线→正式最优：{uplift:.2f}x",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=13,
        fontproperties=FONT_PROP,
        color="#1B9E77",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F0F8F3", edgecolor="#1B9E77", linewidth=1.2),
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.subplots_adjust(top=0.88, bottom=0.16, left=0.08, right=0.98)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_performance_ladder(target: Path) -> None:
    ensure_dir(target)
    from PIL import ImageDraw, ImageFont

    canvas_w, canvas_h = 2300, 1180
    bg = Image.new("RGB", (canvas_w, canvas_h), "#F5F8FC")
    draw = ImageDraw.Draw(bg)

    def load_font_local(size: int, bold: bool = False):
        candidates = [
            Path("/home/tianxing/.local/share/fonts/windows/simhei.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        for p in candidates:
            if p.is_file():
                return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    f_title = load_font_local(60, bold=True)
    f_sub = load_font_local(26)
    f_card_title = load_font_local(32, bold=True)
    f_value = load_font_local(58, bold=True)
    f_unit = load_font_local(24)
    f_note = load_font_local(24)
    f_badge = load_font_local(24, bold=True)

    for y in range(200):
        alpha = int(255 * (1 - y / 200) * 0.16)
        band = Image.new("RGBA", (canvas_w, 1), (24, 65, 118, alpha))
        bg.paste(band, (0, y), band)

    draw.text((90, 48), "系统关键性能跃迁", fill="#173A5E", font=f_title)
    draw.text(
        (90, 128),
        "主线结果并不是单点 benchmark，而是从旧端到端链路到 TVM 主线再到 big.LITTLE 流水线的连续收口。MNN 动态尺寸路线作为旁路负责混合尺寸部署。",
        fill="#5B6D80",
        font=f_sub,
    )

    card_w, card_h = 560, 420
    top_y = 260
    xs = [90, 735, 1380]
    arrow_texts = ["8.0x 更快", "1.71x 更快"]

    for idx, item in enumerate(PERFORMANCE_LADDER):
        x = xs[idx]
        shadow = Image.new("RGBA", (card_w + 28, card_h + 28), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((14, 14, card_w + 14, card_h + 14), radius=30, fill=(12, 23, 38, 58))
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        bg.paste(shadow, (x - 8, top_y - 4), shadow)

        card = Image.new("RGB", (card_w, card_h), "#FFFFFF")
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=30, fill="#FFFFFF", outline="#D4DEEA", width=2)
        cd.rounded_rectangle((28, 24, 180, 72), radius=24, fill=item["color"])
        cd.text((52, 36), "主结果", fill="#FFFFFF", font=f_badge)
        cd.text((28, 110), item["title"], fill="#173A5E", font=f_card_title)
        cd.text((28, 196), item["value"], fill=item["color"], font=f_value)
        cd.text((300, 220), item["unit"], fill="#5B6D80", font=f_unit)
        cd.rounded_rectangle((28, 288, card_w - 28, 368), radius=22, fill="#F3F8FC", outline="#E2EAF2", width=1)
        cd.text((48, 315), item["note"], fill="#5B6D80", font=f_note)
        bg.paste(card, (x, top_y))

        if idx < len(PERFORMANCE_LADDER) - 1:
            arrow_x0 = x + card_w + 24
            arrow_x1 = xs[idx + 1] - 28
            arrow_y = top_y + 195
            draw.line((arrow_x0, arrow_y, arrow_x1, arrow_y), fill="#6A7F94", width=7)
            draw.polygon([(arrow_x1, arrow_y), (arrow_x1 - 26, arrow_y - 14), (arrow_x1 - 26, arrow_y + 14)], fill="#6A7F94")
            text_w = draw.textbbox((0, 0), arrow_texts[idx], font=f_badge)[2]
            draw.rounded_rectangle((arrow_x0 + 24, arrow_y - 54, arrow_x0 + 24 + text_w + 34, arrow_y - 14), radius=20, fill="#EAF2F8")
            draw.text((arrow_x0 + 41, arrow_y - 47), arrow_texts[idx], fill="#42586E", font=f_badge)

    # MNN side panel
    side_x, side_y, side_w, side_h = 1720, 720, 490, 320
    shadow = Image.new("RGBA", (side_w + 28, side_h + 28), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((14, 14, side_w + 14, side_h + 14), radius=28, fill=(12, 23, 38, 52))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    bg.paste(shadow, (side_x - 8, side_y - 4), shadow)
    card = Image.new("RGB", (side_w, side_h), "#FFFFFF")
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, side_w - 1, side_h - 1), radius=28, fill="#FFFFFF", outline="#D4DEEA", width=2)
    cd.rounded_rectangle((24, 22, 196, 68), radius=22, fill="#335C81")
    cd.text((48, 34), "动态尺寸旁路", fill="#FFFFFF", font=f_badge)
    cd.text((24, 96), "MNN dynamic", fill="#173A5E", font=f_card_title)
    cd.text((24, 164), "327.3", fill="#335C81", font=f_value)
    cd.text((250, 188), "ms/image", fill="#5B6D80", font=f_unit)
    cd.text((24, 248), "混合尺寸 / 无需预缩放 / 300 张 98.2 s", fill="#5B6D80", font=f_note)
    bg.paste(card, (side_x, side_y))

    footer_y = 1068
    draw.rounded_rectangle((90, footer_y - 8, canvas_w - 90, canvas_h - 50), radius=24, fill="#EAF2F8", outline="#D3DFEA", width=2)
    draw.text((118, footer_y + 8), "读图方式：固定形状主线看左到右三张卡；混合尺寸部署看右下角 MNN 旁路。", fill="#42586E", font=f_sub)
    bg.save(target)


def render_tvm_result_summary(target: Path) -> None:
    ensure_dir(target)
    from PIL import ImageDraw, ImageFont

    canvas_w, canvas_h = 2260, 1240
    bg = Image.new("RGB", (canvas_w, canvas_h), "#F5F8FC")
    draw = ImageDraw.Draw(bg)

    def load_font_local(size: int, bold: bool = False):
        candidates = [
            Path("/home/tianxing/.local/share/fonts/windows/simhei.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        for p in candidates:
            if p.is_file():
                return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    f_title = load_font_local(58, bold=True)
    f_sub = load_font_local(26)
    f_label = load_font_local(26, bold=True)
    f_value = load_font_local(46, bold=True)
    f_unit = load_font_local(22)
    f_note = load_font_local(22)
    f_badge = load_font_local(24, bold=True)

    for y in range(190):
        alpha = int(255 * (1 - y / 190) * 0.15)
        band = Image.new("RGBA", (canvas_w, 1), (24, 65, 118, alpha))
        bg.paste(band, (0, y), band)

    draw.text((86, 44), "TVM 主线结果总览", fill="#173A5E", font=f_title)
    draw.text(
        (86, 120),
        "该页汇总 4-core Linux performance mode 下最应被引用的 TVM 主线结论：时间、吞吐、质量、完整性与资源占用。",
        fill="#5B6D80",
        font=f_sub,
    )

    card_w, card_h = 650, 240
    x_positions = [86, 804, 1522]
    y_positions = [250, 540]
    accents = ["#2D6A4F", "#1B9E77", "#335C81", "#D95F02", "#6A4C93", "#1F7A8C"]

    for idx, ((label, value, unit, note), accent) in enumerate(zip(TVM_RESULT_SUMMARY, accents)):
        row, col = divmod(idx, 3)
        x = x_positions[col]
        y = y_positions[row]
        shadow = Image.new("RGBA", (card_w + 28, card_h + 28), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((14, 14, card_w + 14, card_h + 14), radius=28, fill=(12, 23, 38, 54))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        bg.paste(shadow, (x - 8, y - 4), shadow)

        card = Image.new("RGB", (card_w, card_h), "#FFFFFF")
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=28, fill="#FFFFFF", outline="#D4DEEA", width=2)
        cd.rounded_rectangle((24, 22, 170, 66), radius=22, fill=accent)
        cd.text((48, 34), "TVM 主线", fill="#FFFFFF", font=f_badge)
        cd.text((24, 92), label, fill="#173A5E", font=f_label)
        cd.text((24, 146), value, fill=accent, font=f_value)
        if unit:
            cd.text((360, 164), unit, fill="#5B6D80", font=f_unit)
        cd.text((24, 202), note, fill="#5B6D80", font=f_note)
        bg.paste(card, (x, y))

    footer_y = 960
    draw.rounded_rectangle((86, footer_y, canvas_w - 86, 1145), radius=26, fill="#EAF2F8", outline="#D3DFEA", width=2)
    draw.text((116, footer_y + 26), "引用边界", fill="#173A5E", font=f_label)
    draw.text(
        (116, footer_y + 84),
        "本图只汇总 4-core Linux performance mode 的 TVM 主线结论。OpenAMP 三核演示模式的公平比较、控制面闭环和 FIT 结果应继续引用第 3 章与第 4.1.3 节对应证据，不与本图混写。",
        fill="#42586E",
        font=f_sub,
    )
    bg.save(target)


def render_evidence_bundle_map(target: Path) -> None:
    ensure_dir(target)
    from PIL import ImageDraw, ImageFont

    canvas_w, canvas_h = 2300, 1360
    bg = Image.new("RGB", (canvas_w, canvas_h), "#F5F8FC")
    draw = ImageDraw.Draw(bg)

    def load_font_local(size: int, bold: bool = False):
        candidates = [
            Path("/home/tianxing/.local/share/fonts/windows/simhei.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        for p in candidates:
            if p.is_file():
                return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    f_title = load_font_local(56, bold=True)
    f_sub = load_font_local(24)
    f_center = load_font_local(34, bold=True)
    f_card_title = load_font_local(28, bold=True)
    f_card_body = load_font_local(22)
    f_badge = load_font_local(23, bold=True)

    for y in range(190):
        alpha = int(255 * (1 - y / 190) * 0.15)
        band = Image.new("RGBA", (canvas_w, 1), (24, 65, 118, alpha))
        bg.paste(band, (0, y), band)

    draw.text((86, 46), "答辩证据包结构图", fill="#173A5E", font=f_title)
    draw.text(
        (86, 118),
        "把最重要的面向评审材料按“总判定、live 状态、安全验证、性能质量、演示话术”五类组织，避免现场翻日志找文件。",
        fill="#5B6D80",
        font=f_sub,
    )

    center_box = (860, 470, 1440, 710)
    draw.rounded_rectangle(center_box, radius=38, fill="#0F2035", outline="#1F3A5A", width=2)
    draw.text((950, 525), "Judge-facing", fill="#86C5FF", font=f_badge)
    draw.text((950, 570), "Evidence Bundle", fill="#FFFFFF", font=f_center)
    draw.text((950, 628), "文档优先 / 证据驱动 /\n操作员在环", fill="#DCE7F3", font=f_sub, spacing=10)

    card_positions = [
        (120, 250),
        (1580, 250),
        (120, 860),
        (860, 860),
        (1580, 860),
    ]

    for (card, (x, y)) in zip(EVIDENCE_BUNDLE_CARDS, card_positions):
        w, h = 560, 280
        shadow = Image.new("RGBA", (w + 28, h + 28), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((14, 14, w + 14, h + 14), radius=28, fill=(12, 23, 38, 54))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        bg.paste(shadow, (x - 8, y - 4), shadow)

        card_img = Image.new("RGB", (w, h), "#FFFFFF")
        cd = ImageDraw.Draw(card_img)
        cd.rounded_rectangle((0, 0, w - 1, h - 1), radius=28, fill="#FFFFFF", outline="#D4DEEA", width=2)
        cd.rounded_rectangle((24, 22, 196, 68), radius=22, fill=card["color"])
        cd.text((48, 34), "证据入口", fill="#FFFFFF", font=f_badge)
        cd.text((24, 102), card["title"], fill="#173A5E", font=f_card_title)
        for idx, line in enumerate(card["lines"]):
            cd.text((24, 154 + idx * 34), line, fill="#5B6D80", font=f_card_body)
        bg.paste(card_img, (x, y))

        cx = x + w / 2
        cy = y + (0 if y > center_box[1] else h)
        target_x = (center_box[0] + center_box[2]) / 2
        target_y = center_box[1] if y > center_box[1] else center_box[3]
        draw.line((cx, cy, target_x, target_y), fill="#B7C7D8", width=5)

    footer_y = 1240
    draw.rounded_rectangle((86, footer_y - 10, canvas_w - 86, canvas_h - 54), radius=24, fill="#EAF2F8", outline="#D3DFEA", width=2)
    draw.text((116, footer_y + 4), "用途：评委追问时先选卡片，再打开对应文档；不把现场临时排障当作正式证据。", fill="#42586E", font=f_sub)
    bg.save(target)


def render_framework_positioning(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)

    labels = [item["label"] for item in FRAMEWORK_POSITIONING][::-1]
    values = [item["value"] for item in FRAMEWORK_POSITIONING][::-1]
    colors = [item["color"] for item in FRAMEWORK_POSITIONING][::-1]
    tags = [item["tag"] for item in FRAMEWORK_POSITIONING][::-1]

    fig, ax = plt.subplots(figsize=(12.2, 6.6), dpi=220)
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=colors, height=0.62)

    fig.suptitle("双引擎部署定位与端侧性能关系", fontproperties=FONT_PROP, fontsize=21, color="#173A5E", y=0.985)
    fig.text(
        0.08,
        0.92,
        "TVM 负责固定形状极致性能，MNN 负责动态尺寸灵活部署；OpenAMP 演示模式的控制/安全结论不与本图 latency 混写。",
        ha="left",
        va="center",
        fontsize=12.2,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    ax.set_xlabel("端到端时间（ms/image，越低越好）", fontproperties=FONT_PROP, fontsize=12.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 560)
    for tick in ax.get_xticklabels():
        tick.set_fontproperties(FONT_PROP)
        tick.set_fontsize(11)
    for tick in ax.get_yticklabels():
        tick.set_fontproperties(FONT_PROP)
        tick.set_fontsize(13)

    for bar, value, tag in zip(bars, values, tags):
        y_mid = bar.get_y() + bar.get_height() / 2.0
        ax.text(
            max(value - 8, 18),
            y_mid,
            f"{value:.1f} ms",
            ha="right",
            va="center",
            fontsize=12.5,
            fontproperties=FONT_PROP,
            color="#FFFFFF",
            weight="bold",
        )
        tag_x = value + 10
        tag_ha = "left"
        if tag_x > 545:
            tag_x = 545
            tag_ha = "right"
        ax.text(
            tag_x,
            y_mid,
            tag,
            ha=tag_ha,
            va="center",
            fontsize=10.8,
            fontproperties=FONT_PROP,
            color="#FFFFFF",
            bbox=dict(boxstyle="round,pad=0.28", facecolor=bar.get_facecolor(), edgecolor="none"),
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.text(
        0.08,
        0.08,
        "注：MNN 值来自 300 张混合尺寸真机 benchmark；TVM 值来自 256×256 固定形状性能主口径。",
        ha="left",
        va="center",
        fontsize=10.8,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )
    fig.text(
        0.97,
        0.08,
        "结论：固定形状优先 TVM；动态尺寸优先 MNN。",
        ha="right",
        va="center",
        fontsize=12.3,
        fontproperties=FONT_PROP,
        color="#1B9E77",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F0F8F3", edgecolor="#1B9E77", linewidth=1.1),
    )
    fig.subplots_adjust(top=0.84, bottom=0.2, left=0.17, right=0.97)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_perf_quality_tradeoff(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)

    fig = plt.figure(figsize=(12.6, 6.4), dpi=220)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 0.95])
    ax = fig.add_subplot(gs[0, 0])
    panel = fig.add_subplot(gs[0, 1])
    panel.axis("off")

    x_vals = [item["latency"] for item in PERF_QUALITY_POINTS]
    y_vals = [item["psnr"] for item in PERF_QUALITY_POINTS]
    ax.plot(x_vals, y_vals, linestyle="--", linewidth=2.0, color="#A9B8C8", zorder=1)

    for item in PERF_QUALITY_POINTS:
        ax.scatter(
            item["latency"],
            item["psnr"],
            s=260,
            color=item["color"],
            edgecolor="white",
            linewidth=1.8,
            zorder=3,
        )
        offset = (10, 12)
        if item["label"] == "初始版本":
            offset = (-70, -5)
        elif item["label"] == "TVM pipeline":
            offset = (10, -28)
        ax.annotate(
            f"{item['label']}\n{item['latency']:.1f} ms / {item['psnr']:.2f} dB",
            xy=(item["latency"], item["psnr"]),
            xytext=offset,
            textcoords="offset points",
            ha="left" if offset[0] >= 0 else "right",
            va="bottom",
            fontsize=10.8,
            fontproperties=FONT_PROP,
            color="#173A5E",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#D4DFEA", linewidth=1.0, alpha=0.95),
        )

    ax.annotate(
        "",
        xy=(230.3, 35.66),
        xytext=(1850.0, 34.42),
        arrowprops=dict(arrowstyle="-|>", lw=2.0, color="#2D6A4F"),
    )
    ax.annotate(
        "",
        xy=(134.6, 35.66),
        xytext=(230.3, 35.66),
        arrowprops=dict(arrowstyle="-|>", lw=2.0, color="#1B9E77"),
    )

    ax.text(
        0.03,
        0.95,
        "更快且未牺牲质量",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=12.2,
        fontproperties=FONT_PROP,
        color="#1B9E77",
        bbox=dict(boxstyle="round,pad=0.32", facecolor="#EEF8F2", edgecolor="#1B9E77", linewidth=1.0),
    )
    ax.text(
        0.03,
        0.07,
        "左图只比较同口径 TVM 主线\nMNN 不与该 PSNR 散点直接混写",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.0,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    ax.set_xscale("log")
    ax.set_xlim(110, 2400)
    ax.set_ylim(34.1, 36.1)
    ax.set_xticks([125, 250, 500, 1000, 2000])
    ax.set_xticklabels(["125", "250", "500", "1000", "2000"])
    ax.set_xlabel("端到端时间（ms/image，对数坐标，越低越好）", fontproperties=FONT_PROP, fontsize=12.5)
    ax.set_ylabel("PSNR (dB，越高越好)", fontproperties=FONT_PROP, fontsize=12.5)
    ax.grid(alpha=0.18, linestyle="--")
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontproperties(FONT_PROP)
        tick.set_fontsize(10.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle("性能-质量-部署灵活性权衡图", fontproperties=FONT_PROP, fontsize=21, color="#173A5E", y=0.985)
    fig.text(
        0.08,
        0.92,
        "TVM 主线证明“更快不等于更差”；MNN 作为混合尺寸部署旁路保留，不与左图的同尺寸质量口径混写。",
        ha="left",
        va="center",
        fontsize=12.0,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    def add_card(x: float, y: float, w: float, h: float, title: str, color: str, lines: list[str]) -> None:
        rect = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="white",
            edgecolor="#D4DFEA",
            linewidth=1.1,
        )
        panel.add_patch(rect)
        tag = patches.FancyBboxPatch(
            (x + 0.03, y + h - 0.12),
            0.24,
            0.08,
            boxstyle="round,pad=0.01,rounding_size=0.04",
            facecolor=color,
            edgecolor="none",
        )
        panel.add_patch(tag)
        panel.text(x + 0.15, y + h - 0.08, "部署卡片", ha="center", va="center", fontsize=10.5, fontproperties=FONT_PROP, color="white", weight="bold")
        panel.text(x + 0.03, y + h - 0.14, title, ha="left", va="top", fontsize=14.2, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
        for idx, line in enumerate(lines):
            panel.text(
                x + 0.03,
                y + h - 0.21 - idx * 0.07,
                line,
                ha="left",
                va="top",
                fontsize=10.8,
                fontproperties=FONT_PROP,
                color="#5B6D80",
            )

    add_card(
        0.04,
        0.56,
        0.9,
        0.29,
        "固定形状 TVM 主线",
        "#2D6A4F",
        [
            "230.3 ms/image 端到端 / 134.6 ms/image big.LITTLE",
            "PSNR 35.66 / SSIM 0.9728 / 性能主口径",
        ],
    )
    add_card(
        0.04,
        0.22,
        0.9,
        0.29,
        "动态尺寸 MNN 旁路",
        "#335C81",
        [
            "327.3 ms/image / 300 张混合尺寸",
            "无需预缩放 / 保留部署灵活性",
        ],
    )
    panel.text(
        0.04,
        0.10,
        "结论：固定形状优先追 TVM 主线；动态尺寸场景保留 MNN。",
        ha="left",
        va="center",
        fontsize=11.6,
        fontproperties=FONT_PROP,
        color="#173A5E",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F7FAFD", edgecolor="#C8D6E5", linewidth=1.0),
    )
    panel.text(
        0.04,
        0.04,
        "注：MNN 保留部署灵活性，不与左图的同尺寸 PSNR 散点直接混写。",
        ha="left",
        va="center",
        fontsize=9.8,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    fig.subplots_adjust(top=0.84, bottom=0.14, left=0.08, right=0.97, wspace=0.12)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_semantic_vs_traditional(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)

    fig, ax = plt.subplots(figsize=(12.6, 6.3), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.suptitle("传统压缩与语义通信的弱网对比", fontproperties=FONT_PROP, fontsize=21, color="#173A5E", y=0.985)
    fig.text(
        0.08,
        0.92,
        "图中同时强调“传什么”和“弱网下会怎样”：传统方案传像素信息，语义通信传 latent 语义特征。",
        ha="left",
        va="center",
        fontsize=11.9,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    left = patches.FancyBboxPatch(
        (0.05, 0.30),
        0.38,
        0.50,
        boxstyle="round,pad=0.018,rounding_size=0.03",
        facecolor="#FFF9F2",
        edgecolor="#F2C38B",
        linewidth=1.2,
    )
    right = patches.FancyBboxPatch(
        (0.57, 0.30),
        0.38,
        0.50,
        boxstyle="round,pad=0.018,rounding_size=0.03",
        facecolor="#F3FBF7",
        edgecolor="#9BCBB3",
        linewidth=1.2,
    )
    ax.add_patch(left)
    ax.add_patch(right)

    def add_header(x: float, y: float, text: str, color: str) -> None:
        chip = patches.FancyBboxPatch(
            (x, y),
            0.18,
            0.07,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            facecolor=color,
            edgecolor="none",
        )
        ax.add_patch(chip)
        ax.text(x + 0.09, y + 0.035, text, ha="center", va="center", fontsize=11.4, fontproperties=FONT_PROP, color="white", weight="bold")

    add_header(0.08, 0.75, "传统压缩", "#D95F02")
    add_header(0.60, 0.75, "语义通信", "#1B9E77")

    ax.text(0.08, 0.68, "传输对象：像素级信息", ha="left", va="center", fontsize=16, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.text(0.60, 0.68, "传输对象：latent 语义特征", ha="left", va="center", fontsize=16, fontproperties=FONT_PROP, color="#173A5E", weight="bold")

    left_lines = [
        "JPEG / H.265 仍围绕像素保真展开",
        "链路变差时需要更强的冗余与纠错开销",
        "极低 SNR 下容易出现明显失真甚至不可用",
    ]
    right_lines = [
        "Encoder 先提取紧凑语义表征再入信道",
        "本系统 32×32×32 latent 约 128 KB (FP32)",
        "文献[6]：SNR=1 dB 时 GAN-based JSCC 仍可达 29 dB+",
    ]
    for idx, line in enumerate(left_lines):
        ax.text(0.09, 0.60 - idx * 0.10, f"- {line}", ha="left", va="center", fontsize=11.5, fontproperties=FONT_PROP, color="#5B6D80")
    for idx, line in enumerate(right_lines):
        ax.text(0.61, 0.60 - idx * 0.10, f"- {line}", ha="left", va="center", fontsize=11.5, fontproperties=FONT_PROP, color="#5B6D80")

    arrow = patches.FancyArrowPatch(
        (0.45, 0.56),
        (0.55, 0.56),
        arrowstyle="simple",
        mutation_scale=28,
        linewidth=0,
        color="#A9B8C8",
        alpha=0.9,
    )
    ax.add_patch(arrow)
    ax.text(0.50, 0.61, "弱网巡检场景", ha="center", va="center", fontsize=12.0, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.text(0.50, 0.52, "更关注“能否传回有效语义”", ha="center", va="center", fontsize=10.6, fontproperties=FONT_PROP, color="#5B6D80")

    ax.text(0.08, 0.22, "本系统输入与 latent 大小对照", ha="left", va="center", fontsize=13.6, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.text(0.08, 0.16, "256×256 RGB 原图", ha="left", va="center", fontsize=11.4, fontproperties=FONT_PROP, color="#5B6D80")
    ax.text(0.08, 0.11, "Encoder latent", ha="left", va="center", fontsize=11.4, fontproperties=FONT_PROP, color="#5B6D80")

    base_x = 0.28
    max_w = 0.48
    raw_w = max_w
    latent_w = max_w * (128.0 / 192.0)
    raw_bar = patches.FancyBboxPatch((base_x, 0.145), raw_w, 0.035, boxstyle="round,pad=0.005,rounding_size=0.015", facecolor="#DADFE6", edgecolor="none")
    latent_bar = patches.FancyBboxPatch((base_x, 0.095), latent_w, 0.035, boxstyle="round,pad=0.005,rounding_size=0.015", facecolor="#1B9E77", edgecolor="none")
    ax.add_patch(raw_bar)
    ax.add_patch(latent_bar)
    ax.text(base_x + raw_w - 0.01, 0.162, "≈192 KB", ha="right", va="center", fontsize=10.8, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
    ax.text(base_x + latent_w - 0.01, 0.112, "≈128 KB", ha="right", va="center", fontsize=10.8, fontproperties=FONT_PROP, color="white", weight="bold")

    ax.text(
        0.08,
        0.04,
        "注：大小对照来自本系统 256×256 RGB 输入与 32×32×32 latent（FP32）；弱网鲁棒性结论引自文献[6]，用于说明语义通信在极端弱网中的工程优势。",
        ha="left",
        va="center",
        fontsize=9.9,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_system_closure_overview(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)

    fig, ax = plt.subplots(figsize=(12.8, 7.0), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.suptitle("弱网安全语义回传系统闭环总览图", fontproperties=FONT_PROP, fontsize=22, color="#173A5E", y=0.985)
    fig.text(
        0.08,
        0.925,
        "把数据面、控制面、性能主口径和答辩证据压成同一页，方便评审快速理解“传得回、跑得快、用得稳”的闭环。",
        ha="left",
        va="center",
        fontsize=12.0,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    center = patches.FancyBboxPatch(
        (0.34, 0.38),
        0.32,
        0.24,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor="#13263F",
        edgecolor="none",
    )
    ax.add_patch(center)
    ax.text(0.50, 0.56, "系统闭环", ha="center", va="center", fontsize=18.5, fontproperties=FONT_PROP, color="white", weight="bold")
    ax.text(0.50, 0.49, "传得回 / 跑得快 / 用得稳", ha="center", va="center", fontsize=13.5, fontproperties=FONT_PROP, color="#D8E6F3")
    ax.text(0.50, 0.42, "数据面 + 控制面 + 证据驱动", ha="center", va="center", fontsize=11.0, fontproperties=FONT_PROP, color="#A9B8C8")

    def add_card(x: float, y: float, w: float, h: float, title: str, color: str, lines: list[str]) -> tuple[float, float]:
        rect = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="white",
            edgecolor="#D4DFEA",
            linewidth=1.2,
        )
        ax.add_patch(rect)
        tag = patches.FancyBboxPatch(
            (x + 0.02, y + h - 0.07),
            0.14,
            0.055,
            boxstyle="round,pad=0.01,rounding_size=0.03",
            facecolor=color,
            edgecolor="none",
        )
        ax.add_patch(tag)
        ax.text(x + 0.09, y + h - 0.043, "模块", ha="center", va="center", fontsize=10.3, fontproperties=FONT_PROP, color="white", weight="bold")
        ax.text(x + 0.02, y + h - 0.11, title, ha="left", va="top", fontsize=15.0, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
        for idx, line in enumerate(lines):
            ax.text(x + 0.02, y + h - 0.20 - idx * 0.065, line, ha="left", va="top", fontsize=10.8, fontproperties=FONT_PROP, color="#5B6D80")
        return (x + w / 2.0, y + h / 2.0)

    add_card(
        0.05,
        0.64,
        0.25,
        0.21,
        "数据面",
        "#1B9E77",
        [
            "Host Encoder -> latent -> 飞腾 Linux 主核",
            "TVM 固定形状 / MNN 动态尺寸双引擎",
            "300 / 300 真机重建与 PNG 落盘",
        ],
    )
    add_card(
        0.70,
        0.64,
        0.25,
        0.21,
        "控制面",
        "#D95F02",
        [
            "RTOS 从核 + OpenAMP 五类消息",
            "READY/CHECKING/RUNNING/SAFE_STOP/FAULT",
            "3 项 FIT 真机通过，SAFE_STOP 可观测收敛",
        ],
    )
    add_card(
        0.05,
        0.12,
        0.25,
        0.23,
        "性能结论",
        "#2D6A4F",
        [
            "TVM direct 230.3 ms/image",
            "big.LITTLE 134.6 ms/image / +56.1%",
            "MNN dynamic 327.3 ms/image",
        ],
    )
    add_card(
        0.70,
        0.12,
        0.25,
        0.23,
        "答辩入口",
        "#335C81",
        [
            "dashboard + evidence bundle + compare drawer",
            "面向评审的五类材料入口",
            "操作员在环，不靠现场翻日志",
        ],
    )

    connectors = [
        ((0.30, 0.74), (0.34, 0.56)),
        ((0.70, 0.74), (0.66, 0.56)),
        ((0.30, 0.24), (0.34, 0.44)),
        ((0.70, 0.24), (0.66, 0.44)),
    ]
    for start, end in connectors:
        arrow = patches.FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=1.8,
            color="#B7C7D8",
        )
        ax.add_patch(arrow)

    ax.text(0.08, 0.05, "结论：弱网语义回传不只是一个更快的模型，而是一套可运行、可控制、可证明的系统。", ha="left", va="center", fontsize=11.6, fontproperties=FONT_PROP, color="#173A5E")

    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_cover_summary(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)

    fig, ax = plt.subplots(figsize=(13.2, 7.2), dpi=220)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    bg = patches.FancyBboxPatch(
        (0.02, 0.04),
        0.96,
        0.90,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor="#F7FAFD",
        edgecolor="#D8E6F3",
        linewidth=1.0,
    )
    ax.add_patch(bg)

    fig.suptitle("飞腾多核异构安全语义回传系统摘要图", fontproperties=FONT_PROP, fontsize=23, color="#173A5E", y=0.985)
    fig.text(
        0.08,
        0.925,
        "一张图同时概括链路、角色分工和关键结果，适合作为论文首页与答辩首页的摘要图。",
        ha="left",
        va="center",
        fontsize=12.1,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )

    step_specs = [
        (0.07, "弱网图像输入", "#335C81", ["原始图像", "巡检/应急场景"]),
        (0.29, "Host Encoder + AWGN", "#6A4C93", ["语义编码", "latent 扰动模拟"]),
        (0.51, "飞腾 Linux + RTOS", "#1B9E77", ["TVM/MNN 重建", "OpenAMP 安全控制"]),
        (0.73, "Dashboard / Evidence", "#2D6A4F", ["重建显示与存储", "面向评审的证据入口"]),
    ]

    centers = []
    for x, title, color, lines in step_specs:
        rect = patches.FancyBboxPatch(
            (x, 0.58),
            0.18,
            0.18,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="white",
            edgecolor="#D4DFEA",
            linewidth=1.2,
        )
        ax.add_patch(rect)
        chip = patches.FancyBboxPatch(
            (x + 0.02, 0.70),
            0.14,
            0.045,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            facecolor=color,
            edgecolor="none",
        )
        ax.add_patch(chip)
        ax.text(x + 0.09, 0.722, "阶段", ha="center", va="center", fontsize=10.0, fontproperties=FONT_PROP, color="white", weight="bold")
        ax.text(x + 0.02, 0.66, title, ha="left", va="top", fontsize=14.0, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
        for idx, line in enumerate(lines):
            ax.text(x + 0.02, 0.60 - idx * 0.05, line, ha="left", va="top", fontsize=10.6, fontproperties=FONT_PROP, color="#5B6D80")
        centers.append((x + 0.09, 0.67))

    for start, end in zip(centers[:-1], centers[1:]):
        arrow = patches.FancyArrowPatch(
            (start[0] + 0.10, start[1]),
            (end[0] - 0.10, end[1]),
            arrowstyle="simple",
            mutation_scale=22,
            linewidth=0,
            color="#B7C7D8",
            alpha=0.95,
        )
        ax.add_patch(arrow)

    metric_specs = [
        (0.07, "性能主口径", "#1B9E77", "230.3 / 134.6 ms", "TVM 端到端 / big.LITTLE"),
        (0.38, "安全闭环", "#D95F02", "5 类消息 + 3 FIT", "SAFE_STOP 可观测收敛"),
        (0.69, "动态部署", "#335C81", "327.3 ms/image", "MNN 混合尺寸 / 无需预缩放"),
    ]
    for x, title, color, value, note in metric_specs:
        card = patches.FancyBboxPatch(
            (x, 0.24),
            0.24,
            0.20,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="white",
            edgecolor="#D4DFEA",
            linewidth=1.2,
        )
        ax.add_patch(card)
        ax.text(x + 0.02, 0.40, title, ha="left", va="top", fontsize=13.5, fontproperties=FONT_PROP, color=color, weight="bold")
        ax.text(x + 0.02, 0.335, value, ha="left", va="top", fontsize=18.0, fontproperties=FONT_PROP, color="#173A5E", weight="bold")
        ax.text(x + 0.02, 0.275, note, ha="left", va="top", fontsize=10.6, fontproperties=FONT_PROP, color="#5B6D80")

    ribbon = patches.FancyBboxPatch(
        (0.18, 0.10),
        0.64,
        0.07,
        boxstyle="round,pad=0.012,rounding_size=0.03",
        facecolor="#13263F",
        edgecolor="none",
    )
    ax.add_patch(ribbon)
    ax.text(0.50, 0.135, "传得回  |  跑得快  |  用得稳", ha="center", va="center", fontsize=16.0, fontproperties=FONT_PROP, color="white", weight="bold")

    ax.text(0.07, 0.05, "注：性能主口径与混合尺寸结果分别对应固定形状 TVM 与动态尺寸 MNN；控制面结论来自 3 核 Linux + RTOS 演示模式。", ha="left", va="center", fontsize=10.0, fontproperties=FONT_PROP, color="#5B6D80")

    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def render_snr_curve(target: Path) -> None:
    apply_plot_style()
    ensure_dir(target)
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9), dpi=220)

    ax0, ax1 = axes
    ax0.plot(SNR_POINTS, SNR_LAT_MS, color="#1B9E77", marker="o", linewidth=2.5, markersize=6.5)
    ax0.fill_between(SNR_POINTS, SNR_LAT_MS.min(), SNR_LAT_MS, color="#1B9E77", alpha=0.08)
    ax0.set_title("时延对 SNR 变化不敏感", fontproperties=FONT_PROP, fontsize=16, color="#173A5E", pad=10)
    ax0.set_xlabel("SNR (dB)", fontproperties=FONT_PROP, fontsize=12)
    ax0.set_ylabel("重建时间 (ms/image)", fontproperties=FONT_PROP, fontsize=12)
    ax0.set_xticks(SNR_POINTS)
    ax0.set_ylim(226.5, 235.5)
    for x, y in zip(SNR_POINTS, SNR_LAT_MS):
        ax0.text(x, y + 0.35, f"{y:.1f}", ha="center", va="bottom", fontsize=10.5, fontproperties=FONT_PROP, color="#1B9E77")

    ax1.plot(SNR_POINTS, SNR_PSNR, color="#335C81", marker="o", linewidth=2.5, markersize=6.5, label="PSNR")
    ax1.plot(SNR_POINTS, SNR_SSIM * 40.0, color="#D95F02", marker="s", linewidth=2.1, markersize=5.8, label="SSIM × 40")
    ax1.set_title("质量随信道条件改善而提升", fontproperties=FONT_PROP, fontsize=16, color="#173A5E", pad=10)
    ax1.set_xlabel("SNR (dB)", fontproperties=FONT_PROP, fontsize=12)
    ax1.set_ylabel("PSNR (dB) / SSIM × 40", fontproperties=FONT_PROP, fontsize=12)
    ax1.set_xticks(SNR_POINTS)
    ax1.set_ylim(28, 40)
    ax1.legend(prop=FONT_PROP, frameon=True, loc="upper left")
    for x, y in zip(SNR_POINTS, SNR_PSNR):
        ax1.text(x, y + 0.35, f"{y:.1f}", ha="center", va="bottom", fontsize=10.2, fontproperties=FONT_PROP, color="#335C81")

    fig.suptitle("TVM trusted current 的多 SNR 鲁棒性", fontproperties=FONT_PROP, fontsize=20, color="#173A5E", y=0.99)
    fig.text(
        0.08,
        0.92,
        "基于 300 张图像的真机复测：SNR=1~13 dB 范围内时延稳定在 228~234 ms/image，质量指标单调提升。",
        ha="left",
        va="center",
        fontsize=11.8,
        fontproperties=FONT_PROP,
        color="#5B6D80",
    )
    fig.subplots_adjust(top=0.82, bottom=0.17, left=0.08, right=0.98, wspace=0.2)
    fig.savefig(target, bbox_inches="tight")
    plt.close(fig)


def load_labeled_image(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def render_reconstruction_grid(target: Path) -> None:
    ensure_dir(target)
    canvas_w, canvas_h = 1980, 1100
    pad_x, pad_y = 84, 52
    title_h = 118
    label_h = 44
    row_gap = 48
    col_gap = 26
    img_w, img_h = 380, 280
    bg = Image.new("RGB", (canvas_w, canvas_h), "#FFFFFF")
    draw = ImageDraw = None

    from PIL import ImageDraw, ImageFont

    def load_font_local(size: int, bold: bool = False):
        candidates = [
            Path("/home/tianxing/.local/share/fonts/windows/simhei.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        for p in candidates:
            if p.is_file():
                return ImageFont.truetype(str(p), size)
        return ImageFont.load_default()

    f_title = load_font_local(42, bold=True)
    f_sub = load_font_local(22)
    f_label = load_font_local(26, bold=True)
    f_row = load_font_local(24, bold=True)

    draw = ImageDraw.Draw(bg)
    draw.text((pad_x, 24), "重建效果对比：PyTorch reference vs TVM current", fill="#173A5E", font=f_title)
    draw.text(
        (pad_x, 78),
        "相同样本在不同 SNR 下的重建结果。列方向展示信道条件变化，行方向展示不同场景样本。",
        fill="#5B6D80",
        font=f_sub,
    )

    column_defs = [
        ("PyTorch ref", None),
        ("SNR=1 dB", "snr1"),
        ("SNR=7 dB", "snr7"),
        ("SNR=13 dB", "snr13"),
    ]

    for col_idx, (label, _) in enumerate(column_defs):
        x = pad_x + col_idx * (img_w + col_gap)
        draw.text((x + 96, title_h + 6), label, fill="#173A5E", font=f_label)

    for row_idx, sample_name in enumerate(RECON_SAMPLES):
        y = title_h + label_h + row_idx * (img_h + row_gap)
        stem = sample_name.replace("_recon.png", "")
        draw.text((24, y + img_h // 2 - 18), f"#{stem.split('_')[-1][-5:]}", fill="#13263A", font=f_row)

        ref_path = QUALITY_ROOT / sample_name
        image_paths = [
            ref_path,
            SNR_ROOT / "snr_current_chunk4_snr1_20260330_152054_current" / "reconstructions" / sample_name,
            SNR_ROOT / "snr_current_chunk4_snr7_20260330_152054_current" / "reconstructions" / sample_name,
            SNR_ROOT / "snr_current_chunk4_snr13_20260330_152054_current" / "reconstructions" / sample_name,
        ]
        for col_idx, image_path in enumerate(image_paths):
            x = pad_x + col_idx * (img_w + col_gap)
            tile = load_labeled_image(image_path, (img_w, img_h))
            bg.paste(tile, (x, y))
            draw.rounded_rectangle((x, y, x + img_w, y + img_h), radius=14, outline="#AAB8C4", width=2)

    draw.text(
        (pad_x, canvas_h - 38),
        "说明：参考列为本地归档的 PyTorch reference 重建；其余列为 TVM trusted current 在不同 SNR 下的真机输出。",
        fill="#5B6D80",
        font=f_sub,
    )
    bg.save(target)


def main() -> None:
    for asset in PDF_ASSETS:
        render_pdf(asset)
    render_project_timeline(FIG_DIR / "paper_fig_project_timeline_cn_20260405.png")
    render_openamp_state_machine(FIG_DIR / "paper_fig_openamp_state_machine_cn_20260405.png")
    render_control_message_sequence(FIG_DIR / "paper_fig_control_message_sequence_cn_20260405.png")
    render_mnn_benchmark(FIG_DIR / "paper_fig_mnn_benchmark_cn_20260405.png")
    render_performance_ladder(FIG_DIR / "paper_fig_performance_ladder_cn_20260405.png")
    render_tvm_result_summary(FIG_DIR / "paper_fig_tvm_result_summary_cn_20260405.png")
    render_evidence_bundle_map(FIG_DIR / "paper_fig_evidence_bundle_cn_20260405.png")
    render_framework_positioning(FIG_DIR / "paper_fig_framework_positioning_cn_20260405.png")
    render_perf_quality_tradeoff(FIG_DIR / "paper_fig_perf_quality_tradeoff_cn_20260405.png")
    render_semantic_vs_traditional(FIG_DIR / "paper_fig_semantic_vs_traditional_cn_20260405.png")
    render_system_closure_overview(FIG_DIR / "paper_fig_system_closure_overview_cn_20260405.png")
    render_cover_summary(FIG_DIR / "paper_fig_cover_summary_cn_20260405.png")
    render_snr_curve(FIG_DIR / "paper_fig_snr_robustness_cn_20260405.png")
    render_reconstruction_grid(FIG_DIR / "paper_fig_reconstruction_gallery_cn_20260405.png")
    for asset in PDF_ASSETS:
        print(asset.target)
    print(FIG_DIR / "paper_fig_project_timeline_cn_20260405.png")
    print(FIG_DIR / "paper_fig_openamp_state_machine_cn_20260405.png")
    print(FIG_DIR / "paper_fig_control_message_sequence_cn_20260405.png")
    print(FIG_DIR / "paper_fig_mnn_benchmark_cn_20260405.png")
    print(FIG_DIR / "paper_fig_performance_ladder_cn_20260405.png")
    print(FIG_DIR / "paper_fig_tvm_result_summary_cn_20260405.png")
    print(FIG_DIR / "paper_fig_evidence_bundle_cn_20260405.png")
    print(FIG_DIR / "paper_fig_framework_positioning_cn_20260405.png")
    print(FIG_DIR / "paper_fig_perf_quality_tradeoff_cn_20260405.png")
    print(FIG_DIR / "paper_fig_semantic_vs_traditional_cn_20260405.png")
    print(FIG_DIR / "paper_fig_system_closure_overview_cn_20260405.png")
    print(FIG_DIR / "paper_fig_cover_summary_cn_20260405.png")
    print(FIG_DIR / "paper_fig_snr_robustness_cn_20260405.png")
    print(FIG_DIR / "paper_fig_reconstruction_gallery_cn_20260405.png")


if __name__ == "__main__":
    main()
