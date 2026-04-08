#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import subprocess
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import build_opener, ProxyHandler, Request, urlopen
from urllib.error import URLError

from archive_replay import ArchiveSessionNotFoundError, list_archive_sessions, load_archive_session
from board_access import BoardAccessConfig, build_board_access_config, build_demo_default_board_access
from board_probe import DEFAULT_LIVE_PROBE_OUTPUT, is_successful_probe, load_probe_output, run_live_probe, write_probe_output
from crypto_runtime import (
    DEFAULT_CIPHER_SUITE,
    DEFAULT_CRYPTO_PORT,
    DEFAULT_STATUS_PORT,
    STATUS_PORT_KEYS,
    SUITE_KEYS,
    MlkemSessionManager,
    build_local_crypto_client_command,
    build_remote_crypto_server_command,
    first_config_value,
    parse_int_config,
    resolve_local_crypto_client,
    resolve_local_crypto_server,
    run_ssh_command,
)
from demo_data import (
    PROJECT_ROOT,
    build_aircraft_position_snapshot,
    build_fault_replay,
    build_job_manifest_contract_snapshot,
    build_link_director_catalog,
    build_prerecorded_inference_result,
    build_recover_replay,
    build_snapshot,
    now_iso,
    read_text,
    repo_relative,
    resolve_repo_path,
)
from fault_injector import query_live_status, run_fault_action, run_recover_action
from event_spine import CONTROL_MODE_SCOPE, DATA_MODE_SCOPE, DemoEventSpine, MODE_BOUNDARY_NOTE, default_event_archive_root
from inference_runner import (
    DEFAULT_MAX_INPUTS,
    DEMO_ADMISSION_MODE_ENV,
    DEMO_BASELINE_ADMISSION_MODE_ENV,
    DEMO_BASELINE_SIGNED_MANIFEST_FILE_ENV,
    DEMO_BASELINE_SIGNED_MANIFEST_PUBLIC_KEY_ENV,
    DEMO_SIGNED_MANIFEST_FILE_ENV,
    DEMO_SIGNED_MANIFEST_PUBLIC_KEY_ENV,
    describe_demo_admission,
    describe_demo_variant_support,
    expected_sha_for_variant,
    generate_live_job_id,
    launch_remote_reconstruction_job,
    load_signed_manifest_summary,
)


STATIC_ROOT = Path(__file__).resolve().parent / "static"


def fetch_json_direct(url: str, *, timeout: float) -> dict[str, Any]:
    """Fetch JSON directly from the target without honoring host-wide HTTP proxies."""
    req = Request(url, headers={"Accept": "application/json"})
    opener = build_opener(ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the Feiteng semantic visual return demo dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8079, help="Bind port.")
    parser.add_argument(
        "--probe-env",
        default="",
        help="Optional env file for read-only SSH board probes.",
    )
    parser.add_argument(
        "--probe-timeout-sec",
        type=float,
        default=30.0,
        help="Timeout for the read-only SSH board probe.",
    )
    parser.add_argument(
        "--probe-startup",
        action="store_true",
        help="Run one read-only board probe during startup.",
    )
    parser.add_argument(
        "--demo-admission-mode",
        choices=("legacy_sha", "signed_manifest_v1"),
        default="",
        help="Optional current-demo admission mode override.",
    )
    parser.add_argument(
        "--signed-manifest-file",
        default="",
        help="Optional signed bundle path for the current demo artifact.",
    )
    parser.add_argument(
        "--signed-manifest-public-key",
        default="",
        help="Optional PEM public key used to verify --signed-manifest-file locally before launch.",
    )
    parser.add_argument(
        "--baseline-admission-mode",
        choices=("legacy_sha", "signed_manifest_v1"),
        default="",
        help="Optional baseline-demo admission mode override.",
    )
    parser.add_argument(
        "--baseline-signed-manifest-file",
        default="",
        help="Optional signed bundle path for the baseline demo artifact.",
    )
    parser.add_argument(
        "--baseline-signed-manifest-public-key",
        default="",
        help="Optional PEM public key used to verify --baseline-signed-manifest-file locally before launch.",
    )
    return parser.parse_args()


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def recover_status_lamp(guard_state: str, last_fault_code: str) -> str:
    if str(guard_state or "").upper() != "READY":
        return "red"
    if str(last_fault_code or "").upper() == "NONE":
        return "green"
    return "yellow"


def recover_message(guard_state: str, last_fault_code: str) -> str:
    guard = str(guard_state or "").upper()
    fault = str(last_fault_code or "").upper()
    if guard == "READY" and fault == "NONE":
        return "已使用当前会话凭据执行 SAFE_STOP，板端已回到 READY。"
    if guard == "READY":
        return "已使用当前会话凭据执行 SAFE_STOP，板端已回到 READY；last_fault_code 保留最近故障证据，不宣称已清零。"
    return "已使用当前会话凭据执行 SAFE_STOP，请以当前 guard_state / last_fault_code 为准。"


def last_log_entry(entries: Any) -> str:
    if not isinstance(entries, list):
        return ""
    for item in reversed(entries):
        text = str(item or "").strip()
        if text:
            return text
    return ""


def derive_safe_stop_state(
    *,
    guard_state: str,
    last_fault_code: str,
    last_fault: dict[str, Any] | None,
) -> tuple[str, str, str]:
    guard = str(guard_state or "").upper()
    fault = str(last_fault_code or "").upper()
    last_status = str((last_fault or {}).get("status") or "").lower()
    if last_status == "recovered":
        tone = "online" if fault == "NONE" else "degraded"
        return (
            "RECOVERED",
            tone,
            "最近一次 SAFE_STOP 收口结果已记录到当前面板镜像；物理 SAFE_STOP 仍由 RTOS/Bare Metal 执行。",
        )
    if fault not in {"", "NONE", "UNKNOWN"}:
        return (
            "FAULT",
            "offline",
            "当前 fault code 仍锁存在面板镜像；Linux UI 不宣称已清除 RTOS/Bare Metal 侧 SAFE_STOP/GPIO。",
        )
    if guard == "JOB_ACTIVE":
        return (
            "STANDBY",
            "degraded",
            "板端当前仍在 JOB_ACTIVE；面板只显示 SAFE_STOP 控制面镜像，不自动触发收口。",
        )
    if guard == "READY":
        return (
            "IDLE",
            "online",
            "当前 guard_state=READY，且没有新的 fault latch；面板显示 SAFE_STOP 待命镜像。",
        )
    return (
        "UNKNOWN",
        "neutral",
        "当前 SAFE_STOP 镜像态未知；请以 guard_state / last_fault_code 与正式证据为准。",
    )


def derive_latch_state(*, last_fault_code: str, total_fault_count: int) -> tuple[str, str, str]:
    fault = str(last_fault_code or "").upper()
    if fault in {"", "UNKNOWN"}:
        return (
            "UNKNOWN",
            "neutral",
            "当前没有足够的锁存信息；请以 status_source / status_note 为准。",
        )
    if fault != "NONE":
        return (
            "LATCHED",
            "offline",
            f"last_fault_code={fault} 仍保留在控制面镜像中；fault_count={total_fault_count}。",
        )
    if total_fault_count > 0:
        return (
            "CLEAR",
            "degraded",
            f"当前 last_fault_code 已回到 NONE，但 fault history 计数保留为 {total_fault_count}。",
        )
    return (
        "CLEAR",
        "online",
        "当前 last_fault_code=NONE，且没有额外 fault history 计数。",
    )


def build_safety_panel(
    *,
    guard_state: str,
    last_fault_code: str,
    total_fault_count: int,
    board_online: bool,
    status_source: str,
    status_note: str,
    last_fault: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_stop_state, safe_stop_tone, safe_stop_note = derive_safe_stop_state(
        guard_state=guard_state,
        last_fault_code=last_fault_code,
        last_fault=last_fault,
    )
    latch_state, latch_tone, latch_note = derive_latch_state(
        last_fault_code=last_fault_code,
        total_fault_count=total_fault_count,
    )
    if safe_stop_state == "RECOVERED":
        panel_label = "SAFE_STOP 已执行"
        panel_tone = safe_stop_tone
    elif latch_state == "LATCHED":
        panel_label = "告警锁存"
        panel_tone = latch_tone
    elif board_online:
        panel_label = "无告警"
        panel_tone = "online"
    else:
        panel_label = "证据镜像"
        panel_tone = "degraded"

    last_fault_result: dict[str, Any] = {}
    if last_fault:
        fault_guard_state = str(last_fault.get("guard_state") or guard_state or "")
        fault_code = str(last_fault.get("last_fault_code") or last_fault_code or "")
        last_fault_result = {
            "status": str(last_fault.get("status") or ""),
            "execution_mode": str(last_fault.get("execution_mode") or ""),
            "source_label": str(last_fault.get("source_label") or ""),
            "message": str(last_fault.get("message") or ""),
            "guard_state": fault_guard_state,
            "last_fault_code": fault_code,
            "status_lamp": str(
                last_fault.get("status_lamp") or recover_status_lamp(fault_guard_state, fault_code)
            ),
            "log_tail": last_log_entry(last_fault.get("log_entries")),
        }

    ownership_note = (
        "RTOS/Bare Metal owns physical SAFE_STOP/GPIO; Linux UI is mirror/control surface only."
    )
    return {
        "panel_label": panel_label,
        "panel_tone": panel_tone,
        "safe_stop_state": safe_stop_state,
        "safe_stop_tone": safe_stop_tone,
        "safe_stop_note": safe_stop_note,
        "latch_state": latch_state,
        "latch_tone": latch_tone,
        "latch_note": latch_note,
        "guard_state": guard_state,
        "last_fault_code": last_fault_code,
        "total_fault_count": total_fault_count,
        "board_online": board_online,
        "status_source": status_source,
        "status_note": status_note,
        "last_fault_result": last_fault_result,
        "recover_action": {
            "action_id": "recover_safe_stop",
            "label": "SAFE_STOP 收口",
            "api_path": "/api/recover",
            "method": "POST",
            "note": "沿用现有 recover action，不新增 destructive 操作；Linux 只发起控制面 recover。",
        },
        "ownership_note": ownership_note,
    }


def cue_jump(label: str, *, target_id: str, act_id: str = "", primary: bool = False) -> dict[str, Any]:
    return {
        "label": label,
        "target_id": target_id,
        "act_id": act_id,
        "primary": primary,
    }


def cue_check(label: str, ready: bool, note: str, *, tone: str = "") -> dict[str, Any]:
    return {
        "label": label,
        "ready": ready,
        "tone": tone or ("online" if ready else "degraded"),
        "note": note,
    }


def cue_scene(
    *,
    scene_id: str,
    number: str,
    eyebrow: str,
    title: str,
    status: str,
    tone: str,
    note: str,
    cue_line: str,
    jump: dict[str, Any],
    jump_hint: str,
    checks: list[dict[str, Any]],
    meta: list[str],
) -> dict[str, Any]:
    ready_count = sum(1 for item in checks if item.get("ready"))
    return {
        "scene_id": scene_id,
        "number": number,
        "eyebrow": eyebrow,
        "title": title,
        "status": status,
        "tone": tone,
        "note": note,
        "cue_line": cue_line,
        "jump": jump,
        "jump_hint": jump_hint,
        "checks": checks,
        "ready_count": ready_count,
        "total_checks": len(checks),
        "meta": meta + [f"{ready_count}/{len(checks)} ready"],
    }


def build_operator_cue(
    *,
    snapshot: dict[str, Any],
    board_access: dict[str, Any],
    live: dict[str, Any],
    active_inference: dict[str, Any],
    last_inference: dict[str, Any],
    safety_panel: dict[str, Any],
    gate: dict[str, Any],
    link_director: dict[str, Any],
    event_spine: dict[str, Any],
) -> dict[str, Any]:
    mission = snapshot.get("mission", {}) if isinstance(snapshot.get("mission"), dict) else {}
    guided_demo = snapshot.get("guided_demo", {}) if isinstance(snapshot.get("guided_demo"), dict) else {}
    compare_viewer = guided_demo.get("compare_viewer", {}) if isinstance(guided_demo.get("compare_viewer"), dict) else {}
    performance = snapshot.get("performance", {}) if isinstance(snapshot.get("performance"), dict) else {}

    access_ready = bool(board_access.get("connection_ready"))
    board_online = bool(live.get("board_online"))
    gate_allow = str(gate.get("verdict") or "").lower() == "allow"
    board_busy = str(live.get("guard_state") or "").upper() == "JOB_ACTIVE"
    current_running = bool(active_inference.get("running")) and str(active_inference.get("variant") or "") == "current"
    active_progress = active_inference.get("progress", {}) if isinstance(active_inference.get("progress"), dict) else {}
    current_count_label = str(active_progress.get("count_label") or "")
    current_stage = str(active_progress.get("current_stage") or "")
    last_variant = str(last_inference.get("variant") or "")
    current_result_visible = last_variant == "current"
    current_request_state = str(last_inference.get("request_state") or "")
    current_execution_mode = str(last_inference.get("execution_mode") or "")
    current_live_done = current_result_visible and current_request_state != "running" and current_execution_mode == "live"
    current_archive_only = current_result_visible and (
        str(last_inference.get("status") or "") == "fallback" or current_execution_mode == "prerecorded"
    )
    compare_ready = bool(compare_viewer.get("samples"))
    performance_ready = bool(performance.get("metrics"))
    archive_event_count = int(event_spine.get("event_count") or 0)
    archive_ready = archive_event_count > 0
    safety_recovered = str(safety_panel.get("safe_stop_state") or "").upper() == "RECOVERED"
    fault_latched = str(safety_panel.get("latch_state") or "").upper() == "LATCHED"
    recover_ready = bool((safety_panel.get("recover_action") or {}).get("api_path"))
    link_profile = str(link_director.get("selected_profile_label") or "正常链路")
    mode_boundary_note = str(mission.get("mode_split_note") or MODE_BOUNDARY_NOTE)
    operator_boundary_note = (
        "Operator-assist only: this cue layer recommends scene order, presenter copy, and page jumps. "
        "Probe, manifest preview, Current/PyTorch launch, fault injection, and SAFE_STOP remain manual operator actions."
    )

    if not access_ready:
        scene1_status = "待补全会话"
        scene1_tone = "degraded"
        scene1_note = "先补齐本场 SSH / 推理会话；页面只保存会话，不会自动推进后续动作。"
        scene1_cue = "先把第一幕立住：当前仍是 operator-assist，先补齐会话，再做探板和 gate 预检。"
        scene1_jump = cue_jump("跳到会话接入", target_id="credentialPanel")
    elif not board_online:
        scene1_status = "待探板"
        scene1_tone = "degraded"
        scene1_note = "会话已就绪，但还没有新的 live 探板；第一幕继续如实显示证据态。"
        scene1_cue = "先展示可信状态，再由操作员手动执行探板确认板端 READY。"
        scene1_jump = cue_jump("跳到第一幕探板", target_id="act1Panel", act_id="act1")
    elif not gate_allow:
        scene1_status = gate.get("verdict_label") or "待预检"
        scene1_tone = str(gate.get("tone") or "degraded")
        scene1_note = str(gate.get("message") or "当前 ticket 仍是草案或保守阻断态，不宣称已放行。")
        scene1_cue = "把 gate verdict 讲清楚：当前只展示预检结果，不伪造已放行。"
        scene1_jump = cue_jump("跳到任务票闸机", target_id="jobManifestGateShell", act_id="act1")
    else:
        scene1_status = "可信状态就绪"
        scene1_tone = "online"
        scene1_note = (
            f"会话、探板和 gate 已齐；当前 link director={link_profile}，"
            "但 live 控制面与证据读数仍保持如实显示。"
        )
        scene1_cue = "第一幕已经就绪：当前展示的是可信状态、gate verdict 和 live 控制面，不是自动化编排。"
        scene1_jump = cue_jump("跳到第一幕", target_id="jobManifestGateShell", act_id="act1")

    scene1_checks = [
        cue_check(
            "会话已录入",
            access_ready,
            "当前 demo 进程内已有可复用的板卡会话。" if access_ready else "仍需补齐 host/user/password 或推理 env。",
        ),
        cue_check(
            "只读探板可见",
            board_online,
            f"remoteproc={live.get('remoteproc_state') or 'unknown'} / guard={live.get('guard_state') or 'UNKNOWN'}"
            if board_online
            else "当前没有新的 live 探板，仍以证据态显示。",
        ),
        cue_check(
            "任务票 verdict",
            gate_allow,
            str(gate.get("verdict_label") or "待补全"),
            tone=str(gate.get("tone") or ("online" if gate_allow else "degraded")),
        ),
    ]

    current_launch_ready = access_ready and board_online and gate_allow and not board_busy and not fault_latched
    if current_running:
        scene2_status = str(active_progress.get("label") or "推进中")
        scene2_tone = str(active_progress.get("tone") or "online")
        scene2_note = (
            f"Current live 当前 {current_count_label or '进行中'}；"
            f"{current_stage or '界面正在跟随板端阶段。'}"
        )
        scene2_cue = "第二幕现在只做监看：Current 在线推进仍由操作员手动触发，页面不自动 SAFE_STOP 或重跑。"
    elif current_live_done:
        scene2_status = "Current live 已完成"
        scene2_tone = "online"
        scene2_note = str(
            last_inference.get("message")
            or "Current live 结果已经回到页面，接下来可以切第三幕做正式对照。"
        )
        scene2_cue = "第二幕已经完成：现在可以把同一轮 Current 结果带到第三幕做正式对照。"
    elif current_archive_only:
        scene2_status = "Current 仍是归档展示"
        scene2_tone = "degraded"
        scene2_note = str(
            last_inference.get("message")
            or "当前画面仍在归档 / fallback 态，不能把它说成刚刚完成的 live run。"
        )
        scene2_cue = "第二幕仍在归档态：要么保持诚实展示，要么由操作员重新手动发起 Current live。"
    elif current_launch_ready:
        scene2_status = "可手动启动"
        scene2_tone = "online"
        scene2_note = "第二幕已具备条件，但 Current 300 张图在线推进仍由操作员手动触发。"
        scene2_cue = "这里开始第二幕：由操作员手动启动 Current 300 张图，页面只负责显示进度和证据。"
    else:
        scene2_status = "等待第一幕条件"
        scene2_tone = "neutral" if not access_ready and not board_online else "degraded"
        scene2_note = "当前还不能进入 live run，先完成会话、探板、gate 和空闲态条件。"
        scene2_cue = "第二幕还没开始：先完成第一幕条件，不把等待态包装成已自动运行。"

    scene2_checks = [
        cue_check(
            "Current 允许启动",
            access_ready and board_online and gate_allow and not fault_latched,
            "会话、探板、gate 与安全镜像已经就绪。"
            if access_ready and board_online and gate_allow and not fault_latched
            else "仍需先完成会话 / 探板 / gate，且不能带着 fault latch 进入 live。",
        ),
        cue_check(
            "板端空闲",
            not board_busy,
            "guard_state=READY，可手动发起 Current live。" if not board_busy else "guard_state=JOB_ACTIVE，demo 保守阻断新的 live launch。",
            tone="online" if not board_busy else "degraded",
        ),
        cue_check(
            "Current 结果可讲",
            current_running or current_result_visible,
            current_count_label if current_running else (str(last_inference.get("source_label") or "等待本轮 Current 结果")),
            tone="online" if current_live_done or current_running else ("degraded" if current_archive_only else "neutral"),
        ),
    ]

    if current_live_done:
        scene3_status = "正式对照可讲"
        scene3_tone = "online"
        scene3_note = "同一样例已可直接讲 Current vs PyTorch reference，并把 headline performance / demo mode 边界分开。"
        scene3_cue = "第三幕要点是口径：Current 与 PyTorch 用同一样例对照，4-core headline 与 3-core demo 边界必须分开说。"
    elif compare_ready:
        scene3_status = "归档对照已备"
        scene3_tone = "degraded"
        scene3_note = "Compare viewer 与性能材料都已就位，但本轮 Current live 结果未必已经更新到本场页面。"
        scene3_cue = "第三幕可以先讲正式口径和归档 compare viewer，再明确说明本场 Current live 是否已经完成。"
    else:
        scene3_status = "等待样例上下文"
        scene3_tone = "neutral"
        scene3_note = "当前还没有可用 compare viewer 样例。"
        scene3_cue = "第三幕暂不建议展开，先保证样例和性能口径都可见。"

    scene3_checks = [
        cue_check(
            "Compare viewer 样例",
            compare_ready,
            "当前 compare viewer 已有归档样例与 provenance。" if compare_ready else "当前没有 compare viewer 样例。",
        ),
        cue_check(
            "Current 来源已标注",
            current_live_done or current_archive_only,
            str(last_inference.get("source_label") or "当前仍将沿用归档样例或等待 live 结果。"),
            tone="online" if current_live_done else ("degraded" if current_archive_only else "neutral"),
        ),
        cue_check(
            "4-core vs 3-core 边界",
            performance_ready and bool(mode_boundary_note),
            mode_boundary_note or "保持 4-core headline 与 3-core demo mode 的边界标注。",
        ),
    ]

    if fault_latched:
        scene4_status = "告警锁存"
        scene4_tone = str(safety_panel.get("panel_tone") or "offline")
        scene4_note = (
            f"last_fault_code={safety_panel.get('last_fault_code') or 'UNKNOWN'} 仍锁存在控制面镜像中；"
            "是否 SAFE_STOP 收口仍由操作员决定。"
        )
        scene4_cue = "第四幕现在应该展开：SAFE_STOP / fault latch 仍在，Linux UI 只显示镜像与 recover 入口，不宣称自动收口。"
    elif safety_recovered:
        scene4_status = "SAFE_STOP 已收口"
        scene4_tone = str(safety_panel.get("panel_tone") or "degraded")
        scene4_note = "SAFE_STOP 收口结果已经回写到面板镜像，但 Linux UI 不拥有物理 SAFE_STOP / GPIO 所有权。"
        scene4_cue = "第四幕可说明 SAFE_STOP 已收口，但这仍是 operator-driven 的恢复动作，不是假自动化。"
    elif archive_ready or recover_ready:
        scene4_status = "收口页待命"
        scene4_tone = "online" if archive_ready else "degraded"
        scene4_note = (
            f"archive session={event_spine.get('session_id') or 'pending'} / "
            f"{archive_event_count} events；当前页面可展示 blackbox timeline 与 recover 入口。"
        )
        scene4_cue = "第四幕保持待命：安全镜像、recover 入口和 blackbox timeline 已在页内，但动作仍需操作员手动触发。"
    else:
        scene4_status = "等待事件"
        scene4_tone = "neutral"
        scene4_note = "当前还没有 archive 事件写入，但安全镜像和 FIT 证据仍可展示。"
        scene4_cue = "第四幕暂以证据页为主，blackbox timeline 会在有事件写盘后补齐。"

    scene4_checks = [
        cue_check(
            "SAFE_STOP 镜像",
            bool(safety_panel.get("safe_stop_state")),
            f"safe_stop={safety_panel.get('safe_stop_state') or 'UNKNOWN'} / fault={safety_panel.get('last_fault_code') or 'UNKNOWN'}",
            tone=str(safety_panel.get("panel_tone") or "neutral"),
        ),
        cue_check(
            "Blackbox timeline",
            archive_ready,
            f"{archive_event_count} events / {event_spine.get('last_event_at') or '等待首次写盘'}"
            if archive_ready
            else "当前尚无 archive 事件，会先显示 mission fallback timeline。",
            tone="online" if archive_ready else "neutral",
        ),
        cue_check(
            "Recover 入口",
            recover_ready,
            f"{(safety_panel.get('recover_action') or {}).get('method') or 'POST'} {(safety_panel.get('recover_action') or {}).get('api_path') or '/api/recover'}"
            if recover_ready
            else "当前没有 recover action 绑定。",
            tone="online" if recover_ready else "neutral",
        ),
    ]

    scenes = [
        cue_scene(
            scene_id="scene1",
            number="01",
            eyebrow="可信状态",
            title="第一幕 / 板卡接入与 gate",
            status=scene1_status,
            tone=scene1_tone,
            note=scene1_note,
            cue_line=scene1_cue,
            jump=scene1_jump,
            jump_hint="会话 / 探板 / gate",
            checks=scene1_checks,
            meta=[
                f"link={link_profile}",
                f"admission={gate.get('admission_label') or '未设置'}",
            ],
        ),
        cue_scene(
            scene_id="scene2",
            number="02",
            eyebrow="语义回传",
            title="第二幕 / Current live",
            status=scene2_status,
            tone=scene2_tone,
            note=scene2_note,
            cue_line=scene2_cue,
            jump=cue_jump("跳到第二幕", target_id="act2Panel", act_id="act2"),
            jump_hint="Current 进度与样例画面",
            checks=scene2_checks,
            meta=[
                f"count={current_count_label or '0 / 300'}",
                f"mode={current_execution_mode or 'pending'}",
            ],
        ),
        cue_scene(
            scene_id="scene3",
            number="03",
            eyebrow="正式对照",
            title="第三幕 / Compare 与性能口径",
            status=scene3_status,
            tone=scene3_tone,
            note=scene3_note,
            cue_line=scene3_cue,
            jump=cue_jump("跳到第三幕", target_id="compareViewerShell", act_id="act3"),
            jump_hint="Compare viewer 与 performance",
            checks=scene3_checks,
            meta=[
                "同一样例 compare viewer",
                "4-core headline / 3-core demo",
            ],
        ),
        cue_scene(
            scene_id="scene4",
            number="04",
            eyebrow="故障收口",
            title="第四幕 / SAFE_STOP 与 archive",
            status=scene4_status,
            tone=scene4_tone,
            note=scene4_note,
            cue_line=scene4_cue,
            jump=cue_jump("跳到第四幕", target_id="act4Panel", act_id="act4"),
            jump_hint="fault / recover / blackbox timeline",
            checks=scene4_checks,
            meta=[
                f"SAFE_STOP={safety_panel.get('safe_stop_state') or 'UNKNOWN'}",
                f"archive={archive_event_count} events",
            ],
        ),
    ]

    if not access_ready:
        current_scene = scenes[0]
        next_action = cue_jump("跳到会话接入", target_id="credentialPanel", primary=True)
        next_step_note = "先补齐本场会话；之后再由操作员执行探板与 gate 预检。"
    elif not board_online:
        current_scene = scenes[0]
        next_action = cue_jump("跳到第一幕探板", target_id="act1Panel", act_id="act1", primary=True)
        next_step_note = "先做只读探板确认板端在线；页面不会自动刷新成真机状态。"
    elif fault_latched or safety_recovered:
        current_scene = scenes[3]
        next_action = cue_jump("跳到第四幕 SAFE_STOP", target_id="act4Panel", act_id="act4", primary=True)
        next_step_note = scene4_note
    elif not gate_allow:
        current_scene = scenes[0]
        next_action = cue_jump("跳到任务票闸机", target_id="jobManifestGateShell", act_id="act1", primary=True)
        next_step_note = str(gate.get("message") or "先看 gate verdict，再决定是否推进 live。")
    elif current_running or not current_live_done or current_archive_only:
        current_scene = scenes[1]
        next_action = cue_jump("跳到第二幕 Current", target_id="act2Panel", act_id="act2", primary=True)
        next_step_note = (
            "由操作员手动启动或继续监看 Current 300 张图在线推进；页面只做进度和证据展示。"
            if not current_live_done
            else scene2_note
        )
    elif compare_ready:
        current_scene = scenes[2]
        next_action = cue_jump("跳到第三幕 Compare", target_id="compareViewerShell", act_id="act3", primary=True)
        next_step_note = "用同一样例讲 Current / PyTorch 对照，并明确 4-core headline 与 3-core demo 边界。"
    else:
        current_scene = scenes[3]
        next_action = cue_jump("跳到第四幕 SAFE_STOP", target_id="act4Panel", act_id="act4", primary=True)
        next_step_note = scene4_note

    for item in scenes:
        item["recommended"] = item["scene_id"] == current_scene["scene_id"]

    return {
        "mode": "operator_assist_only",
        "status_label": current_scene["title"],
        "status_tone": current_scene["tone"],
        "current_scene_id": current_scene["scene_id"],
        "current_scene_label": current_scene["title"],
        "current_scene_tone": current_scene["tone"],
        "presenter_line": current_scene["cue_line"],
        "next_step_label": next_action["label"],
        "next_step_note": next_step_note,
        "next_action": next_action,
        "manual_boundary_note": operator_boundary_note,
        "boundary_note": mode_boundary_note,
        "quick_jumps": [
            cue_jump("Mission 总览", target_id="missionPanel"),
            cue_jump("会话接入", target_id="credentialPanel"),
            cue_jump("任务票闸机", target_id="jobManifestGateShell", act_id="act1"),
            cue_jump("第二幕 Current", target_id="act2Panel", act_id="act2"),
            cue_jump("第三幕 Compare", target_id="compareViewerShell", act_id="act3"),
            cue_jump("性能口径", target_id="performanceGrid"),
            cue_jump("第四幕 SAFE_STOP", target_id="act4Panel", act_id="act4"),
            cue_jump("Blackbox Timeline", target_id="archiveTimelineCard"),
        ],
        "scenes": scenes,
    }


def link_profile_catalog() -> dict[str, Any]:
    return build_link_director_catalog()


def link_profile_by_id(profile_id: str) -> dict[str, Any]:
    for profile in link_profile_catalog()["profiles"]:
        if str(profile.get("profile_id") or "") == profile_id:
            return dict(profile)
    raise KeyError(profile_id)


def default_link_director_state() -> dict[str, Any]:
    profile = link_profile_by_id("normal")
    return {
        "selected_profile_id": profile["profile_id"],
        "last_applied_at": "",
        "last_operator_action": "导演台尚未切换预案；当前默认按正常链路展示。",
        "apply_status": "idle",
        "backend_binding": "ui_scaffold_only",
    }


def _compute_benchmark(samples: dict[str, list[float]]) -> dict[str, Any]:
    """从样本列表计算 min/max/mean/median，用于 batch benchmark 汇总。"""
    import statistics

    result: dict[str, Any] = {}
    for key, values in samples.items():
        if not values:
            result[key] = None
            continue
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        result[key] = {
            "n": n,
            "min_ms": round(sorted_vals[0], 2),
            "max_ms": round(sorted_vals[-1], 2),
            "mean_ms": round(statistics.mean(sorted_vals), 2),
            "median_ms": round(statistics.median(sorted_vals), 2),
            "p95_ms": round(sorted_vals[int(n * 0.95)], 2) if n >= 20 else None,
        }
    return result


class DashboardState:
    def __init__(
        self,
        probe_env: str | None,
        probe_timeout_sec: float,
        probe_cache_path: str | Path | None = DEFAULT_LIVE_PROBE_OUTPUT,
        demo_startup_env_overrides: dict[str, str] | None = None,
        event_archive_root: str | Path | None = None,
    ) -> None:
        self._probe_env = probe_env or None
        self._probe_timeout_sec = probe_timeout_sec
        self._probe_cache_path = probe_cache_path
        self._event_archive_root = Path(event_archive_root).resolve() if event_archive_root is not None else None
        self._lock = Lock()
        self._board_access = build_demo_default_board_access(
            self._probe_env,
            startup_env_overrides=demo_startup_env_overrides,
        )
        self._last_control_status: dict[str, Any] | None = None
        self._last_inference_result: dict[str, Any] | None = None
        self._recent_inference_results: dict[str, dict[str, Any]] = {}
        self._last_fault_result: dict[str, Any] | None = None
        self._inference_jobs: dict[str, dict[str, Any]] = {}
        self._manifest_preview_count = 0
        self._link_director = default_link_director_state()
        self._aircraft_position = build_aircraft_position_snapshot()
        self._event_spine = DemoEventSpine(event_archive_root)
        self._crypto_status_cache: dict[str, Any] | None = None
        self._crypto_status_cache_ts: float = 0.0
        self._crypto_enabled: bool = False
        self._last_soft_recover_ts: float = 0.0
        self._soft_recover_cooldown_sec: float = 45.0
        self._last_soft_recover_result: dict[str, Any] | None = None
        # ── 批量推理状态 ──
        self._batch_state: dict[str, Any] | None = None
        # ── ML-KEM 持久化会话 ──
        self._mlkem_session_mgr: MlkemSessionManager | None = None

        cached_probe = load_probe_output(probe_cache_path) if probe_cache_path else None
        if is_successful_probe(cached_probe):
            self._last_live_probe = {**cached_probe, "_loaded_from_cache": True}
        else:
            self._last_live_probe = None

        initial_snapshot = build_snapshot(self._last_live_probe, aircraft_position=self._aircraft_position)
        self._trusted_current_sha = initial_snapshot["project"]["trusted_current_sha"]
        self._target_label = "cortex-a72 + neon"
        self._runtime_label = "tvm"

    def _live_board_access_for_variant(self, board_access: BoardAccessConfig, *, variant: str) -> BoardAccessConfig:
        if variant != "current" or not self._trusted_current_sha:
            return board_access
        return board_access.with_env_overrides({"INFERENCE_CURRENT_EXPECTED_SHA256": self._trusted_current_sha})

    def set_board_access(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            fallback = self._board_access
        config = build_board_access_config(payload, fallback=fallback)
        with self._lock:
            self._board_access = config
            crypto_enabled = self._crypto_enabled
        # 密码录入后立即在后台尝试启动板端 tcp_server，无需等待 toggle ON 或首次推理
        if config.connection_ready:
            import threading
            threading.Thread(
                target=self._ensure_board_tcp_server,
                args=(config,),
                daemon=True,
                name="tcp-server-autostart",
            ).start()
        return config.to_public_dict()

    def _merged_aircraft_position_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = json.loads(json.dumps(self._aircraft_position, ensure_ascii=False))
        merged = dict(current)

        for key in (
            "aircraft_id",
            "mission_call_sign",
            "source_kind",
            "source_status",
            "source_label",
            "source_note",
        ):
            value = payload.get(key)
            if value not in (None, ""):
                merged[key] = value

        position = dict(current.get("position") or {})
        if isinstance(payload.get("position"), dict):
            position.update(payload["position"])
        for key in ("latitude", "longitude"):
            value = payload.get(key)
            if value not in (None, ""):
                position[key] = value

        kinematics = dict(current.get("kinematics") or {})
        if isinstance(payload.get("kinematics"), dict):
            kinematics.update(payload["kinematics"])
        for key in ("altitude_m", "ground_speed_kph", "heading_deg", "vertical_speed_mps"):
            value = payload.get(key)
            if value not in (None, ""):
                kinematics[key] = value

        fix = dict(current.get("fix") or {})
        if isinstance(payload.get("fix"), dict):
            fix.update(payload["fix"])
        flat_fix = {
            "type": payload.get("fix_type"),
            "confidence_m": payload.get("confidence_m"),
            "satellites": payload.get("satellites"),
        }
        for key, value in flat_fix.items():
            if value not in (None, ""):
                fix[key] = value

        sample = dict(current.get("sample") or {})
        if isinstance(payload.get("sample"), dict):
            sample.update(payload["sample"])
        for key in ("captured_at", "sequence", "producer_id", "transport"):
            value = payload.get(key)
            if value not in (None, ""):
                sample[key] = value

        merged["position"] = position
        merged["kinematics"] = kinematics
        merged["fix"] = fix
        merged["updated_at"] = now_iso()

        position_changed = any(payload.get(key) not in (None, "") for key in ("latitude", "longitude")) or isinstance(
            payload.get("position"),
            dict,
        )
        if position_changed:
            merged.setdefault("source_kind", "upper_computer_gps")
            if not payload.get("source_kind"):
                merged["source_kind"] = "upper_computer_gps"
            if not payload.get("source_status"):
                merged["source_status"] = "live"
            if not payload.get("source_label"):
                merged["source_label"] = "Upper Computer GPS live feed"
            if not payload.get("source_note"):
                merged["source_note"] = "Upper-computer GPS live samples are currently driving the backend aircraft-position contract."
            explicit_captured_at = payload.get("captured_at") not in (None, "") or (
                isinstance(payload.get("sample"), dict) and payload["sample"].get("captured_at") not in (None, "")
            )
            if not explicit_captured_at:
                sample["captured_at"] = merged["updated_at"]
            explicit_sequence = payload.get("sequence") not in (None, "") or (
                isinstance(payload.get("sample"), dict) and payload["sample"].get("sequence") not in (None, "")
            )
            if not explicit_sequence:
                sample["sequence"] = self._safe_int(current.get("sample", {}).get("sequence"), default=0) + 1
        merged["sample"] = sample
        return merged

    def current_aircraft_position(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._aircraft_position, ensure_ascii=False))

    def set_aircraft_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged = self._merged_aircraft_position_payload(payload)
        aircraft_position = build_aircraft_position_snapshot(merged)
        with self._lock:
            self._aircraft_position = aircraft_position

        self._archive_event_snapshot(
            reason="aircraft_position_update",
            extra={
                "source_kind": aircraft_position["source_kind"],
                "source_status": aircraft_position["source_status"],
                "latitude": aircraft_position["position"]["latitude"],
                "longitude": aircraft_position["position"]["longitude"],
            },
        )
        return aircraft_position

    def set_link_director_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile_id = str(payload.get("profile_id") or "").strip().lower()
        if not profile_id:
            raise ValueError("missing profile_id")
        try:
            profile = link_profile_by_id(profile_id)
        except KeyError as exc:
            raise ValueError("unsupported profile_id") from exc

        change_applied = False
        previous_profile_id = "normal"
        previous_profile_label = link_profile_by_id("normal")["label"]
        with self._lock:
            previous_profile_id = str(self._link_director.get("selected_profile_id") or "normal")
            try:
                previous_profile_label = link_profile_by_id(previous_profile_id)["label"]
            except KeyError:
                previous_profile_id = "normal"
                previous_profile_label = link_profile_by_id("normal")["label"]
            if previous_profile_id != profile["profile_id"]:
                action = (
                    f"导演台已切到 {profile['label']} 预案；当前仅更新操作员态势与后续绑定目标，"
                    "未执行 tc/netem 或物理弱网控制。"
                )
                self._link_director = {
                    "selected_profile_id": profile["profile_id"],
                    "last_applied_at": now_iso(),
                    "last_operator_action": action,
                    "apply_status": "staged",
                    "backend_binding": "ui_scaffold_only",
                }
                change_applied = True

        if not change_applied:
            status = self.current_link_director_status()
            status["change_applied"] = False
            status["status_message"] = (
                f"导演台已保持 {profile['label']} 预案；当前仍是 UI/control-plane scaffold，"
                "不会执行 tc/netem 或改写 live telemetry。"
            )
            status["previous_profile_id"] = previous_profile_id
            status["previous_profile_label"] = previous_profile_label
            return status

        status = self.current_link_director_status()
        status["change_applied"] = True
        status["status_message"] = str(status.get("last_operator_action") or "")
        status["previous_profile_id"] = previous_profile_id
        status["previous_profile_label"] = previous_profile_label
        self._event_spine.publish(
            "LINK_PROFILE_CHANGED",
            source="link_director",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=str(status.get("last_operator_action") or f"Link director switched to {profile['label']}."),
            data={
                "profile_id": profile["profile_id"],
                "profile_label": profile["label"],
                "previous_profile_id": previous_profile_id,
                "previous_profile_label": previous_profile_label,
                "backend_binding": str(status.get("backend_binding") or "ui_scaffold_only"),
            },
        )
        self._archive_event_snapshot(
            reason="link_profile_changed",
            extra={
                "profile_id": profile["profile_id"],
                "profile_label": profile["label"],
                "previous_profile_id": previous_profile_id,
                "previous_profile_label": previous_profile_label,
                "backend_binding": str(status.get("backend_binding") or "ui_scaffold_only"),
            },
        )
        return status

    def current_snapshot(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
            aircraft_position = self._aircraft_position
        return build_snapshot(live_probe=live_probe, aircraft_position=aircraft_position)

    def _get_mlkem_session_manager(
        self, board_access: "BoardAccessConfig", env_values: dict,
    ) -> MlkemSessionManager | None:
        """获取或创建持久化 ML-KEM 会话管理器

        如果 host 发生变化会关闭旧管理器。
        找不到 tcp_client.py 时返回 None（回退到子进程模式）。
        """
        with self._lock:
            if self._mlkem_session_mgr is not None:
                if self._mlkem_session_mgr._host == board_access.host:
                    return self._mlkem_session_mgr
                else:
                    self._mlkem_session_mgr.close()
                    self._mlkem_session_mgr = None

        tcp_client, _ = resolve_local_crypto_client(env_values)
        if tcp_client is None:
            return None

        mgr = MlkemSessionManager(
            env_values, host=board_access.host, client_script=tcp_client)
        with self._lock:
            self._mlkem_session_mgr = mgr
        return mgr

    def _idle_active_inference_summary(self) -> dict[str, Any]:
        return {
            "running": False,
            "job_id": "",
            "variant": "",
            "source": "demo_process",
            "queue_depth": 0,
            "request_state": "idle",
            "status_category": "idle",
            "message": "当前 demo 进程内没有活动中的 live 作业。",
            "progress": {
                "state": "idle",
                "label": "队列空闲",
                "tone": "neutral",
                "percent": 0,
                "phase_percent": 0,
                "completed_count": 0,
                "expected_count": DEFAULT_MAX_INPUTS,
                "remaining_count": DEFAULT_MAX_INPUTS,
                "completion_ratio": 0.0,
                "count_source": "demo_default",
                "count_label": "0 active / 0 queued",
                "current_stage": "等待操作员发起任务",
                "stages": [],
                "event_log": [],
            },
        }

    def _active_inference_summary(self) -> dict[str, Any]:
        record = self._running_inference_job_record()
        if record is not None:
            snapshot = record["snapshot"]
            progress = snapshot.get("progress") if isinstance(snapshot.get("progress"), dict) else {}
            return {
                "running": True,
                "job_id": record["job_id"],
                "variant": record["variant"],
                "source": "demo_process",
                "queue_depth": 1,
                "request_state": snapshot.get("request_state", "running"),
                "status_category": snapshot.get("status_category", "running"),
                "message": str(snapshot.get("message") or "当前 live 作业正在推进。"),
                "progress": progress,
            }

        with self._lock:
            control_status = dict(self._last_control_status or {})

        guard_state = str(control_status.get("guard_state") or "").upper()
        if guard_state != "JOB_ACTIVE":
            return self._idle_active_inference_summary()

        active_job_id = int(control_status.get("active_job_id") or 0)
        event_log = list(control_status.get("logs") or [])
        return {
            "running": True,
            "job_id": "",
            "variant": "unknown",
            "source": "board_status",
            "queue_depth": 1,
            "request_state": "running",
            "status_category": "board_busy",
            "message": "板端当前报告 guard_state=JOB_ACTIVE；demo 仅展示现有作业状态，不自动 SAFE_STOP。",
            "progress": {
                "state": "running",
                "label": "板端已有活动作业",
                "tone": "degraded",
                "percent": 0,
                "phase_percent": 0,
                "completed_count": 0,
                "expected_count": DEFAULT_MAX_INPUTS,
                "remaining_count": DEFAULT_MAX_INPUTS,
                "completion_ratio": 0.0,
                "count_source": "board_status",
                "count_label": f"active_job_id={active_job_id}" if active_job_id else "JOB_ACTIVE",
                "current_stage": "等待当前作业完成或人工 SAFE_STOP",
                "stages": [
                    {
                        "key": "job_active",
                        "label": "板端作业占用",
                        "status": "current",
                        "detail": "当前 board status 报告 guard_state=JOB_ACTIVE。",
                    }
                ],
                "event_log": event_log,
            },
        }

    def current_link_director_status(self) -> dict[str, Any]:
        catalog = link_profile_catalog()
        with self._lock:
            stored = dict(self._link_director)
        selected_id = str(stored.get("selected_profile_id") or "normal")
        try:
            selected = link_profile_by_id(selected_id)
        except KeyError:
            selected = link_profile_by_id("normal")
            selected_id = "normal"
        status = str(stored.get("apply_status") or "idle")
        tone = selected.get("tone", "neutral") if status != "idle" else "neutral"
        label = "导演台待命" if status == "idle" else f"{selected['label']} 预案已设定"
        profiles = [{**profile, "active": profile["profile_id"] == selected_id} for profile in catalog["profiles"]]
        return {
            "status": status,
            "label": label,
            "tone": tone,
            "backend_binding": str(stored.get("backend_binding") or catalog.get("backend_status") or "ui_scaffold_only"),
            "backend_status": catalog["backend_status"],
            "summary": catalog["summary"],
            "plane_split_note": catalog["plane_split_note"],
            "mode_boundary_note": MODE_BOUNDARY_NOTE,
            "truth_note": "当前仅记录导演台预案；live 控制面与证据读数继续如实显示。",
            "selected_profile_id": selected_id,
            "selected_profile_label": selected["label"],
            "selected_profile": selected,
            "profiles": profiles,
            "last_applied_at": str(stored.get("last_applied_at") or ""),
            "last_operator_action": str(stored.get("last_operator_action") or catalog["summary"]),
        }

    def _signed_manifest_gate_details(self, access: BoardAccessConfig, *, variant: str) -> dict[str, Any]:
        try:
            return load_signed_manifest_summary(access.build_env(), variant=variant, require_public_key=False)
        except ValueError:
            return {}

    def _next_manifest_preview_job_id(self, *, variant: str) -> str:
        with self._lock:
            self._manifest_preview_count += 1
            sequence = self._manifest_preview_count
        return f"manifest-preview-{variant}-{sequence:04d}"

    def _job_manifest_gate_status(
        self,
        *,
        board_access: BoardAccessConfig,
        admission: dict[str, Any],
        support: dict[str, Any],
        active_inference: dict[str, Any],
        control_status: dict[str, Any] | None,
        trusted_sha: str,
        variant: str,
        status_probe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        contract = build_job_manifest_contract_snapshot()
        defaults = contract["defaults"]
        variant_access = self._live_board_access_for_variant(board_access, variant=variant)
        signed_summary = (
            self._signed_manifest_gate_details(variant_access, variant=variant)
            if admission.get("mode") == "signed_manifest_v1"
            else {}
        )
        variant_label = "PyTorch" if variant == "baseline" else "Current"
        active_variant = str(active_inference.get("variant") or "")
        active_job_running = bool(active_inference.get("running"))
        active_job_id = str(active_inference.get("job_id") or "")
        expected_sha = str(admission.get("artifact_sha256") or expected_sha_for_variant(variant_access, variant) or "")
        if variant == "current" and not expected_sha:
            expected_sha = trusted_sha

        expected_outputs = int(signed_summary.get("expected_outputs") or defaults["expected_outputs"])
        deadline_ms = int(signed_summary.get("deadline_ms") or defaults["deadline_ms"])
        job_flags = str(signed_summary.get("job_flags") or defaults["job_flags"])

        job_id = ""
        job_id_source = "launch_generated"
        guard_state = str((control_status or {}).get("guard_state") or "").upper()
        board_active_job_id = int((control_status or {}).get("active_job_id") or 0)
        if active_job_running and active_job_id:
            job_id = active_job_id
            job_id_source = "active_job"
        elif guard_state == "JOB_ACTIVE" and board_active_job_id > 0:
            job_id = str(board_active_job_id)
            job_id_source = "board_status"
        elif self._last_inference_result and self._last_inference_result.get("variant") == variant:
            last_job_id = str(self._last_inference_result.get("job_id") or "")
            if last_job_id:
                job_id = last_job_id
                job_id_source = "last_launch"

        preview_probe_failed = bool(status_probe) and str(status_probe.get("status") or "") != "success"
        ready_for_launch = bool(support.get("launch_allowed")) and admission.get("status") == "ready" and board_access.connection_ready
        verdict = "hold"
        verdict_label = "待补全"
        if active_job_running or guard_state == "JOB_ACTIVE":
            verdict = "deny"
            verdict_label = "暂不放行"
        elif preview_probe_failed:
            verdict = "hold"
            verdict_label = "待复核"
        elif ready_for_launch:
            verdict = "allow"
            verdict_label = "可放行"

        reasons: list[str] = []

        def append_reason(text: str) -> None:
            value = str(text or "").strip()
            if value and value not in reasons:
                reasons.append(value)

        if active_job_running and active_job_id:
            if active_variant == variant:
                append_reason(
                    f"{variant_label} live job {active_job_id} is already running in the demo process; a new ticket stays blocked."
                )
            else:
                append_reason(
                    f"Demo process already has active {active_variant or 'other'} live job {active_job_id}; "
                    "the gate conservatively blocks another ticket."
                )
        if guard_state == "JOB_ACTIVE":
            active_suffix = f" active_job_id={board_active_job_id}." if board_active_job_id else ""
            append_reason(f"STATUS_RESP reports guard_state=JOB_ACTIVE; the demo will not auto SAFE_STOP.{active_suffix}")
        if preview_probe_failed:
            probe_message = str(status_probe.get("message") or "").strip()
            if probe_message:
                append_reason(f"Preview STATUS_REQ did not return a usable STATUS_RESP: {probe_message}")
            else:
                append_reason("Preview STATUS_REQ did not return a usable STATUS_RESP; the gate remains conservative.")
        if not board_access.connection_ready:
            missing = ", ".join(board_access.missing_connection_fields()) or "host, user, password"
            append_reason(f"Board session is incomplete: missing {missing}.")
        support_note = str(support.get("note") or "")
        if not support.get("launch_allowed"):
            append_reason(support_note or f"{variant_label} live path is not launchable yet.")
        admission_note = str(admission.get("note") or "")
        if admission_note:
            append_reason(admission_note)
        if ready_for_launch and not status_probe:
            append_reason("This view reflects cached control/demo state; use the preview action to re-check admitability only.")

        if active_job_running and active_variant == variant:
            status = "running"
            label = "任务票已在推进"
            tone = "online"
            message = (
                f"{variant_label} 任务票已进入 live launch；若再提交新票，demo 会保守阻断，"
                "避免把预检和真实 live 路径混写。"
            )
        elif active_job_running:
            status = "blocked"
            label = "票据阻断"
            tone = "degraded"
            message = (
                f"当前 demo 进程已有 {active_variant or 'other'} live 作业占用；"
                f"{variant_label} 新票只做 gate 预检，不会越过现有控制面边界。"
            )
        elif guard_state == "JOB_ACTIVE":
            status = "blocked"
            label = "票据阻断"
            tone = "degraded"
            message = "板端当前 guard_state=JOB_ACTIVE；manifest gate 保守阻断新票，不自动 SAFE_STOP。"
        elif preview_probe_failed:
            status = "draft"
            label = "待复核"
            tone = "degraded"
            message = (
                f"{variant_label} 票据预检未拿到可用 STATUS_RESP；当前不会宣称可放行，"
                "也不会启动 board execution。"
            )
        elif support.get("launch_allowed") and admission.get("status") == "ready" and board_access.connection_ready:
            status = "ready"
            label = "可签发"
            tone = "online"
            message = (
                f"{variant_label} 票面参数已齐；launch 时继续沿用现有 "
                f"{admission.get('label') or 'admission'}，不改 JOB_REQ / signed-manifest 协议。"
            )
        else:
            status = "draft"
            label = "待补全"
            tone = "degraded"
            message = "当前仅展示任务票草案；会话、expected_sha 或 signed-manifest 条件未全部就绪，不宣称可放行。"

        field_map = {
            "job_id": job_id,
            "expected_sha256": expected_sha,
            "expected_outputs": expected_outputs,
            "deadline_ms": deadline_ms,
            "job_flags": job_flags,
            "input_shape": str(defaults["input_shape"]),
            "input_dtype": str(defaults["input_dtype"]),
            "output_shape": str(defaults["output_shape"]),
            "output_dtype": str(defaults["output_dtype"]),
            "shape_buckets": str(defaults["shape_buckets"]),
            "manifest_sha256": str(admission.get("manifest_sha256") or ""),
            "key_id": str(admission.get("key_id") or ""),
        }
        wire_fields = [
            {
                "key": "job_id",
                "label": "job_id",
                "value": job_id or "launch 时由 wrapper 分配 uint32",
                "source": job_id_source,
            },
            {
                "key": "expected_sha256",
                "label": "expected_sha256",
                "value": expected_sha or "未就绪",
                "source": "admission",
            },
            {
                "key": "expected_outputs",
                "label": "expected_outputs",
                "value": str(expected_outputs),
                "source": "signed_manifest" if signed_summary else "wrapper_default",
            },
            {
                "key": "deadline_ms",
                "label": "deadline_ms",
                "value": str(deadline_ms),
                "source": "signed_manifest" if signed_summary else "wrapper_default",
            },
            {
                "key": "job_flags",
                "label": "job_flags",
                "value": job_flags,
                "source": "signed_manifest" if signed_summary else "wrapper_default",
            },
            {
                "key": "manifest_sha256",
                "label": "manifest_sha256",
                "value": str(admission.get("manifest_sha256") or "legacy / none"),
                "source": "signed_manifest" if signed_summary else "legacy",
            },
            {
                "key": "key_id",
                "label": "key_id",
                "value": str(admission.get("key_id") or "legacy / none"),
                "source": "signed_manifest" if signed_summary else "legacy",
            },
        ]
        context_fields = [
            {
                "key": "input_shape",
                "label": "input_shape",
                "value": str(defaults["input_shape"]),
                "source": "archive_report",
            },
            {
                "key": "shape_buckets",
                "label": "shape_buckets",
                "value": str(defaults["shape_buckets"]),
                "source": "archive_report",
            },
            {
                "key": "output_shape",
                "label": "output_shape",
                "value": str(defaults["output_shape"]),
                "source": "archive_report",
            },
            {
                "key": "input_dtype",
                "label": "input_dtype",
                "value": str(defaults["input_dtype"]),
                "source": "archive_report",
            },
            {
                "key": "output_dtype",
                "label": "output_dtype",
                "value": str(defaults["output_dtype"]),
                "source": "archive_report",
            },
        ]
        return {
            "status": status,
            "label": label,
            "tone": tone,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "variant": variant,
            "variant_label": variant_label,
            "admission_mode": str(admission.get("mode") or "legacy_sha"),
            "admission_label": str(admission.get("label") or ""),
            "admission_note": str(admission.get("note") or ""),
            "summary": contract["summary"],
            "protocol_boundary_note": contract["protocol_boundary_note"],
            "demo_only_note": (
                "Preview action is demo/operator-side only: it re-checks admitability and emits preview-only JOB_* events, "
                "but it does not send JOB_REQ or mutate board execution."
            ),
            "message": message,
            "reasons": reasons,
            "status_source": (
                "preview_status"
                if status_probe and str(status_probe.get("status") or "") == "success"
                else "preview_status_error"
                if preview_probe_failed
                else "cached_control_status"
                if control_status
                else "demo_snapshot"
            ),
            "field_map": field_map,
            "wire_fields": wire_fields,
            "context_fields": context_fields,
            "evidence": contract["evidence"],
        }

    def current_job_manifest_gate_status(
        self,
        *,
        variant: str = "current",
        status_probe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            board_access = self._board_access
            control_status = dict(self._last_control_status or {}) if self._last_control_status else None
        active_inference = self._active_inference_summary()
        variant_access = self._live_board_access_for_variant(board_access, variant=variant)
        admission = describe_demo_admission(variant_access, variant=variant)
        support = describe_demo_variant_support(variant_access, variant=variant)
        effective_control_status = control_status
        if status_probe and str(status_probe.get("status") or "") == "success":
            effective_control_status = status_probe
        return self._job_manifest_gate_status(
            board_access=board_access,
            admission=admission,
            support=support,
            active_inference=active_inference,
            control_status=effective_control_status,
            trusted_sha=self._trusted_current_sha,
            variant=variant,
            status_probe=status_probe,
        )

    def preview_job_manifest_gate(self, *, variant: str = "current") -> dict[str, Any]:
        with self._lock:
            board_access = self._board_access

        variant_access = self._live_board_access_for_variant(board_access, variant=variant)
        status_probe: dict[str, Any] | None = None
        trusted_sha = expected_sha_for_variant(variant_access, variant) or self._trusted_current_sha
        if board_access.probe_ready:
            status_probe = query_live_status(board_access, trusted_sha=trusted_sha)
            if status_probe.get("status") == "success":
                with self._lock:
                    self._last_control_status = status_probe

        gate = self.current_job_manifest_gate_status(variant=variant, status_probe=status_probe)
        preview_job_id = self._next_manifest_preview_job_id(variant=variant)
        common_data = {
            "variant": variant,
            "preview_only": True,
            "preview_action": "job_manifest_gate_preview",
            "verdict": gate["verdict"],
            "status_category": gate["status"],
            "admission_mode": gate["admission_mode"],
            "status_source": gate["status_source"],
        }
        self._event_spine.publish(
            "JOB_SUBMITTED",
            job_id=preview_job_id,
            source="manifest_gate_preview",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=f"{gate['variant_label']} manifest gate preview requested by the operator.",
            data=common_data,
        )
        preview_event_type = "JOB_ADMITTED" if gate["verdict"] == "allow" else "JOB_REJECTED"
        preview_message = (
            f"{gate['variant_label']} 任务票 demo-only 预检判定为可放行；未发送 JOB_REQ，也未启动板端执行。"
            if gate["verdict"] == "allow"
            else f"{gate['variant_label']} 任务票 demo-only 预检未放行；未发送 JOB_REQ，也未启动板端执行。"
        )
        self._event_spine.publish(
            preview_event_type,
            job_id=preview_job_id,
            source="manifest_gate_preview",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=preview_message,
            data={
                **common_data,
                "reasons": list(gate["reasons"]),
            },
        )
        self._archive_event_snapshot(
            reason="job_manifest_gate_preview",
            job_id=preview_job_id,
            extra={
                "variant": variant,
                "preview_only": True,
                "verdict": gate["verdict"],
            },
        )
        return {
            "status": "ok",
            "action": "preview",
            "preview_only": True,
            "job_id": preview_job_id,
            "event_type": preview_event_type,
            "message": preview_message,
            "checked_at": now_iso(),
            "gate": gate,
        }

    def get_crypto_status(self) -> dict[str, Any]:
        """从板卡 tcp_server 的 HTTP /status 端点获取 ML-KEM 通道状态。

        逻辑:
        1. toggle OFF → disabled
        2. 板卡未配置密码 → 提示先输入密码
        3. 请求板卡 :8080/status → 成功则缓存并返回
        4. 请求失败 → 保留上次正常值，只更新 error 字段
        """
        control_summary = self._control_plane_summary()
        _disabled = {
            "channel_state": "disabled",
            "kem_backend": "-",
            "cipher_suite": "-",
            "handshake_ms": None,
            "encrypt_ms": None,
            "decrypt_ms": None,
            "inference_ms": None,
            "bytes_sent": 0,
            "bytes_received": 0,
            "last_sha256_match": None,
            "session_count": 0,
            "last_session_at": None,
            "error": None,
            "enabled": False,
            "board_configured": False,
            **control_summary,
        }

        with self._lock:
            board_access = self._board_access
            if not self._crypto_enabled:
                bc = bool(board_access and board_access.connection_ready)
                return {**_disabled, "board_configured": bc, "batch_benchmark": None}
            cached = self._crypto_status_cache
            cache_ts = self._crypto_status_cache_ts
            if cached is not None and (time.monotonic() - cache_ts) < 1.5:
                batch = self._batch_state
                bm = batch.get("benchmark") if batch else None
                bs = batch.get("status") if batch else None
                bc_completed = batch.get("completed", 0) if batch else 0
                bc_total = batch.get("total", 0) if batch else 0
                return {
                    **cached,
                    "enabled": True,
                    **control_summary,
                    "batch_benchmark": bm,
                    "batch_status": bs,
                    "batch_completed": bc_completed,
                    "batch_total": bc_total,
                }

        board_configured = bool(board_access and board_access.connection_ready)

        if not board_configured:
            return {
                "channel_state": "disabled",
                "kem_backend": "-",
                "cipher_suite": "-",
                "handshake_ms": None,
                "encrypt_ms": None,
                "decrypt_ms": None,
                "inference_ms": None,
                "bytes_sent": 0,
                "bytes_received": 0,
                "last_sha256_match": None,
                "session_count": 0,
                "last_session_at": None,
                "error": "board_not_configured",
                "enabled": True,
                "board_configured": False,
                "batch_benchmark": None,
                "batch_status": None,
                "batch_completed": 0,
                "batch_total": 0,
                **control_summary,
            }

        host = board_access.host
        status_port = parse_int_config(
            first_config_value(board_access.env_values, keys=STATUS_PORT_KEYS),
            DEFAULT_STATUS_PORT,
        )
        url = f"http://{host}:{status_port}/status"

        try:
            data = fetch_json_direct(url, timeout=3)
            data["enabled"] = True
            data["board_configured"] = True
            data.update(control_summary)
            with self._lock:
                self._crypto_status_cache = data
                self._crypto_status_cache_ts = time.monotonic()
                batch = self._batch_state
            data["batch_benchmark"] = batch.get("benchmark") if batch else None
            data["batch_status"] = batch.get("status") if batch else None
            data["batch_completed"] = batch.get("completed", 0) if batch else 0
            data["batch_total"] = batch.get("total", 0) if batch else 0
            return data
        except (URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
            # 保留上次正常值，只更新 error
            with self._lock:
                prev = self._crypto_status_cache
                batch = self._batch_state
            if prev is not None:
                fallback = {
                    **prev,
                    "enabled": True,
                    "board_configured": True,
                    "error": f"board not reachable: {exc}",
                    "batch_benchmark": batch.get("benchmark") if batch else None,
                    "batch_status": batch.get("status") if batch else None,
                    "batch_completed": batch.get("completed", 0) if batch else 0,
                    "batch_total": batch.get("total", 0) if batch else 0,
                    **control_summary,
                }
                with self._lock:
                    self._crypto_status_cache = fallback
                    self._crypto_status_cache_ts = time.monotonic()
                return fallback
            # 从未成功获取过 → 返回带 error 的 idle
            cold: dict[str, Any] = {
                "channel_state": "idle",
                "kem_backend": "unknown",
                "cipher_suite": "unknown",
                "handshake_ms": None,
                "encrypt_ms": None,
                "decrypt_ms": None,
                "inference_ms": None,
                "bytes_sent": 0,
                "bytes_received": 0,
                "last_sha256_match": None,
                "session_count": 0,
                "last_session_at": None,
                "error": f"board not reachable: {exc}",
                "enabled": True,
                "board_configured": True,
                "batch_benchmark": None,
                "batch_status": None,
                "batch_completed": 0,
                "batch_total": 0,
                **control_summary,
            }
            with self._lock:
                self._crypto_status_cache = cold
                self._crypto_status_cache_ts = time.monotonic()
            return cold

    def _control_plane_summary(self) -> dict[str, Any]:
        with self._lock:
            control_status = dict(self._last_control_status or {})
            soft_recover = dict(self._last_soft_recover_result or {})
        event_summary = self._event_spine.summary(limit=1)
        aggregate = event_summary.get("aggregate") if isinstance(event_summary, dict) else {}
        event_counters = aggregate.get("event_counters") if isinstance(aggregate, dict) else {}
        if not isinstance(event_counters, dict):
            event_counters = {}

        heartbeat_ok_events = self._safe_int(event_counters.get("HEARTBEAT_OK"), default=0)
        heartbeat_lost_events = self._safe_int(event_counters.get("HEARTBEAT_LOST"), default=0)
        safe_stop_triggered_events = self._safe_int(event_counters.get("SAFE_STOP_TRIGGERED"), default=0)
        safe_stop_cleared_events = self._safe_int(event_counters.get("SAFE_STOP_CLEARED"), default=0)
        return {
            "control_guard_state": str(control_status.get("guard_state") or "UNKNOWN"),
            "control_last_fault_code": str(control_status.get("last_fault_code") or "UNKNOWN"),
            "control_heartbeat_ok": self._safe_int(control_status.get("heartbeat_ok"), default=0),
            "control_total_fault_count": self._safe_int(control_status.get("total_fault_count"), default=0),
            "control_job_req_count": self._safe_int(event_counters.get("JOB_SUBMITTED"), default=0),
            "control_job_admit_count": self._safe_int(event_counters.get("JOB_ADMITTED"), default=0),
            "control_job_reject_count": self._safe_int(event_counters.get("JOB_REJECTED"), default=0),
            "control_heartbeat_event_count": heartbeat_ok_events + heartbeat_lost_events,
            "control_heartbeat_lost_count": heartbeat_lost_events,
            "control_safe_stop_triggered_count": safe_stop_triggered_events,
            "control_safe_stop_cleared_count": safe_stop_cleared_events,
            "control_recover_attempted": bool(soft_recover),
            "control_recover_note": str(soft_recover.get("note") or ""),
        }

    def _maybe_soft_recover_control_plane(
        self,
        board_access: BoardAccessConfig,
        *,
        trusted_sha: str,
        reason: str,
    ) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            elapsed = now - self._last_soft_recover_ts
            cooldown = self._soft_recover_cooldown_sec
        if elapsed < cooldown:
            note = f"soft recover skipped by cooldown ({cooldown - elapsed:.1f}s left)"
            return {"attempted": False, "note": note}

        recover_result = run_recover_action(board_access, trusted_sha=trusted_sha)
        status_probe = query_live_status(board_access, trusted_sha=trusted_sha)
        attempted = {
            "attempted": True,
            "reason": reason,
            "recover_status": str(recover_result.get("status") or ""),
            "probe_status": str(status_probe.get("status") or ""),
            "note": "soft recover attempted before deciding to block",
        }
        with self._lock:
            self._last_soft_recover_ts = time.monotonic()
            self._last_soft_recover_result = attempted
            if recover_result.get("status") == "success":
                self._last_control_status = recover_result
            if status_probe.get("status") == "success":
                self._last_control_status = status_probe
        if status_probe.get("status") == "success":
            self._emit_status_observation_events(status_probe, source="soft_recover_retry")
        return {**attempted, "recover_result": recover_result, "status_retry": status_probe}

    def set_crypto_toggle(self, enabled: bool) -> dict[str, Any]:
        """设置 ML-KEM 开关状态

        当 enabled=True 时，自动通过 SSH 检测板卡 tcp_server 是否在运行，
        如果没有则自动启动（后台 nohup），这样用户不需要手动 SSH。
        """
        with self._lock:
            self._crypto_enabled = enabled
            board_access = self._board_access

        if enabled and board_access and board_access.connection_ready:
            import threading
            threading.Thread(
                target=self._ensure_board_tcp_server,
                args=(board_access,),
                daemon=True,
                name="tcp-server-toggle-start",
            ).start()

        return {"enabled": enabled}

    def _ensure_board_tcp_server(self, board_access: BoardAccessConfig) -> None:
        """通过 SSH 检测板卡 tcp_server 是否运行，如果没有则启动它。"""
        host = board_access.host
        user = board_access.user
        password = board_access.password
        ssh_port = board_access.port or "22"
        env_values = board_access.build_env()
        status_port = parse_int_config(
            first_config_value(env_values, keys=STATUS_PORT_KEYS),
            DEFAULT_STATUS_PORT,
        )

        # 1) 检测 status 端口是否响应，并验证密码套件是否匹配
        expected_suite = first_config_value(env_values, keys=SUITE_KEYS, default=DEFAULT_CIPHER_SUITE).lower().replace("_", "-")
        # AES_256_GCM → aes-256-gcm, SM4_GCM → sm4-gcm
        try:
            status = fetch_json_direct(f"http://{host}:{status_port}/status", timeout=2)
            running_suite = str(status.get("cipher_suite") or "").lower()
            if running_suite and running_suite == expected_suite:
                return  # 已在运行且套件匹配
            if running_suite and running_suite != expected_suite:
                print(f"[ML-KEM auto-start] 套件不匹配 (running={running_suite}, expected={expected_suite})，重启板端 tcp_server")
                # kill 旧进程
                run_ssh_command(
                    host=host, user=user, password=password, port=ssh_port,
                    remote_command="pkill -f 'tcp_server.py' || true",
                    timeout=8,
                )
                import time as _time; _time.sleep(1)
        except Exception:
            pass  # 没运行，继续启动

        # 1b) 若进程已在运行但 status 不通，等一下再试
        try:
            pgrep_proc = run_ssh_command(
                host=host,
                user=user,
                password=password,
                port=ssh_port,
                remote_command="pgrep -af 'tcp_server.py' || true",
                timeout=8,
            )
            if pgrep_proc.returncode == 0 and (pgrep_proc.stdout or "").strip():
                for _ in range(4):
                    try:
                        fetch_json_direct(f"http://{host}:{status_port}/status", timeout=2)
                        return
                    except Exception:
                        time.sleep(0.8)
        except Exception:
            pass

        # 2) SSH 到板卡启动 tcp_server
        local_server_script, _ = resolve_local_crypto_server(env_values)
        remote_command = build_remote_crypto_server_command(
            env_values,
            local_server_script=local_server_script,
        )

        try:
            proc = run_ssh_command(
                host=host,
                user=user,
                password=password,
                port=ssh_port,
                remote_command=remote_command,
                timeout=30,
            )
            if proc.returncode != 0:
                error_output = proc.stderr.strip() or proc.stdout.strip() or "unknown error"
                print(f"[ML-KEM auto-start] SSH failed: {error_output}")
                return
            for _ in range(6):
                try:
                    fetch_json_direct(f"http://{host}:{status_port}/status", timeout=2)
                    return
                except Exception:
                    time.sleep(0.8)
        except Exception as exc:
            print(f"[ML-KEM auto-start] error: {exc}")

    def run_crypto_test(self) -> dict[str, Any]:
        """通过 tcp_client.py 向板卡发送测试 latent，验证 ML-KEM 加密通道"""
        with self._lock:
            board_access = self._board_access
            if not self._crypto_enabled:
                return {"status": "error", "message": "ML-KEM not enabled"}

        if not (board_access and board_access.connection_ready):
            return {"status": "error", "message": "board not configured, please enter board password first"}

        host = board_access.host
        env_values = board_access.build_env()
        tcp_client, searched_paths = resolve_local_crypto_client(env_values)
        if tcp_client is None:
            searched_text = ", ".join(str(path) for path in searched_paths[:5]) or "no candidate paths"
            return {
                "status": "error",
                "message": "tcp_client.py not found; set MLKEM_CLIENT_SCRIPT/MLKEM_LOCAL_REPO_ROOT. "
                f"searched: {searched_text}",
            }

        # 生成测试 latent：优先使用 .bin，避免本机必须装 numpy。
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
        tmp.write(b"\0" * (1 * 32 * 32 * 32 * 4))
        tmp.close()
        tmp_path = Path(tmp.name)

        cmd, env = build_local_crypto_client_command(
            env_values,
            host=host,
            input_path=tmp_path,
            client_script=tcp_client,
        )

        # ── 尝试 daemon 模式（复用已有 session，省握手开销）──
        mgr = self._get_mlkem_session_manager(board_access, env_values)
        if mgr is not None:
            try:
                mgr.ensure_alive()
                t0 = time.monotonic()
                daemon_result = mgr.send_image(str(tmp_path), "crypto_test")
                wall_ms = round((time.monotonic() - t0) * 1000, 1)
                tmp_path.unlink()
                return {
                    "status": "ok" if daemon_result.get("status") == "ok" else "error",
                    "wall_ms": wall_ms,
                    "handshake_ms": round(mgr._handshake_ms, 1),
                    "sha256_match": daemon_result.get("sha256_match", False),
                    "transport_mode": "daemon",
                }
            except Exception:
                pass  # 回退到子进程模式

        # ── 子进程模式（原有逻辑）──
        try:
            t0 = time.monotonic()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            wall_ms = round((time.monotonic() - t0) * 1000, 1)
            try:
                tmp_path.unlink()
            except OSError:
                pass

            if proc.returncode != 0:
                return {
                    "status": "error",
                    "message": proc.stderr[-500:] if proc.stderr else "unknown error",
                    "wall_ms": wall_ms,
                }

            # 解析 stdout 中关键指标
            stdout = proc.stdout
            result: dict[str, Any] = {"status": "ok", "wall_ms": wall_ms}

            for line in stdout.splitlines():
                if "握手完成" in line:
                    # 提取耗时
                    m = re.search(r"([\d.]+)\s*ms", line)
                    if m:
                        result["handshake_ms"] = float(m.group(1))
                if "SHA256 匹配" in line or "对端 SHA256 匹配: 是" in line or "✓ 传输成功" in line:
                    result["sha256_match"] = True

            return result

        except subprocess.TimeoutExpired:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            return {"status": "error", "message": "timeout (30s)"}
        except Exception as exc:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            return {"status": "error", "message": str(exc)}

    def current_system_status(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
            board_access = self._board_access
            control_status = self._last_control_status
            last_inference = self._last_inference_result
            recent_inference_results = dict(self._recent_inference_results)
            last_fault = self._last_fault_result
            aircraft_position = self._aircraft_position

        snapshot = build_snapshot(live_probe=live_probe, aircraft_position=aircraft_position)
        aircraft_position_payload = snapshot["aircraft_position"]
        event_spine = self._event_spine.summary(limit=1)
        active_inference = self._active_inference_summary()
        current_board_access = self._live_board_access_for_variant(board_access, variant="current")
        baseline_board_access = self._live_board_access_for_variant(board_access, variant="baseline")
        admission = describe_demo_admission(current_board_access, variant="current")
        current_support = describe_demo_variant_support(current_board_access, variant="current")
        baseline_support = describe_demo_variant_support(baseline_board_access, variant="baseline")
        evidence_status = snapshot["board"]["evidence_status"]
        live_details = live_probe.get("details", {}) if live_probe else {}
        remoteproc_entries = live_details.get("remoteproc", [])
        remoteproc_state = (
            remoteproc_entries[0].get("state")
            if remoteproc_entries
            else evidence_status["transport"].get("remoteproc_state", "unknown")
        )
        rpmsg_devices = live_details.get("rpmsg_devices", [])
        rpmsg_device = rpmsg_devices[0] if rpmsg_devices else evidence_status["transport"].get("rpmsg_dev", "unknown")

        if control_status and control_status.get("status") == "success":
            guard_state = control_status.get("guard_state", "UNKNOWN")
            last_fault_code = control_status.get("last_fault_code", "UNKNOWN")
            active_job_id = control_status.get("active_job_id", 0)
            total_fault_count = control_status.get("total_fault_count", 0)
            status_source = "live_control"
            status_note = "已缓存最近一次 RPMsg 控制面读数。"
        else:
            fallback_timeout = evidence_status["timeout_ready_state"]
            guard_state = fallback_timeout.get("guard_state", "UNKNOWN")
            last_fault_code = fallback_timeout.get("last_fault", "UNKNOWN")
            active_job_id = fallback_timeout.get("active_job_id", 0)
            total_fault_count = fallback_timeout.get("total_fault_count", 0)
            status_source = "evidence"
            status_note = "当前 guard_state / fault_code 仍以正式证据包为准。"

        if str(guard_state or "").upper() == "JOB_ACTIVE":
            active_job_text = f" active_job_id={active_job_id}。" if active_job_id else ""
            status_note = (
                "板端当前 guard_state=JOB_ACTIVE；demo 会保守阻断新的 live launch，"
                f"不会自动 SAFE_STOP。{active_job_text}请等待现有作业完成，或由操作员手动 SAFE_STOP 后再重试。"
            )

        board_online = bool(live_probe and live_probe.get("reachable"))
        safety_panel = build_safety_panel(
            guard_state=str(guard_state or "UNKNOWN"),
            last_fault_code=str(last_fault_code or "UNKNOWN"),
            total_fault_count=self._safe_int(total_fault_count, default=0),
            board_online=board_online,
            status_source=status_source,
            status_note=status_note,
            last_fault=last_fault or None,
        )
        if board_online:
            mode_label = "在线模式"
            mode_tone = "online"
            mode_summary = "当前处于 3-core Linux + RTOS demo mode；板卡 SSH 与 RPMsg 控制面可用，第二幕会展示语义回传数据面的真实在线推进。"
        elif board_access.connection_ready:
            mode_label = "降级模式"
            mode_tone = "degraded"
            mode_summary = "本场会话已就绪；若真机链路暂不可用，界面会明确切回归档证据，不把 demo mode 数字混写成 4-core 性能口径。"
        elif board_access.has_preloaded_defaults and board_access.missing_connection_fields() == ["password"]:
            mode_label = "待补全密码"
            mode_tone = "degraded"
            mode_summary = "SSH 与推理默认值已预载；补一次密码即可触发真机动作。headline 性能仍以 4-core Linux performance mode 报告为准。"
        elif board_access.configured:
            mode_label = "待补全会话"
            mode_tone = "degraded"
            mode_summary = "已接入部分会话信息；补齐缺失字段后即可尝试真机动作。OpenAMP live 仅用于控制与安全演示。"
        else:
            mode_label = "离线模式"
            mode_tone = "offline"
            mode_summary = "尚未配置板卡会话，当前只展示证据与预录结果；headline 性能仍引用 4-core Linux performance mode 报告。"

        board_access_public = board_access.to_public_dict()
        live_payload = {
            "board_online": board_online,
            "remoteproc_state": remoteproc_state,
            "rpmsg_device": rpmsg_device,
            "guard_state": guard_state,
            "last_fault_code": last_fault_code,
            "active_job_id": active_job_id,
            "total_fault_count": total_fault_count,
            "trusted_sha": snapshot["project"]["trusted_current_sha"],
            "target": self._target_label,
            "runtime": self._runtime_label,
            "admission": admission,
            "variant_support": {
                "current": current_support,
                "baseline": baseline_support,
            },
            "last_probe_at": live_probe.get("requested_at", "") if live_probe else "",
            "status_source": status_source,
            "status_note": status_note,
        }
        event_spine_payload = {
            "api_path": "/api/event-spine",
            "session_id": event_spine["session_id"],
            "event_count": event_spine["aggregate"]["event_count"],
            "last_event_at": event_spine["aggregate"]["last_event_at"],
            "archive_enabled": event_spine["aggregate"]["archive"]["enabled"],
        }
        link_director = self.current_link_director_status()
        job_manifest_gate = self._job_manifest_gate_status(
            board_access=current_board_access,
            admission=admission,
            support=current_support,
            active_inference=active_inference,
            control_status=control_status,
            trusted_sha=self._trusted_current_sha,
            variant="current",
        )
        operator_cue = build_operator_cue(
            snapshot=snapshot,
            board_access=board_access_public,
            live=live_payload,
            active_inference=active_inference,
            last_inference=last_inference or {},
            safety_panel=safety_panel,
            gate=job_manifest_gate,
            link_director=link_director,
            event_spine=event_spine_payload,
        )

        return {
            "generated_at": snapshot["generated_at"],
            "board_access": board_access_public,
            "execution_mode": {
                "label": mode_label,
                "tone": mode_tone,
                "summary": mode_summary,
            },
            "aircraft_position": aircraft_position_payload,
            "live": live_payload,
            "active_inference": active_inference,
            "last_inference": last_inference or {},
            "recent_results": recent_inference_results,
            "last_fault": last_fault or {},
            "safety_panel": safety_panel,
            "job_manifest_gate": job_manifest_gate,
            "link_director": link_director,
            "operator_cue": operator_cue,
            "event_spine": event_spine_payload,
        }

    def current_event_spine(self, *, limit: int = 25) -> dict[str, Any]:
        return self._event_spine.summary(limit=limit)

    def list_archive_sessions(self, *, limit: int = 25) -> dict[str, Any]:
        return list_archive_sessions(
            self._event_archive_root,
            current_session_id=self._event_spine.session_id,
            limit=limit,
        )

    def current_archive_session(self, *, session_id: str = "", recent_limit: int = 25) -> dict[str, Any]:
        selected_session_id = str(session_id or "").strip()
        if not selected_session_id:
            sessions_payload = self.list_archive_sessions(limit=max(1, recent_limit))
            sessions = sessions_payload.get("sessions") if isinstance(sessions_payload.get("sessions"), list) else []
            if not sessions:
                raise ArchiveSessionNotFoundError("no archived sessions found")
            current_session_id = self._event_spine.session_id
            matching_current = next(
                (item for item in sessions if str(item.get("session_id") or "") == current_session_id),
                None,
            )
            selected_session_id = str(
                (matching_current or sessions[0]).get("session_id") or ""
            ).strip()
        return load_archive_session(
            self._event_archive_root,
            session_id=selected_session_id,
            recent_limit=recent_limit,
        )

    def _archive_event_snapshot(self, *, reason: str, job_id: str = "", extra: dict[str, Any] | None = None) -> None:
        self._event_spine.write_snapshot(reason=reason, job_id=job_id, extra=extra)

    def _emit_status_observation_events(self, payload: dict[str, Any], *, source: str, job_id: str = "") -> None:
        if payload.get("status") != "success":
            return
        heartbeat_ok = self._safe_int(payload.get("heartbeat_ok"), default=0)
        last_fault_code = str(payload.get("last_fault_code") or "").upper()
        if heartbeat_ok > 0:
            self._event_spine.publish(
                "HEARTBEAT_OK",
                job_id=job_id,
                source=source,
                plane="control",
                mode_scope=CONTROL_MODE_SCOPE,
                message="Heartbeat acknowledgement is healthy on the demo control path.",
                data={
                    "heartbeat_ok": heartbeat_ok,
                    "guard_state": str(payload.get("guard_state") or ""),
                    "last_fault_code": last_fault_code,
                },
            )
        if last_fault_code == "HEARTBEAT_TIMEOUT":
            self._event_spine.publish(
                "HEARTBEAT_LOST",
                job_id=job_id,
                source=source,
                plane="control",
                mode_scope=CONTROL_MODE_SCOPE,
                message="Heartbeat watchdog reported HEARTBEAT_TIMEOUT on the demo control path.",
                data={
                    "guard_state": str(payload.get("guard_state") or ""),
                    "last_fault_code": last_fault_code,
                },
            )

    def _emit_inference_rejection_events(
        self,
        *,
        variant: str,
        image_index: int,
        status_category: str,
        message: str,
        diagnostics: dict[str, Any],
    ) -> None:
        self._event_spine.publish(
            "JOB_SUBMITTED",
            source="inference",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=f"{variant} demo launch requested by the operator.",
            data={
                "variant": variant,
                "image_index": image_index,
                "status_category": status_category,
            },
        )
        self._event_spine.publish(
            "JOB_REJECTED",
            source="inference",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=message,
            data={
                "variant": variant,
                "image_index": image_index,
                "status_category": status_category,
                "diagnostics": diagnostics,
            },
        )
        self._archive_event_snapshot(
            reason="job_rejected",
            extra={
                "variant": variant,
                "image_index": image_index,
                "status_category": status_category,
            },
        )

    def _emit_job_event_once(
        self,
        record: dict[str, Any],
        event_type: str,
        *,
        source: str,
        plane: str,
        mode_scope: str,
        message: str,
        data: dict[str, Any],
    ) -> bool:
        event_marks = record.setdefault("event_marks", set())
        if event_type in event_marks:
            return False
        self._event_spine.publish(
            event_type,
            job_id=str(record.get("job_id") or ""),
            source=source,
            plane=plane,
            mode_scope=mode_scope,
            message=message,
            data=data,
        )
        event_marks.add(event_type)
        return True

    def _emit_inference_record_events(self, record: dict[str, Any], payload: dict[str, Any]) -> None:
        variant = str(record.get("variant") or "")
        job_id = str(record.get("job_id") or "")
        image_index = self._safe_int(record.get("image_index"), default=0)
        live_attempt = payload.get("live_attempt") if isinstance(payload.get("live_attempt"), dict) else {}
        control_transport = str(live_attempt.get("control_transport") or "hook").strip().lower()
        common_data = {
            "variant": variant,
            "image_index": image_index,
            "status": str(payload.get("status") or ""),
            "request_state": str(payload.get("request_state") or ""),
            "status_category": str(payload.get("status_category") or ""),
            "control_transport": control_transport or "hook",
        }
        self._emit_job_event_once(
            record,
            "JOB_SUBMITTED",
            source="inference",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=f"Live job {job_id} entered the demo submission spine.",
            data=common_data,
        )
        if payload.get("execution_mode") == "live" and control_transport != "none":
            self._emit_job_event_once(
                record,
                "JOB_ADMITTED",
                source="inference",
                plane="control",
                mode_scope=CONTROL_MODE_SCOPE,
                message=f"OpenAMP admitted live job {job_id}.",
                data=common_data,
            )
        if payload.get("execution_mode") == "live":
            self._emit_job_event_once(
                record,
                "JOB_STARTED",
                source="inference",
                plane="data",
                mode_scope=DATA_MODE_SCOPE,
                message=f"Reconstruction execution started for job {job_id}.",
                data=common_data,
            )
        if payload.get("request_state") != "completed":
            return
        if payload.get("status") == "success":
            self._emit_job_event_once(
                record,
                "FRAME_RECON_READY",
                source="inference",
                plane="data",
                mode_scope=DATA_MODE_SCOPE,
                message=f"Reconstruction output is ready for job {job_id}.",
                data={
                    **common_data,
                    "sample_label": str(payload.get("sample", {}).get("label") or ""),
                    "artifact_sha": str(payload.get("artifact_sha") or ""),
                },
            )
            done_emitted = self._emit_job_event_once(
                record,
                "JOB_DONE",
                source="inference",
                plane="data",
                mode_scope=DATA_MODE_SCOPE,
                message=f"Reconstruction job {job_id} completed.",
                data={
                    **common_data,
                    "artifact_sha": str(payload.get("artifact_sha") or ""),
                    "total_ms": payload.get("timings", {}).get("total_ms"),
                },
            )
            if done_emitted:
                self._archive_event_snapshot(
                    reason="job_done",
                    job_id=job_id,
                    extra={
                        "variant": variant,
                        "image_index": image_index,
                    },
                )
            return
        rejected_emitted = self._emit_job_event_once(
            record,
            "JOB_REJECTED",
            source="inference",
            plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=str(payload.get("message") or "Live job fallback captured in the demo spine."),
            data={
                **common_data,
                "execution_mode": str(payload.get("execution_mode") or ""),
            },
        )
        if rejected_emitted:
            self._archive_event_snapshot(
                reason="job_fallback",
                job_id=job_id,
                extra={
                    "variant": variant,
                    "image_index": image_index,
                    "status_category": str(payload.get("status_category") or ""),
                },
            )

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def refresh_live_probe(self) -> dict[str, Any]:
        with self._lock:
            board_access = self._board_access

        if board_access.probe_ready:
            result = run_live_probe(timeout_sec=self._probe_timeout_sec, env_values=board_access.build_env())
        else:
            result = run_live_probe(env_file=self._probe_env, timeout_sec=self._probe_timeout_sec)

        if is_successful_probe(result):
            with self._lock:
                self._last_live_probe = result
                if self._probe_cache_path:
                    write_probe_output(result, self._probe_cache_path)
            if board_access.probe_ready:
                current_board_access = self._live_board_access_for_variant(board_access, variant="current")
                status_payload = query_live_status(
                    board_access,
                    trusted_sha=expected_sha_for_variant(current_board_access, "current") or self._trusted_current_sha,
                )
                if status_payload.get("status") == "success":
                    with self._lock:
                        self._last_control_status = status_payload
                    self._emit_status_observation_events(status_payload, source="probe_status")
                result["control_status"] = status_payload
            self._archive_event_snapshot(
                reason="probe_refresh",
                extra={"requested_at": str(result.get("requested_at") or "")},
            )
        return result

    def _can_launch_runner_only_fallback(
        self,
        *,
        board_access,
        status_payload: dict[str, Any],
    ) -> bool:
        if not board_access.connection_ready:
            return False
        status_category = str(status_payload.get("status_category") or "")
        return status_category in {"timeout", "permission_error", "error"}

    def _build_inference_response(self, record: dict[str, Any], live_attempt: dict[str, Any]) -> dict[str, Any]:
        variant = str(record["variant"])
        image_index = int(record["image_index"])
        control_transport = str(live_attempt.get("control_transport") or "hook").strip().lower()
        runner_only_mode = control_transport == "none"
        payload = build_prerecorded_inference_result(image_index, variant)
        progress = live_attempt.get("progress", {})
        payload["job_id"] = record["job_id"]
        payload["request_state"] = live_attempt.get("request_state", "completed")
        payload["live_progress"] = progress

        if live_attempt.get("request_state") == "running":
            payload.update(
                {
                    "status": "running",
                    "execution_mode": "live",
                    "status_category": "running",
                    "source_label": "真实在线执行（控制面降级）" if runner_only_mode else "真实在线推进",
                    "message": (
                        live_attempt.get("message")
                        or (
                            "控制面预检未通过后已切到 SSH 兼容模式，界面正在同步板端执行进度。"
                            if runner_only_mode
                            else "OpenAMP 控制面已接入本次演示，界面正在同步板端推进阶段。"
                        )
                    ),
                    "timings": {
                        "payload_ms": None,
                        "prepare_ms": None,
                        "total_ms": None,
                        "stages": [],
                    },
                    "quality": payload["quality"],
                    "live_attempt": live_attempt,
                }
            )
            return payload

        if live_attempt.get("status") == "success":
            summary = live_attempt["runner_summary"]
            live_stages = [
                {
                    "label": "板端装载",
                    "value_ms": round(float(summary.get("load_ms") or 0.0), 3),
                    "emphasis": "host",
                },
                {
                    "label": "板端初始化",
                    "value_ms": round(float(summary.get("vm_init_ms") or 0.0), 3),
                    "emphasis": "board",
                },
                {
                    "label": "板端推理",
                    "value_ms": round(float(summary.get("run_median_ms") or summary.get("run_mean_ms") or 0.0), 3),
                    "emphasis": "total",
                },
            ]
            live_total_ms = round(sum(item["value_ms"] for item in live_stages), 3)
            payload.update(
                {
                    "status": "success",
                    "execution_mode": "live",
                    "status_category": "success",
                    "source_label": (
                        "真实在线执行（控制面降级） + 归档样例图"
                        if runner_only_mode
                        else "真实在线推进 + 归档样例图"
                    ),
                    "message": live_attempt.get("message")
                    or (
                        "本次演示已通过 OpenAMP 控制面完成作业下发、板端执行与结果回收；图像对比继续使用归档样例，"
                        "现场呈现更稳定。"
                        if not runner_only_mode
                        else (
                            "本次演示已在 SSH 兼容模式下完成真实板端执行；"
                            "图像对比继续使用归档样例，当前不宣称控制面握手已成功。"
                        )
                    ),
                    "timings": {
                        "payload_ms": round(float(summary.get("run_median_ms") or summary.get("run_mean_ms") or 0.0), 3),
                        "prepare_ms": round(float(summary.get("load_ms") or 0.0) + float(summary.get("vm_init_ms") or 0.0), 3),
                        "total_ms": live_total_ms,
                        "stages": live_stages,
                    },
                    "artifact_sha": summary.get("artifact_sha256") or payload["artifact_sha"],
                    "runner_summary": summary,
                    "wrapper_summary": live_attempt.get("wrapper_summary", {}),
                    "live_attempt": live_attempt,
                }
            )
            return payload

        payload.update(
            {
                "status": "fallback",
                "execution_mode": "prerecorded",
                "status_category": live_attempt.get("status_category", "fallback"),
                "source_label": (
                    "握手未完成，回退展示（归档样例）"
                    if live_attempt.get("control_handshake_complete") is False
                    else "回退展示（归档样例）"
                ),
                "message": (
                    f"{live_attempt.get('message', '在线推进未完成')}"
                    + (
                        " 当前画面仅显示归档样例与正式报告，不宣称本次 live 已完成。"
                        if live_attempt.get("control_handshake_complete") is False
                        else " 当前画面已切回归档样例，上方阶段条保留本次真机推进停留点。"
                    )
                ),
                "live_attempt": live_attempt,
            }
        )
        return payload

    def _update_last_inference_summary(self, payload: dict[str, Any], variant: str) -> None:
        cached_payload = json.loads(json.dumps(payload, ensure_ascii=False))
        self._last_inference_result = {
            "status": payload["status"],
            "execution_mode": payload["execution_mode"],
            "status_category": payload.get("status_category", "fallback"),
            "variant": variant,
            "total_ms": payload["timings"].get("total_ms"),
            "artifact_sha": payload["artifact_sha"],
            "message": payload["message"],
            "source_label": payload["source_label"],
            "sample_label": payload["sample"]["label"],
            "request_state": payload.get("request_state", "completed"),
        }
        self._recent_inference_results[variant] = cached_payload

    def _running_inference_job_record(self) -> dict[str, Any] | None:
        with self._lock:
            records = list(self._inference_jobs.values())
        for record in records:
            snapshot = record.get("last_snapshot")
            if not isinstance(snapshot, dict):
                snapshot = record["job"].snapshot()
                record["last_snapshot"] = snapshot
            if snapshot.get("request_state") == "running":
                return {
                    "job_id": record["job_id"],
                    "variant": record["variant"],
                    "snapshot": snapshot,
                }
        return None

    def _blocked_live_progress(
        self,
        *,
        label: str,
        detail: str,
        event_log: list[str] | None = None,
    ) -> dict[str, Any]:
        expected_count = DEFAULT_MAX_INPUTS
        return {
            "state": "completed",
            "label": label,
            "tone": "degraded",
            "percent": 0,
            "phase_percent": 100,
            "completed_count": 0,
            "expected_count": expected_count,
            "remaining_count": expected_count,
            "completion_ratio": 0.0,
            "count_source": "demo_default",
            "count_label": f"0 / {expected_count}",
            "current_stage": "未发起 live launch",
            "stages": [
                {
                    "key": "launch_guard",
                    "label": "启动前检查",
                    "status": "error",
                    "detail": detail,
                }
            ],
            "event_log": list(event_log or []),
        }

    def _build_blocked_inference_payload(
        self,
        *,
        variant: str,
        image_index: int,
        status_category: str,
        source_label: str,
        message: str,
        detail: str,
        diagnostics: dict[str, Any],
        event_log: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = self._build_prerecorded_payload_safe(image_index=image_index, variant=variant)
        payload.update(
            {
                "status": "fallback",
                "execution_mode": "prerecorded",
                "request_state": "completed",
                "status_category": status_category,
                "source_label": source_label,
                "message": message,
                "live_progress": self._blocked_live_progress(label=source_label, detail=detail, event_log=event_log),
                "live_attempt": {
                    "status": "blocked",
                    "request_state": "completed",
                    "status_category": status_category,
                    "message": message,
                    "diagnostics": diagnostics,
                },
            }
        )
        return payload

    def _build_prerecorded_payload_safe(self, *, image_index: int, variant: str) -> dict[str, Any]:
        """Return a prerecorded payload template, tolerating out-of-range indices.

        Batch live runs can request many indices (e.g. 0..299), while prerecorded
        assets are a smaller fixed subset. For live path accounting, we keep the
        requested index and reuse a stable template when index is out of range.
        """
        try:
            payload = build_prerecorded_inference_result(image_index, variant)
        except IndexError:
            payload = build_prerecorded_inference_result(0, variant)
            payload["message"] = (
                f"image_index={image_index} 超出预录样例范围，已复用 index=0 模板承载本次 live 结果。"
            )
        payload["image_index"] = image_index
        return payload

    def _parse_mlkem_client_metrics(self, stdout: str) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "handshake_ms": None,
            "encrypt_ms": None,
            "decrypt_ms": None,
            "inference_ms": None,
            "result_recv_ms": None,
            "sha256_match": None,
            "suite": "",
            "backend": "",
        }
        for line in stdout.splitlines():
            text = str(line).strip()
            if not text:
                continue
            if text.startswith("密码套件:"):
                metrics["suite"] = text.split(":", 1)[1].strip()
            elif text.startswith("KEM 后端:"):
                metrics["backend"] = text.split(":", 1)[1].strip()
            elif "握手完成" in text:
                m = re.search(r"([\d.]+)\s*ms", text)
                if m:
                    metrics["handshake_ms"] = float(m.group(1))
            elif "加密发送" in text:
                m = re.search(r"耗时\s*([\d.]+)\s*ms", text)
                if m:
                    metrics["encrypt_ms"] = float(m.group(1))
            elif "接收重建结果" in text:
                m = re.search(r"耗时\s*([\d.]+)\s*ms", text)
                if m:
                    metrics["result_recv_ms"] = float(m.group(1))
                    metrics["decrypt_ms"] = metrics["result_recv_ms"]
            elif "TVM 推理耗时" in text:
                m = re.search(r"([\d.]+)\s*ms", text)
                if m:
                    metrics["inference_ms"] = float(m.group(1))
            elif "对端 SHA256 匹配: 是" in text or "SHA256 匹配" in text:
                metrics["sha256_match"] = True
            elif "SHA256 不匹配" in text:
                metrics["sha256_match"] = False
        return metrics

    # ── 批量推理 ──────────────────────────────────────────────────────────────

    def get_batch_state(self) -> dict[str, Any]:
        with self._lock:
            state = self._batch_state
        if state is None:
            return {"status": "idle"}
        return dict(state)

    def start_batch_inference(self, *, count: int = 300, allow_preflight_degraded: bool = True) -> dict[str, Any]:
        """在后台线程启动批量 ML-KEM 加密推理，返回 batch_job_id。"""
        import threading

        with self._lock:
            existing = self._batch_state
            if existing and existing.get("status") == "running":
                return {"status": "already_running", "batch_job_id": existing.get("batch_job_id")}
            batch_job_id = f"batch-{int(time.time())}-{count}"
            self._batch_state = {
                "status": "running",
                "batch_job_id": batch_job_id,
                "total": count,
                "completed": 0,
                "success": 0,
                "fallback": 0,
                "sha_match": 0,
                "started_at": time.time(),
                "finished_at": None,
                # 各阶段计时样本列表（仅 live success 时记录）
                "_samples": {
                    "handshake_ms": [],
                    "encrypt_ms": [],
                    "decrypt_ms": [],
                    "inference_ms": [],
                    "total_ms": [],
                },
                "benchmark": None,
            }

        def _worker() -> None:
            for i in range(count):
                result = self.run_mlkem_inference(
                    variant="current",
                    image_index=i,
                    allow_preflight_degraded=allow_preflight_degraded,
                )
                with self._lock:
                    state = self._batch_state
                    if state is None or state.get("status") != "running":
                        break
                    state["completed"] += 1
                    is_live = result.get("execution_mode") == "live" and result.get("status") == "success"
                    if is_live:
                        state["success"] += 1
                    else:
                        state["fallback"] += 1
                    if result.get("live_attempt", {}).get("metrics", {}).get("sha256_match"):
                        state["sha_match"] += 1
                    if is_live:
                        m = result.get("live_attempt", {}).get("metrics", {})
                        t = result.get("timings", {})
                        samples = state["_samples"]
                        for key in ("handshake_ms", "encrypt_ms", "decrypt_ms", "inference_ms"):
                            v = m.get(key)
                            if v is not None:
                                samples[key].append(float(v))
                        total = t.get("total_ms")
                        if total is not None:
                            samples["total_ms"].append(float(total))

            with self._lock:
                state = self._batch_state
                if state is None:
                    return
                state["status"] = "done"
                state["finished_at"] = time.time()
                state["benchmark"] = _compute_benchmark(state["_samples"])

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return {"status": "started", "batch_job_id": batch_job_id, "total": count}

    def run_mlkem_inference(
        self,
        *,
        variant: str,
        image_index: int,
        allow_preflight_degraded: bool = False,
    ) -> dict[str, Any]:
        payload = self._build_prerecorded_payload_safe(image_index=image_index, variant=variant)
        with self._lock:
            board_access = self._board_access
            crypto_enabled = self._crypto_enabled

        if not crypto_enabled:
            return self._build_blocked_inference_payload(
                variant=variant,
                image_index=image_index,
                status_category="crypto_disabled",
                source_label="ML-KEM 未启用，回退展示（归档样例）",
                message="当前 ML-KEM 开关为 OFF，本次不发起加密推理。",
                detail="启用安全信道后，Current 主路径才会走 ML-KEM 加密通道。",
                diagnostics={"crypto_enabled": False},
            )

        if not (board_access and board_access.connection_ready):
            return self._build_blocked_inference_payload(
                variant=variant,
                image_index=image_index,
                status_category="config_error",
                source_label="会话未配置，回退展示（归档样例）",
                message="尚未录入完整板卡会话，无法发起 ML-KEM 推理。",
                detail="请先补齐 host/user/password。",
                diagnostics={"board_configured": False},
            )

        # ── Preflight：daemon 存活时跳过 SSH 查询（O-1 优化） ──
        env_values = board_access.build_env()
        mgr_early = self._get_mlkem_session_manager(board_access, env_values)
        daemon_alive = mgr_early is not None and mgr_early.is_alive

        if daemon_alive:
            # daemon 已与板端建立 ML-KEM 会话，板卡 TCP 通道畅通，无需 SSH 预检
            with self._lock:
                preflight = self._last_control_status
            if not preflight or preflight.get("status") not in ("success", "degraded"):
                preflight = {
                    "status": "degraded",
                    "message": "daemon 存活，跳过 SSH preflight",
                    "logs": [],
                    "guard_state": "UNKNOWN",
                    "last_fault_code": "NONE",
                    "heartbeat_ok": 1,
                    "total_fault_count": 0,
                    "status_category": "daemon_skip_preflight",
                }
        else:
            # daemon 未启动，走完整 SSH + RPMsg 预检
            live_board_access = self._live_board_access_for_variant(board_access, variant=variant)
            variant_expected_sha = expected_sha_for_variant(live_board_access, variant) or self._trusted_current_sha
            preflight = query_live_status(board_access, trusted_sha=variant_expected_sha)
            if preflight.get("status") != "success":
                soft_recover = self._maybe_soft_recover_control_plane(
                    board_access,
                    trusted_sha=variant_expected_sha,
                    reason="mlkem_preflight_failed",
                )
                retry = soft_recover.get("status_retry") if isinstance(soft_recover.get("status_retry"), dict) else {}
                if retry.get("status") == "success":
                    preflight = retry
                else:
                    if allow_preflight_degraded:
                        preflight = {
                            "status": "degraded",
                            "message": str(preflight.get("message") or "control preflight timeout"),
                            "logs": list(preflight.get("logs") or []),
                            "guard_state": "UNKNOWN",
                            "last_fault_code": "UNKNOWN",
                            "heartbeat_ok": 0,
                            "total_fault_count": 0,
                            "status_category": "control_preflight_degraded",
                        }
                    else:
                        return self._build_blocked_inference_payload(
                            variant=variant,
                            image_index=image_index,
                            status_category="control_preflight_failed",
                            source_label="控制面预检失败，回退展示（归档样例）",
                            message="控制面 STATUS_REQ 预检失败，本次不继续 ML-KEM 推理。",
                            detail=str(preflight.get("message") or "未拿到有效 STATUS_RESP"),
                            diagnostics={"control_status": preflight, "soft_recover": soft_recover},
                            event_log=list(preflight.get("logs") or []),
                        )

        with self._lock:
            self._last_control_status = preflight
        self._emit_status_observation_events(preflight, source="mlkem_preflight")

        guard_state = str(preflight.get("guard_state") or "UNKNOWN").upper()
        if guard_state == "JOB_ACTIVE":
            active_job_id = int(preflight.get("active_job_id") or 0)
            active_suffix = f" active_job_id={active_job_id}。" if active_job_id else ""
            return self._build_blocked_inference_payload(
                variant=variant,
                image_index=image_index,
                status_category="board_busy",
                source_label="保守阻断（板端已有活动作业）",
                message=(
                    "板端当前 guard_state=JOB_ACTIVE，本次 ML-KEM 推理已保守阻断；"
                    f"不会自动 SAFE_STOP。{active_suffix}"
                ),
                detail="STATUS_RESP 显示 guard_state=JOB_ACTIVE；未再发起新的加密推理。",
                diagnostics={"control_status": preflight},
                event_log=list(preflight.get("logs") or []),
            )

        # env_values 已在上方 O-1 优化块中提前获取
        self._ensure_board_tcp_server(board_access)
        # O-3: 复用 mgr_early 的 client_script，避免重复文件系统搜索
        if mgr_early is not None:
            tcp_client = mgr_early._client_script
            searched_paths = [tcp_client]
        else:
            tcp_client, searched_paths = resolve_local_crypto_client(env_values)
        if tcp_client is None:
            searched_text = ", ".join(str(path) for path in searched_paths[:5]) or "no candidate paths"
            return self._build_blocked_inference_payload(
                variant=variant,
                image_index=image_index,
                status_category="client_missing",
                source_label="客户端缺失，回退展示（归档样例）",
                message="tcp_client.py 未找到，无法执行 ML-KEM 推理主路径。",
                detail=f"searched: {searched_text}",
                diagnostics={"searched": searched_paths[:10]},
            )

        import tempfile
        from threading import Thread

        # ── 构建 ML-KEM 后台 job（和 SSH 路径一样：返回 running，后台推进） ──
        mlkem_job_id = generate_live_job_id()
        max_inputs = DEFAULT_MAX_INPUTS

        class _MlkemJob:
            """模拟 LiveRemoteReconstructionJob：后台线程逐张 ML-KEM 推理，前端轮询进度。"""
            def __init__(self_self, jid: str, max_n: int, board: Any, env_vals: dict,
                         client_script: str, variant_name: str, img_idx: int,
                         preflight_data: dict, app_state: Any,
                         session_mgr: "MlkemSessionManager | None" = None):
                self_self.job_id = jid
                self_self._max = max_n
                self_self._board = board
                self_self._env_vals = env_vals
                self_self._client = client_script
                self_self._variant = variant_name
                self_self._img_idx = img_idx
                self_self._preflight = preflight_data
                self_self._app = app_state
                self_self._session_mgr = session_mgr
                self_self._lock = Lock()
                self_self._completed = 0
                self_self._final_snapshot: dict[str, Any] | None = None
                self_self._stages_summary: list[dict[str, Any]] = []
                self_self._total_ms = 0.0
                self_self._sha_match: bool | None = None
                self_self._error: str | None = None

            def snapshot(self_self) -> dict:
                with self_self._lock:
                    if self_self._final_snapshot is not None:
                        return dict(self_self._final_snapshot)
                completed = self_self._completed
                pct = int(round(completed / self_self._max * 100)) if self_self._max > 0 else 0
                return {
                    "status": "running",
                    "request_state": "running",
                    "status_category": "running",
                    "execution_mode": "live",
                    "variant": self_self._variant,
                    "message": "ML-KEM 安全信道在线推进中…",
                    "control_transport": "mlkem",
                    "control_handshake_complete": True,
                    "runner_summary": {"processed_count": completed, "input_count": self_self._max, "max_inputs": self_self._max},
                    "wrapper_summary": {},
                    "diagnostics": {"control_preflight": self_self._preflight},
                    "progress": {
                        "state": "running",
                        "label": "ML-KEM 加密推理中",
                        "tone": "online",
                        "percent": pct,
                        "phase_percent": pct,
                        "completed_count": completed,
                        "expected_count": self_self._max,
                        "remaining_count": self_self._max - completed,
                        "completion_ratio": round(completed / self_self._max, 4) if self_self._max > 0 else 0.0,
                        "count_source": "mlkem_live",
                        "count_label": f"{completed} / {self_self._max}",
                        "current_stage": f"ML-KEM 加密推理 {completed}/{self_self._max}",
                        "stages": [{"key": "mlkem_live", "label": "ML-KEM 全链路", "status": "current",
                                     "detail": f"已完成 {completed}/{self_self._max}"}],
                        "event_log": [],
                    },
                    "artifacts": [],
                }

            def start(self_self) -> None:
                Thread(target=self_self._run_loop, daemon=True).start()

            def _run_loop(self_self) -> None:
                tmp_in = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
                tmp_in.write(b"\0" * (1 * 32 * 32 * 32 * 4))
                tmp_in.close()
                input_path = Path(tmp_in.name)
                try:
                    if self_self._session_mgr is not None:
                        self_self._run_loop_daemon(input_path)
                    else:
                        self_self._run_loop_subprocess(input_path)
                finally:
                    try:
                        input_path.unlink()
                    except OSError:
                        pass

            def _run_loop_daemon(self_self, input_path: Path) -> None:
                """通过持久化 daemon 发送图片（一次握手 N 张复用）"""
                mgr = self_self._session_mgr
                assert mgr is not None

                try:
                    mgr.ensure_alive()
                except Exception as e:
                    print(f"[ML-KEM _run_loop] daemon 启动失败, 回退子进程: {e}")
                    self_self._run_loop_subprocess(input_path)
                    return

                t0 = time.monotonic()
                for i in range(self_self._max):
                    job_id = f"{self_self.job_id}_{i:04d}"
                    try:
                        result = mgr.send_image(str(input_path), job_id)
                    except Exception as e:
                        print(f"[ML-KEM _run_loop] daemon 错误 (第 {i} 张): {e}")
                        # 回退：剩余图片用子进程
                        remaining = self_self._max - i
                        if remaining > 0:
                            self_self._run_loop_subprocess(input_path, remaining=remaining)
                        return

                    if result.get("status") == "ok":
                        with self_self._lock:
                            self_self._completed += 1
                            self_self._total_ms = (time.monotonic() - t0) * 1000
                    else:
                        print(f"[ML-KEM _run_loop] 第 {i} 张失败: {result}")
                        with self_self._lock:
                            self_self._error = f"第 {i} 张失败: {result.get('message', '')}"

                total_wall = (time.monotonic() - t0) * 1000
                with self_self._lock:
                    self_self._sha_match = (self_self._completed == self_self._max)
                    is_ok = self_self._completed == self_self._max and self_self._error is None
                    per_image_ms = total_wall / max(self_self._max, 1)
                    self_self._final_snapshot = {
                        "status": "success" if is_ok else "fallback",
                        "request_state": "completed",
                        "status_category": "success" if is_ok else "fallback",
                        "execution_mode": "live" if is_ok else "fallback",
                        "variant": self_self._variant,
                        "message": (
                            "Current 已通过 ML-KEM 安全信道完成加密传输与板端执行。"
                            if is_ok
                            else f"ML-KEM 推理中断（已完成 {self_self._completed}/{self_self._max}），已回退。"
                        ),
                        "control_transport": "mlkem",
                        "control_handshake_complete": True,
                        "runner_summary": {
                            "processed_count": self_self._completed,
                            "input_count": self_self._max,
                            "max_inputs": self_self._max,
                            "total_ms": round(total_wall, 3),
                        },
                        "wrapper_summary": {
                            "total_ms": round(total_wall, 3),
                            "sha_match": self_self._sha_match,
                            "handshake_ms": mgr._handshake_ms,
                            "per_image_ms": round(per_image_ms, 1),
                            "transport_mode": "daemon",
                        },
                        "diagnostics": {"control_preflight": self_self._preflight},
                        "progress": {
                            "state": "completed" if is_ok else "fallback",
                            "label": "ML-KEM 加密推理完成" if is_ok else "ML-KEM 推理中断",
                            "tone": "online" if is_ok else "degraded",
                            "percent": 100 if is_ok else int(round(self_self._completed / self_self._max * 100)),
                            "phase_percent": 100,
                            "completed_count": self_self._completed,
                            "expected_count": self_self._max,
                            "remaining_count": self_self._max - self_self._completed,
                            "completion_ratio": round(self_self._completed / self_self._max, 4) if self_self._max > 0 else 0.0,
                            "count_source": "mlkem_live",
                            "count_label": f"{self_self._completed} / {self_self._max}",
                            "current_stage": "加密推理完成" if is_ok else "推理中断",
                            "stages": [{"key": "mlkem_live_done", "label": "ML-KEM 全链路", "status": "done" if is_ok else "error",
                                         "detail": f"wall={round(total_wall, 1)}ms, sha_match={self_self._sha_match}"}],
                            "event_log": [] if is_ok else [f"error: {self_self._error}"],
                        },
                        "artifacts": [],
                    }
                    self_self._app._event_spine.publish("JOB_DONE", source="inference", plane="data",
                        mode_scope=DATA_MODE_SCOPE,
                        message=f"ML-KEM live job {self_self.job_id} completed (daemon).",
                        data={"variant": self_self._variant, "image_index": self_self._img_idx,
                              "total_ms": round(total_wall, 3), "sha256_match": self_self._sha_match,
                              "control_transport": "mlkem"})

            def _run_loop_subprocess(self_self, input_path: Path,
                                     remaining: int | None = None) -> None:
                """通过一次性子进程发送图片（原有逻辑，回退路径）"""
                count = remaining if remaining is not None else self_self._max
                cmd, env = build_local_crypto_client_command(
                    self_self._env_vals, host=self_self._board.host,
                    input_path=input_path, client_script=self_self._client,
                )
                cmd.extend([
                    "--job-id", self_self.job_id,
                    "--count", str(count),
                    "--json-summary",
                ])
                env["PYTHONUNBUFFERED"] = "1"
                timeout_s = count * 10
                t0 = time.monotonic()
                stdout_lines: list[str] = []
                print(f"[ML-KEM _run_loop_subprocess] cmd={' '.join(cmd[:8])}...")
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, env=env, bufsize=1)
                    assert proc.stdout is not None
                    for raw_line in proc.stdout:
                        line = raw_line.rstrip('\n')
                        stdout_lines.append(line)
                        if "✓" in line:
                            with self_self._lock:
                                self_self._completed += 1
                                self_self._total_ms = (time.monotonic() - t0) * 1000
                    proc.wait(timeout=timeout_s - (time.monotonic() - t0))
                except subprocess.TimeoutExpired:
                    print(f"[ML-KEM _run_loop_subprocess] TIMEOUT after {timeout_s}s")
                    with self_self._lock:
                        self_self._error = "ML-KEM 批量传输超时"
                    return
                except Exception as e:
                    print(f"[ML-KEM _run_loop_subprocess] EXCEPTION: {e}")
                    with self_self._lock:
                        self_self._error = f"ML-KEM 进程异常: {e}"
                    return
                total_wall = (time.monotonic() - t0) * 1000
                stdout_full = '\n'.join(stdout_lines)

                if proc.returncode != 0:
                    stderr = (proc.stderr.read() if proc.stderr else "")[-300:]
                    with self_self._lock:
                        self_self._error = f"ML-KEM 批量失败 (rc={proc.returncode}): {stderr.strip()}"
                    print(f"[ML-KEM _run_loop_subprocess] FAIL rc={proc.returncode}: {stderr.strip()[:200]}")
                    return

                print(f"[ML-KEM _run_loop_subprocess] done rc=0, {len(stdout_lines)} lines, {total_wall:.0f}ms")

                summary = _MlkemJob._parse_json_summary(stdout_full)
                success = summary.get("success", self_self._completed)
                total = summary.get("total", count)
                handshake_ms = summary.get("handshake_ms", 0)
                per_image_ms = summary.get("per_image_ms", 0)

                with self_self._lock:
                    self_self._completed = success
                    self_self._total_ms = total_wall
                    self_self._stages_summary = [
                        {"label": "ML-KEM 握手 (1 次)", "value_ms": handshake_ms, "emphasis": "host"},
                        {"label": "AEAD 加密传输 (N 张)", "value_ms": round(per_image_ms * total, 1), "emphasis": "data"},
                    ]
                    self_self._sha_match = (success == total)
                    is_ok = self_self._completed == self_self._max and self_self._error is None
                    self_self._final_snapshot = {
                        "status": "success" if is_ok else "fallback",
                        "request_state": "completed",
                        "status_category": "success" if is_ok else "fallback",
                        "execution_mode": "live" if is_ok else "fallback",
                        "variant": self_self._variant,
                        "message": (
                            "Current 已通过 ML-KEM 安全信道完成 300 张加密传输与板端执行。"
                            if is_ok
                            else f"ML-KEM 推理中断（已完成 {self_self._completed}/{self_self._max}），已回退。"
                        ),
                        "control_transport": "mlkem",
                        "control_handshake_complete": True,
                        "runner_summary": {
                            "processed_count": self_self._completed,
                            "input_count": self_self._max,
                            "max_inputs": self_self._max,
                            "total_ms": round(total_wall, 3),
                        },
                        "wrapper_summary": {
                            "total_ms": round(total_wall, 3),
                            "sha_match": self_self._sha_match,
                            "handshake_ms": handshake_ms,
                            "per_image_ms": per_image_ms,
                        },
                        "diagnostics": {"control_preflight": self_self._preflight},
                        "progress": {
                            "state": "completed" if is_ok else "fallback",
                            "label": "ML-KEM 加密推理完成" if is_ok else "ML-KEM 推理中断",
                            "tone": "online" if is_ok else "degraded",
                            "percent": 100 if is_ok else int(round(self_self._completed / self_self._max * 100)),
                            "phase_percent": 100,
                            "completed_count": self_self._completed,
                            "expected_count": self_self._max,
                            "remaining_count": self_self._max - self_self._completed,
                            "completion_ratio": round(self_self._completed / self_self._max, 4) if self_self._max > 0 else 0.0,
                            "count_source": "mlkem_live",
                            "count_label": f"{self_self._completed} / {self_self._max}",
                            "current_stage": "加密推理完成" if is_ok else "推理中断",
                            "stages": [{"key": "mlkem_live_done", "label": "ML-KEM 全链路", "status": "done" if is_ok else "error",
                                         "detail": f"wall={round(total_wall, 1)}ms, sha_match={self_self._sha_match}"}],
                            "event_log": [] if is_ok else [f"error: {self_self._error}"],
                        },
                        "artifacts": [],
                    }
                    self_self._app._event_spine.publish("JOB_DONE", source="inference", plane="data",
                        mode_scope=DATA_MODE_SCOPE,
                        message=f"ML-KEM live job {self_self.job_id} completed.",
                        data={"variant": self_self._variant, "image_index": self_self._img_idx,
                              "total_ms": round(total_wall, 3), "sha256_match": self_self._sha_match,
                              "control_transport": "mlkem"})
                    self_self._app._archive_event_snapshot(
                        reason="mlkem_live_done", job_id=self_self.job_id,
                        extra={"variant": self_self._variant, "completed": self_self._completed,
                              "total_ms": round(total_wall, 3)})

            @staticmethod
            def _parse_json_summary(stdout: str) -> dict[str, Any]:
                """解析 tcp_client.py --json-summary 输出的 JSON"""
                # JSON 摘要在 stdout 末尾，找到最后一个 '{' 开始的行
                lines = stdout.splitlines()
                json_start = -1
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('{') or stripped.startswith('['):
                        json_start = i
                if json_start < 0:
                    return {}
                try:
                    return json.loads('\n'.join(lines[json_start:]))
                except (json.JSONDecodeError, ValueError):
                    return {}

            @staticmethod
            def _parse_stdout(stdout: str) -> dict[str, Any]:
                metrics: dict[str, Any] = {}
                for line in stdout.splitlines():
                    text = line.strip()
                    if "握手完成" in text:
                        m = re.search(r"([\d.]+)\s*ms", text)
                        if m:
                            metrics.setdefault("stages", []).append(
                                {"label": "ML-KEM 握手", "value_ms": round(float(m.group(1)), 3), "emphasis": "host"})
                    elif "加密发送" in text:
                        m = re.search(r"([\d.]+)\s*ms", text)
                        if m:
                            metrics.setdefault("stages", []).append(
                                {"label": "AEAD 加密发送", "value_ms": round(float(m.group(1)), 3), "emphasis": "data"})
                    elif "TVM 推理" in text or "解密结果" in text:
                        m = re.search(r"([\d.]+)\s*ms", text)
                        if m:
                            metrics.setdefault("stages", []).append(
                                {"label": "板端 TVM 推理", "value_ms": round(float(m.group(1)), 3), "emphasis": "board"})
                    elif "SHA256 匹配" in text or "sha256" in text.lower():
                        if "不匹配" not in text and "mismatch" not in text.lower():
                            metrics["sha_match"] = True
                return metrics

        mgr = self._get_mlkem_session_manager(board_access, env_values)
        mlkem_job = _MlkemJob(
            jid=mlkem_job_id, max_n=max_inputs, board=board_access,
            env_vals=env_values, client_script=tcp_client, variant_name=variant,
            img_idx=image_index, preflight_data=preflight, app_state=self,
            session_mgr=mgr,
        )

        # 初始 "running" snapshot → 通过 _build_inference_response 生成 payload
        running_snapshot = mlkem_job.snapshot()
        record = {
            "job": mlkem_job,
            "job_id": mlkem_job_id,
            "variant": variant,
            "image_index": image_index,
            "last_snapshot": dict(running_snapshot),
        }
        with self._lock:
            self._inference_jobs[mlkem_job_id] = record

        payload = self._build_inference_response(record, running_snapshot)
        payload["source_label"] = "ML-KEM 全链路加密（控制+数据）"

        # 启动后台推理线程
        mlkem_job.start()

        self._event_spine.publish(
            "JOB_SUBMITTED", source="inference", plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=f"ML-KEM live job {mlkem_job_id} submitted (300 images).",
            data={"variant": variant, "image_index": image_index, "control_transport": "mlkem"},
        )
        self._event_spine.publish(
            "JOB_ADMITTED", source="inference", plane="control",
            mode_scope=CONTROL_MODE_SCOPE,
            message=f"ML-KEM live job {mlkem_job_id} admitted.",
            data={"variant": variant, "image_index": image_index, "control_transport": "mlkem"},
        )

        return payload

    def run_demo_inference(
        self,
        *,
        variant: str,
        image_index: int,
        allow_preflight_degraded: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            crypto_enabled = self._crypto_enabled
        if crypto_enabled and variant == "current":
            return self.run_mlkem_inference(
                variant=variant,
                image_index=image_index,
                allow_preflight_degraded=allow_preflight_degraded,
            )

        payload = self._build_prerecorded_payload_safe(image_index=image_index, variant=variant)
        event_record: dict[str, Any] | None = None
        with self._lock:
            board_access = self._board_access
            last_live_probe = self._last_live_probe
        live_board_access = self._live_board_access_for_variant(board_access, variant=variant)
        variant_expected_sha = expected_sha_for_variant(live_board_access, variant) or self._trusted_current_sha
        variant_support = describe_demo_variant_support(live_board_access, variant=variant)

        if board_access.configured:
            active_record = self._running_inference_job_record()
            if active_record is not None:
                active_variant = str(active_record["variant"])
                active_job_id = str(active_record["job_id"])
                message = (
                    f"当前 demo 已有 live 作业在跑（job_id={active_job_id}，variant={active_variant}）；"
                    "为避免板端落入 DUPLICATE_JOB_ID / JOB_ACTIVE，已保守阻断新的 launch。"
                )
                payload = self._build_blocked_inference_payload(
                    variant=variant,
                    image_index=image_index,
                    status_category="board_busy",
                    source_label="保守阻断（已有 live 作业）",
                    message=message,
                    detail="当前 demo 进程内已有 live 作业尚未完成。",
                    diagnostics={
                        "running_job_id": active_job_id,
                        "running_variant": active_variant,
                    },
                    event_log=[message],
                )
            elif board_access.probe_ready:
                status_payload = query_live_status(board_access, trusted_sha=variant_expected_sha)
                if status_payload.get("status") == "success":
                    with self._lock:
                        self._last_control_status = status_payload
                    self._emit_status_observation_events(status_payload, source="status_preflight")
                    guard_state = str(status_payload.get("guard_state") or "UNKNOWN").upper()
                    if guard_state == "JOB_ACTIVE":
                        active_job_id = int(status_payload.get("active_job_id") or 0)
                        active_suffix = f" active_job_id={active_job_id}。" if active_job_id else ""
                        message_prefix = ""
                        if variant == "current" and variant_support.get("mode") == "signed_manifest_v1":
                            message_prefix = "Current signed-admission live path 已支持，但"
                        message = (
                            f"{message_prefix}板端当前 guard_state=JOB_ACTIVE，"
                            "本次 launch 已被保守阻断，demo 不会自动 SAFE_STOP。"
                            f"{active_suffix}请等待现有作业完成，或由操作员手动 SAFE_STOP 后再重试。"
                        )
                        payload = self._build_blocked_inference_payload(
                            variant=variant,
                            image_index=image_index,
                            status_category="board_busy",
                            source_label="保守阻断（板端已有活动作业）",
                            message=message,
                            detail="STATUS_RESP 显示 guard_state=JOB_ACTIVE；未再发起新的 live launch。",
                            diagnostics={"board_status": status_payload},
                            event_log=status_payload.get("logs", []),
                        )
                else:
                    status_category = str(status_payload.get("status_category") or "error")
                    preflight_message = str(status_payload.get("message") or "").strip()
                    firmware_sha = (
                        str(last_live_probe.get("details", {}).get("firmware", {}).get("sha256", ""))
                        if isinstance(last_live_probe, dict)
                        else ""
                    )
                    firmware_hint = f" 最近只读探板 firmware={firmware_sha[:12]}..." if firmware_sha else ""
                    detail = (
                        "启动前 STATUS_REQ 预检未返回可用 STATUS_RESP；"
                        "demo 判定当前 lower layer 与现有 live 控制面不兼容，"
                        "不会继续发起 live launch。"
                        f"{firmware_hint}"
                    )
                    message = (
                        f"{preflight_message} 启动前 STATUS_REQ 预检未通过，"
                        "本次不再继续发起 live launch，已回退到预录结果。"
                        if preflight_message
                        else (
                            "启动前 STATUS_REQ 预检未返回 STATUS_RESP，"
                            "当前 demo 判定下层行为与现有 live 控制面不兼容；"
                            "本次不再继续发起 live launch，已回退到预录结果。"
                        )
                    )
                    diagnostics = dict(status_payload.get("diagnostics") or {})
                    diagnostics["board_status_preflight"] = status_payload
                    if isinstance(last_live_probe, dict):
                        diagnostics["last_live_probe"] = last_live_probe
                    event_log = list(status_payload.get("logs") or [])
                    if self._can_launch_runner_only_fallback(board_access=board_access, status_payload=status_payload):
                        live_job = launch_remote_reconstruction_job(
                            live_board_access,
                            variant=variant,
                            control_transport="none",
                            control_preflight=status_payload,
                        )
                        live_result = live_job.snapshot()
                        record = {
                            "job": live_job,
                            "job_id": live_job.job_id,
                            "variant": variant,
                            "image_index": image_index,
                            "last_snapshot": live_result,
                        }
                        with self._lock:
                            self._inference_jobs[live_job.job_id] = record
                        event_record = record
                        payload = self._build_inference_response(record, live_result)
                    else:
                        if detail not in event_log:
                            event_log.append(detail)
                        payload = self._build_blocked_inference_payload(
                            variant=variant,
                            image_index=image_index,
                            status_category=status_category,
                            source_label="启动前检查失败，回退展示（归档样例）",
                            message=message,
                            detail=detail,
                            diagnostics=diagnostics,
                            event_log=event_log,
                        )
                if payload.get("status") != "fallback" and not payload.get("job_id"):
                    live_job = launch_remote_reconstruction_job(live_board_access, variant=variant)
                    live_result = live_job.snapshot()
                    record = {
                        "job": live_job,
                        "job_id": live_job.job_id,
                        "variant": variant,
                        "image_index": image_index,
                        "last_snapshot": live_result,
                    }
                    with self._lock:
                        self._inference_jobs[live_job.job_id] = record
                    event_record = record
                    payload = self._build_inference_response(record, live_result)
            else:
                live_job = launch_remote_reconstruction_job(live_board_access, variant=variant)
                live_result = live_job.snapshot()
                record = {
                    "job": live_job,
                    "job_id": live_job.job_id,
                    "variant": variant,
                    "image_index": image_index,
                    "last_snapshot": live_result,
                }
                with self._lock:
                    self._inference_jobs[live_job.job_id] = record
                event_record = record
                payload = self._build_inference_response(record, live_result)
        else:
            payload.update(
                {
                    "status": "fallback",
                    "request_state": "completed",
                    "status_category": "config_error",
                    "live_progress": {
                        "state": "completed",
                        "label": "回退展示",
                        "tone": "degraded",
                        "percent": 0,
                        "phase_percent": 100,
                        "completed_count": 0,
                        "expected_count": DEFAULT_MAX_INPUTS,
                        "remaining_count": DEFAULT_MAX_INPUTS,
                        "completion_ratio": 0.0,
                        "count_source": "demo_default",
                        "count_label": f"0 / {DEFAULT_MAX_INPUTS}",
                        "current_stage": "回退展示",
                        "stages": [],
                        "event_log": [],
                    },
                    "message": "尚未录入本场板卡会话，当前展示归档样例与正式速度报告。",
                    "live_attempt": {
                        "status": "config_error",
                        "request_state": "completed",
                        "status_category": "config_error",
                        "message": "远端推理配置不完整或不可用。 当前已回退到预录结果。",
                        "diagnostics": {},
                    },
                }
            )

        with self._lock:
            if payload.get("request_state") == "completed":
                self._update_last_inference_summary(payload, variant)
        if event_record is not None:
            self._emit_inference_record_events(event_record, payload)
        elif payload.get("request_state") == "completed":
            self._emit_inference_rejection_events(
                variant=variant,
                image_index=image_index,
                status_category=str(payload.get("status_category") or "fallback"),
                message=str(payload.get("message") or "Live job request rejected in demo spine."),
                diagnostics=dict(payload.get("live_attempt", {}).get("diagnostics") or {}),
            )
        return payload

    def get_inference_progress(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._inference_jobs.get(job_id)
        if record is None:
            raise KeyError(job_id)
        job_snapshot = record["job"].snapshot()
        with self._lock:
            record["last_snapshot"] = job_snapshot
        payload = self._build_inference_response(record, job_snapshot)
        with self._lock:
            if payload.get("request_state") == "completed":
                self._update_last_inference_summary(payload, record["variant"])
        self._emit_inference_record_events(record, payload)
        return payload

    def run_fault_demo(self, fault_type: str) -> dict[str, Any]:
        with self._lock:
            board_access = self._board_access

        if board_access.probe_ready:
            live_result = run_fault_action(
                board_access,
                fault_type=fault_type,
                trusted_sha=self._trusted_current_sha,
            )
            if live_result.get("status") == "success":
                response = {
                    "status": "injected",
                    "status_category": "success",
                    "execution_mode": "live",
                    "fault_type": fault_type,
                    "source_label": "真机注入",
                    "message": "已使用当前会话凭据执行 RPMsg 故障注入。",
                    "board_response": live_result.get("board_response", {}),
                    "guard_state": live_result.get("guard_state", "UNKNOWN"),
                    "last_fault_code": live_result.get("last_fault_code", "UNKNOWN"),
                    "status_lamp": "green" if live_result.get("last_fault_code") == "NONE" else "red",
                    "log_entries": live_result.get("logs", []),
                    "details": live_result,
                }
                with self._lock:
                    self._last_control_status = live_result
                    self._last_fault_result = {
                        "fault_type": fault_type,
                        "status": response["status"],
                        "status_category": response["status_category"],
                        "execution_mode": response["execution_mode"],
                        "message": response["message"],
                        "guard_state": response["guard_state"],
                        "last_fault_code": response["last_fault_code"],
                    }
                self._event_spine.publish(
                    "JOB_SUBMITTED",
                    source="fault",
                    plane="control",
                    mode_scope=CONTROL_MODE_SCOPE,
                    message=f"{fault_type} fault demo submitted a control-plane job request.",
                    data={"fault_type": fault_type},
                )
                if fault_type == "heartbeat_timeout":
                    self._event_spine.publish(
                        "JOB_ADMITTED",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message="Heartbeat timeout FIT received an ALLOW admission before watchdog expiry.",
                        data={"fault_type": fault_type},
                    )
                    self._event_spine.publish(
                        "HEARTBEAT_OK",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message="Heartbeat ACK observed before watchdog timeout during FIT-03.",
                        data={"fault_type": fault_type},
                    )
                    self._event_spine.publish(
                        "HEARTBEAT_LOST",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message="Heartbeat watchdog timeout observed during FIT-03.",
                        data={"fault_type": fault_type, "last_fault_code": response["last_fault_code"]},
                    )
                    self._event_spine.publish(
                        "SAFE_STOP_TRIGGERED",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message="SAFE_STOP cleanup triggered after heartbeat timeout FIT.",
                        data={"fault_type": fault_type, "reason": "heartbeat_timeout_cleanup"},
                    )
                    self._event_spine.publish(
                        "SAFE_STOP_CLEARED",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message="SAFE_STOP cleanup returned the board to READY after heartbeat timeout FIT.",
                        data={"fault_type": fault_type, "reason": "heartbeat_timeout_cleanup"},
                    )
                else:
                    self._event_spine.publish(
                        "JOB_REJECTED",
                        source="fault",
                        plane="control",
                        mode_scope=CONTROL_MODE_SCOPE,
                        message=f"{fault_type} fault demo ended in the expected rejection state.",
                        data={"fault_type": fault_type, "last_fault_code": response["last_fault_code"]},
                    )
                self._archive_event_snapshot(
                    reason=f"fault_{fault_type}",
                    extra={"fault_type": fault_type, "execution_mode": response["execution_mode"]},
                )
                return response
            replay = build_fault_replay(fault_type)
            replay["status_category"] = live_result.get("status_category", "fallback")
            replay["live_attempt"] = live_result
            replay["message"] = f"{live_result.get('message', '真机注入失败')} 已切换到 {replay['source_label']}。"
        else:
            replay = build_fault_replay(fault_type)
            replay["status_category"] = "fallback"
        with self._lock:
            self._last_fault_result = {
                "fault_type": fault_type,
                "status": replay["status"],
                "status_category": replay.get("status_category", "fallback"),
                "execution_mode": replay["execution_mode"],
                "message": replay["message"],
                "guard_state": replay["guard_state"],
                "last_fault_code": replay["last_fault_code"],
            }
        return replay

    def recover_fault(self) -> dict[str, Any]:
        with self._lock:
            board_access = self._board_access
            control_status = self._last_control_status
            last_fault = self._last_fault_result

        retained_fault_code = ""
        if last_fault and last_fault.get("last_fault_code"):
            retained_fault_code = str(last_fault.get("last_fault_code") or "")
        elif control_status and control_status.get("last_fault_code"):
            retained_fault_code = str(control_status.get("last_fault_code") or "")

        if board_access.probe_ready:
            live_result = run_recover_action(board_access, trusted_sha=self._trusted_current_sha)
            if live_result.get("status") == "success":
                guard_state = live_result.get("guard_state", "UNKNOWN")
                last_fault_code = live_result.get("last_fault_code", "UNKNOWN")
                response = {
                    "status": "recovered",
                    "status_category": "success",
                    "execution_mode": "live",
                    "source_label": "真机 SAFE_STOP 收口",
                    "message": recover_message(guard_state, last_fault_code),
                    "board_response": live_result.get("board_response", {}),
                    "guard_state": guard_state,
                    "last_fault_code": last_fault_code,
                    "status_lamp": recover_status_lamp(guard_state, last_fault_code),
                    "log_entries": live_result.get("logs", []),
                    "details": live_result,
                }
                with self._lock:
                    self._last_control_status = live_result
                    self._last_fault_result = {
                        "fault_type": "recover",
                        "status": response["status"],
                        "status_category": response["status_category"],
                        "execution_mode": response["execution_mode"],
                        "message": response["message"],
                        "guard_state": response["guard_state"],
                        "last_fault_code": response["last_fault_code"],
                    }
                self._event_spine.publish(
                    "SAFE_STOP_TRIGGERED",
                    source="recover",
                    plane="control",
                    mode_scope=CONTROL_MODE_SCOPE,
                    message="Operator-triggered SAFE_STOP entered the demo event spine.",
                    data={"reason": "manual_recover", "last_fault_code": last_fault_code},
                )
                self._event_spine.publish(
                    "SAFE_STOP_CLEARED",
                    source="recover",
                    plane="control",
                    mode_scope=CONTROL_MODE_SCOPE,
                    message="SAFE_STOP returned the board to READY.",
                    data={"reason": "manual_recover", "last_fault_code": last_fault_code},
                )
                self._archive_event_snapshot(
                    reason="recover_safe_stop",
                    extra={"guard_state": guard_state, "last_fault_code": last_fault_code},
                )
                return response
            replay = build_recover_replay(retained_fault_code)
            replay["status_category"] = live_result.get("status_category", "fallback")
            replay["live_attempt"] = live_result
            replay["message"] = f"{live_result.get('message', '真机恢复失败')} 已切换到安全恢复回放。"
        else:
            replay = build_recover_replay(retained_fault_code)
            replay["status_category"] = "fallback"
        with self._lock:
            self._last_fault_result = {
                "fault_type": "recover",
                "status": replay["status"],
                "status_category": replay.get("status_category", "fallback"),
                "execution_mode": replay["execution_mode"],
                "message": replay["message"],
                "guard_state": replay["guard_state"],
                "last_fault_code": replay["last_fault_code"],
            }
        return replay


class DemoHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler: type["DemoRequestHandler"], app_state: DashboardState) -> None:
        super().__init__(server_address, handler)
        self.app_state = app_state


def demo_startup_env_overrides(args: argparse.Namespace) -> dict[str, str]:
    overrides: dict[str, str] = {}

    env_or_arg_pairs = (
        (DEMO_ADMISSION_MODE_ENV, str(getattr(args, "demo_admission_mode", "") or "").strip()),
        (DEMO_SIGNED_MANIFEST_FILE_ENV, str(getattr(args, "signed_manifest_file", "") or "").strip()),
        (DEMO_SIGNED_MANIFEST_PUBLIC_KEY_ENV, str(getattr(args, "signed_manifest_public_key", "") or "").strip()),
        (DEMO_BASELINE_ADMISSION_MODE_ENV, str(getattr(args, "baseline_admission_mode", "") or "").strip()),
        (
            DEMO_BASELINE_SIGNED_MANIFEST_FILE_ENV,
            str(getattr(args, "baseline_signed_manifest_file", "") or "").strip(),
        ),
        (
            DEMO_BASELINE_SIGNED_MANIFEST_PUBLIC_KEY_ENV,
            str(getattr(args, "baseline_signed_manifest_public_key", "") or "").strip(),
        ),
        ("REMOTE_PASS", ""),
        ("PHYTIUM_PI_PASSWORD", ""),
    )

    for env_name, cli_value in env_or_arg_pairs:
        value = cli_value or str(os.environ.get(env_name, "") or "").strip()
        if value:
            overrides[env_name] = value
    return overrides


class DemoRequestHandler(SimpleHTTPRequestHandler):
    server: DemoHTTPServer

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_cors_headers(self) -> None:
        """Allow local Electron/renderer to call JSON APIs across origins (dev + file:// builds)."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/snapshot":
            self.respond_json(HTTPStatus.OK, self.server.app_state.current_snapshot())
            return
        if parsed.path == "/api/job-manifest-gate":
            params = parse_qs(parsed.query)
            try:
                variant = self.coerce_variant(params.get("variant", ["current"])[0])
            except ValueError as exc:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc)})
                return
            self.respond_json(
                HTTPStatus.OK,
                {"status": "ok", "gate": self.server.app_state.current_job_manifest_gate_status(variant=variant)},
            )
            return
        if parsed.path == "/api/link-director":
            self.respond_json(HTTPStatus.OK, self.server.app_state.current_link_director_status())
            return
        if parsed.path == "/api/aircraft-position":
            self.respond_json(HTTPStatus.OK, self.server.app_state.current_aircraft_position())
            return
        if parsed.path == "/api/event-spine":
            params = parse_qs(parsed.query)
            limit = max(1, min(100, self.coerce_int(params.get("limit", ["25"])[0], default=25)))
            self.respond_json(HTTPStatus.OK, self.server.app_state.current_event_spine(limit=limit))
            return
        if parsed.path == "/api/archive/sessions":
            params = parse_qs(parsed.query)
            limit = max(1, min(100, self.coerce_int(params.get("limit", ["25"])[0], default=25)))
            self.respond_json(HTTPStatus.OK, self.server.app_state.list_archive_sessions(limit=limit))
            return
        if parsed.path == "/api/archive/session":
            params = parse_qs(parsed.query)
            session_id = str(params.get("session_id", [""])[0]).strip()
            limit = max(1, min(100, self.coerce_int(params.get("limit", ["25"])[0], default=25)))
            try:
                payload = self.server.app_state.current_archive_session(session_id=session_id, recent_limit=limit)
            except ArchiveSessionNotFoundError as exc:
                self.respond_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": str(exc)})
                return
            self.respond_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/api/system-status":
            self.respond_json(HTTPStatus.OK, self.server.app_state.current_system_status())
            return
        if parsed.path == "/api/crypto-status":
            self.respond_json(HTTPStatus.OK, self.server.app_state.get_crypto_status())
            return
        if parsed.path == "/api/health":
            self.respond_json(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/api/inference-progress":
            params = parse_qs(parsed.query)
            job_id = str(params.get("job_id", [""])[0]).strip()
            if not job_id:
                self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": "missing job_id"})
                return
            try:
                payload = self.server.app_state.get_inference_progress(job_id)
            except KeyError:
                self.respond_json(HTTPStatus.NOT_FOUND, {"status": "error", "message": "job not found"})
                return
            self.respond_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/docs":
            self.respond_doc_view(parsed.query)
            return
        if parsed.path == "/api/batch-state":
            self.respond_json(HTTPStatus.OK, self.server.app_state.get_batch_state())
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json_body()
        if body is None:
            return
        try:
            if parsed.path == "/api/crypto-toggle":
                enabled = bool(body.get("enabled", False))
                payload = self.server.app_state.set_crypto_toggle(enabled)
                self.respond_json(HTTPStatus.OK, {"status": "ok", **payload})
                return
            if parsed.path == "/api/crypto-test":
                payload = self.server.app_state.run_crypto_test()
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/session/board-access":
                try:
                    payload = self.server.app_state.set_board_access(body)
                except ValueError as exc:
                    self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc)})
                    return
                self.respond_json(HTTPStatus.OK, {"status": "ok", "board_access": payload})
                return
            if parsed.path == "/api/link-director/profile":
                try:
                    payload = self.server.app_state.set_link_director_profile(body)
                except ValueError as exc:
                    self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc)})
                    return
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/aircraft-position":
                payload = self.server.app_state.set_aircraft_position(body)
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/probe-board":
                payload = self.server.app_state.refresh_live_probe()
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/job-manifest-gate/preview":
                try:
                    variant = self.coerce_variant(body.get("variant"), default="current")
                except ValueError as exc:
                    self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": str(exc)})
                    return
                payload = self.server.app_state.preview_job_manifest_gate(variant=variant)
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/run-inference":
                image_index = self.coerce_int(body.get("image_index"), default=0)
                variant = str(body.get("mode") or "current").strip().lower() or "current"
                allow_preflight_degraded = bool(body.get("allow_preflight_degraded", True))
                payload = self.server.app_state.run_demo_inference(
                    variant=variant,
                    image_index=image_index,
                    allow_preflight_degraded=allow_preflight_degraded,
                )
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/run-baseline":
                image_index = self.coerce_int(body.get("image_index"), default=0)
                payload = self.server.app_state.run_demo_inference(variant="baseline", image_index=image_index)
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/run-inference-batch":
                count = self.coerce_int(body.get("count"), default=300)
                count = max(1, min(count, 1000))
                allow_degraded = bool(body.get("allow_preflight_degraded", True))
                payload = self.server.app_state.start_batch_inference(
                    count=count,
                    allow_preflight_degraded=allow_degraded,
                )
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/inject-fault":
                fault_type = str(body.get("fault_type") or "").strip()
                if fault_type not in {"wrong_sha", "illegal_param", "heartbeat_timeout"}:
                    self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": "unsupported fault_type"})
                    return
                payload = self.server.app_state.run_fault_demo(fault_type)
                self.respond_json(HTTPStatus.OK, payload)
                return
            if parsed.path == "/api/recover":
                payload = self.server.app_state.recover_fault()
                self.respond_json(HTTPStatus.OK, payload)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            try:
                self.respond_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "status": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                })
            except Exception:
                pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def read_json_body(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": "invalid json body"})
            return None
        if not isinstance(payload, dict):
            self.respond_json(HTTPStatus.BAD_REQUEST, {"status": "error", "message": "json body must be an object"})
            return None
        return payload

    def coerce_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def coerce_variant(self, value: Any, default: str = "current") -> str:
        variant = str(value or default).strip().lower() or default
        if variant not in {"current", "baseline"}:
            raise ValueError("unsupported variant")
        return variant

    def respond_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def respond_doc_view(self, query: str) -> None:
        params = parse_qs(query)
        raw_path = params.get("path", [""])[0]
        if not raw_path:
            self.send_error(HTTPStatus.BAD_REQUEST, "missing path")
            return
        try:
            path = resolve_repo_path(raw_path)
        except (ValueError, OSError):
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid path")
            return
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "file not found")
            return

        if path.suffix == ".json":
            content = json.dumps(json.loads(read_text(path)), ensure_ascii=False, indent=2)
        else:
            content = read_text(path)

        body = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(repo_relative(path))}</title>
  <style>
    body {{
      margin: 0;
      font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Helvetica Neue", sans-serif;
      background: linear-gradient(180deg, #f3efe6 0%, #fcfbf8 100%);
      color: #123041;
    }}
    header {{
      padding: 1.25rem 1.5rem 1rem;
      border-bottom: 1px solid rgba(18, 48, 65, 0.12);
      background: rgba(255, 255, 255, 0.9);
      position: sticky;
      top: 0;
    }}
    a {{
      color: #a04b14;
      text-decoration: none;
      font-weight: 700;
    }}
    main {{
      padding: 1.25rem 1.5rem 2rem;
    }}
    pre {{
      margin: 0;
      overflow: auto;
      padding: 1rem;
      border-radius: 16px;
      background: #102635;
      color: #f7f1e8;
      line-height: 1.55;
      font-size: 0.92rem;
    }}
    .path {{
      font-family: "Noto Serif SC", "Source Han Serif SC", "STSong", serif;
      font-size: 1.15rem;
      margin-bottom: 0.35rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="path">{html.escape(repo_relative(path))}</div>
    <a href="/">返回演示系统</a>
  </header>
  <main><pre>{html.escape(content)}</pre></main>
</body>
</html>
""".encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path: str) -> str:
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"


def main() -> int:
    args = parse_args()
    app_state = DashboardState(
        args.probe_env,
        args.probe_timeout_sec,
        demo_startup_env_overrides=demo_startup_env_overrides(args),
        event_archive_root=default_event_archive_root(),
    )
    if args.probe_startup:
        app_state.refresh_live_probe()
    server = DemoHTTPServer((args.host, args.port), DemoRequestHandler, app_state)
    print(f"Feiteng semantic visual return demo dashboard: http://{args.host}:{args.port}")
    print(f"Project root: {PROJECT_ROOT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
