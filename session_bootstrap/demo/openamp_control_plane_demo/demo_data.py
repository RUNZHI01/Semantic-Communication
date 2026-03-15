from __future__ import annotations

import base64
from functools import lru_cache
import json
import re
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_ROOT = PROJECT_ROOT / "session_bootstrap" / "reports"
PACKAGE_ROOT = REPORTS_ROOT / "openamp_control_plane_evidence_package_20260315"
SCRIPTS_ROOT = PROJECT_ROOT / "session_bootstrap" / "scripts"

FAULT_CODE_NAMES = {
    0: "NONE",
    1: "ARTIFACT_SHA_MISMATCH",
    3: "HEARTBEAT_TIMEOUT",
    9: "ILLEGAL_PARAM_RANGE",
    10: "MANUAL_SAFE_STOP",
}

GUARD_STATE_NAMES = {
    0: "BOOT",
    1: "READY",
    2: "JOB_ACTIVE",
    3: "WAIT_DONE",
    4: "DENY_PENDING",
    5: "FAULT_LATCHED",
}

DISPLAY_GUARD_STATE_NAMES = {
    "BOOT": "启动中 BOOT",
    "READY": "就绪 READY",
    "JOB_ACTIVE": "任务执行中 JOB_ACTIVE",
    "WAIT_DONE": "等待完成 WAIT_DONE",
    "DENY_PENDING": "拒绝待确认 DENY_PENDING",
    "FAULT_LATCHED": "故障锁存 FAULT_LATCHED",
}

DISPLAY_FAULT_CODE_NAMES = {
    "NONE": "无故障 NONE",
    "ARTIFACT_SHA_MISMATCH": "工件 SHA 不匹配 ARTIFACT_SHA_MISMATCH",
    "HEARTBEAT_TIMEOUT": "心跳超时 HEARTBEAT_TIMEOUT",
    "ILLEGAL_PARAM_RANGE": "参数范围非法 ILLEGAL_PARAM_RANGE",
    "MANUAL_SAFE_STOP": "人工安全停止 MANUAL_SAFE_STOP",
}

FIT_SCENARIO_LABELS = {
    "wrong expected_sha256 JOB_REQ on real board path": "真机路径下发送错误 expected_sha256 的 JOB_REQ",
    "illegal expected_outputs JOB_REQ on real board path": "真机路径下发送非法 expected_outputs 的 JOB_REQ",
    "heartbeat timeout / watchdog semantics on real board path": "真机路径下验证 heartbeat timeout / watchdog 语义",
    "heartbeat timeout / watchdog semantics on real board path after watchdog fix": (
        "部署 watchdog 修复后，在真机路径下复验 heartbeat timeout / watchdog 语义"
    ),
}

FIT_RISK_LABELS = {
    "unknown artifact execution risk": "未知工件被放行执行的风险",
    "input contract / param range violation": "输入契约或参数范围违规风险",
    "runaway active job due to missing heartbeat timeout watchdog": "缺少 heartbeat timeout watchdog 导致任务失控持续运行的风险",
}

FIT_CONCLUSION_LABELS = {
    (
        "After deploying the lazy watchdog firmware fix, a follow-up STATUS_REQ after 5s with no "
        "heartbeat now exposes HEARTBEAT_TIMEOUT(F003) and returns the board to READY."
    ): "部署 watchdog 修复固件后，停发 heartbeat 5 秒再发 STATUS_REQ，板卡会返回 READY，并显式暴露 HEARTBEAT_TIMEOUT(F003)。",
    (
        "Current live firmware does not auto-trigger HEARTBEAT_TIMEOUT / SAFE_STOP after the tested "
        "5s no-heartbeat window; manual SAFE_STOP was required to return the board to READY."
    ): "旧 live firmware 在停发 heartbeat 5 秒后不会自动触发 HEARTBEAT_TIMEOUT / SAFE_STOP，必须手动 SAFE_STOP 才能回到 READY。",
}

FIT_EVIDENCE_LABELS = {
    "fit_report": "FIT 报告",
    "coverage_matrix": "覆盖矩阵",
    "remote_probe": "远程探板结果",
    "wrapper_summary": "wrapper 摘要",
    "job_req_bridge_summary": "JOB_REQ bridge 摘要",
    "post_status_snapshot": "事后状态快照",
    "final_status_snapshot": "最终状态快照",
}

INLINE_LINK_LABELS = {
    "summary": "摘要",
    "probe": "原始探板",
    "probe log": "探针日志",
    "history summary": "历史摘要",
    "fit": "FIT 报告",
}

PRERECORDED_SAMPLE_FIXTURES = (
    {
        "sample_id": "places365-208",
        "label": "样例 208",
        "title": "Places365 预置样例 208",
        "note": "使用仓库内已归档的参考图与 current/baseline 重建图，适合现场稳定演示。",
        "relative_path": "Places365_val_00000208_recon.png",
        "original_path": PROJECT_ROOT / "session_bootstrap" / "tmp" / "quality_samples_20260311" / "current" / "test_208.png",
        "current_path": PROJECT_ROOT
        / "session_bootstrap"
        / "tmp"
        / "quality_samples_20260311"
        / "current"
        / "Places365_val_00000208_recon.png",
        "baseline_path": PROJECT_ROOT
        / "session_bootstrap"
        / "tmp"
        / "quality_samples_20260311"
        / "baseline"
        / "Places365_val_00000208_recon.png",
    },
)
QUALITY_CURRENT_REPORT = REPORTS_ROOT / "quality_metrics_20260312_pytorch_vs_tvm_current.json"
QUALITY_BASELINE_REPORT = REPORTS_ROOT / "quality_metrics_20260312_pytorch_vs_tvm_baseline.json"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def resolve_repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    path.relative_to(PROJECT_ROOT)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


@lru_cache(maxsize=None)
def image_data_uri(path_value: str) -> str:
    path = Path(path_value)
    suffix = path.suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


@lru_cache(maxsize=2)
def quality_metrics_by_relative_path(report_path_value: str) -> dict[str, dict[str, Any]]:
    payload = read_json(Path(report_path_value))
    return {
        item["relative_path"]: item
        for item in payload.get("per_image", [])
        if isinstance(item, dict) and item.get("relative_path")
    }


def clean_markdown_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def normalize_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")


def to_float(value: Any) -> float:
    return float(str(value).replace(",", "").replace("%", "").replace("x", ""))


def short_sha(value: str) -> str:
    return value[:12] if value else ""


def display_guard_state(value: int | str | None) -> str:
    raw = format_guard_state(value)
    return DISPLAY_GUARD_STATE_NAMES.get(raw, raw)


def display_fault_code(value: int | str | None) -> str:
    raw = format_fault_code(value)
    return DISPLAY_FAULT_CODE_NAMES.get(raw, raw)


def localize_fit_scenario(value: str) -> str:
    return FIT_SCENARIO_LABELS.get(value, value)


def localize_fit_risk(value: str) -> str:
    return FIT_RISK_LABELS.get(value, value)


def localize_fit_conclusion(value: str) -> str:
    return FIT_CONCLUSION_LABELS.get(value, value)


def localize_fit_evidence_label(value: str) -> str:
    return FIT_EVIDENCE_LABELS.get(value, value.replace("_", " "))


def localize_inline_link_label(value: str) -> str:
    return INLINE_LINK_LABELS.get(value, value)


def localize_live_probe_summary(summary: str, loaded_from_cache: bool) -> str:
    if summary:
        message = f"当前板卡可达。探板摘要：{summary}"
    else:
        message = "当前板卡可达，已拿到最新只读 SSH 探板结果。"
    if loaded_from_cache:
        message += " 该结果来自上一次成功探板的保存记录。"
    return message


def localize_coverage_item(value: str) -> str:
    mapping = {
        "wrapper-backed board smoke": "wrapper 板级冒烟",
        "wrong-SHA denial": "错误 SHA 拒绝",
        "input contract violation denial": "输入契约违规拒绝",
        "heartbeat timeout / watchdog on old live firmware": "旧固件心跳超时 / watchdog",
        "heartbeat timeout / watchdog after fix": "修复后心跳超时 / watchdog",
    }
    return mapping.get(value, value)


def localize_mapped_id(value: str) -> str:
    mapping = {
        "bring-up gate": "bring-up 门禁",
        "manual stop milestone": "手动停止里程碑",
    }
    return mapping.get(value, value)


def format_guard_state(value: int | str | None) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, str):
        return value
    return GUARD_STATE_NAMES.get(value, f"UNKNOWN_{value}")


def format_fault_code(value: int | str | None) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, str):
        return value
    return FAULT_CODE_NAMES.get(value, f"UNKNOWN_{value}")


def parse_markdown_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in read_text(path).splitlines():
        match = re.match(r"^- ([^:]+):\s*(.+?)\s*$", line)
        if not match:
            continue
        values[normalize_key(match.group(1))] = clean_markdown_value(match.group(2))
    return values


def parse_links(cell: str, base_dir: Path) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", cell):
        localized_label = localize_inline_link_label(label)
        if target.startswith("http://") or target.startswith("https://"):
            links.append({"label": localized_label, "path": target, "external": True})
            continue
        resolved = (base_dir / target).resolve()
        links.append({"label": localized_label, "path": repo_relative(resolved), "external": False})
    return links


def parse_markdown_table(text: str, heading: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    table_lines: list[str] = []
    collecting = False
    for line in lines:
        if line.strip() == heading:
            collecting = True
            continue
        if not collecting:
            continue
        if line.startswith("|"):
            table_lines.append(line.rstrip())
            continue
        if table_lines:
            break
    if len(table_lines) < 3:
        return []

    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def link_entry(path: Path | str, label: str, note: str | None = None) -> dict[str, Any]:
    if isinstance(path, Path):
        value = repo_relative(path)
    else:
        value = path
    entry = {"label": label, "path": value}
    if note:
        entry["note"] = note
    return entry


def load_fit_summary(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    evidence = payload.get("evidence_bundle", {})
    links = []
    for key in (
        "fit_report",
        "coverage_matrix",
        "remote_probe",
        "wrapper_summary",
        "job_req_bridge_summary",
        "post_status_snapshot",
        "final_status_snapshot",
    ):
        raw = evidence.get(key)
        if not raw:
            continue
        links.append(link_entry(resolve_repo_path(raw), localize_fit_evidence_label(key)))
    return {
        "fit_id": payload["fit_id"],
        "status": payload["status"],
        "scenario": localize_fit_scenario(payload["scenario"]),
        "risk_item": localize_fit_risk(payload["risk_item"]),
        "trusted_current_sha": payload.get("trusted_current_sha", ""),
        "live_firmware_sha256": payload.get("live_firmware_sha256", ""),
        "generated_at": payload["generated_at"],
        "board_access": payload.get("board_access", {}),
        "observed_result": payload.get("observed_result", {}),
        "conclusion": localize_fit_conclusion(payload.get("conclusion", "")),
        "evidence": links,
        "run_id": payload["run_id"],
    }


def synthesize_fit_readout(summary: dict[str, Any]) -> str:
    fit_id = summary["fit_id"]
    observed = summary.get("observed_result", {})
    if fit_id == "FIT-01":
        return (
            f"判定={observed.get('decision', 'UNKNOWN')}；"
            f"故障={display_fault_code(observed.get('fault_name', 'UNKNOWN'))}；"
            f"守护状态保持 {display_guard_state(observed.get('guard_final', 'UNKNOWN'))}。"
        )
    if fit_id == "FIT-02":
        return (
            f"判定={observed.get('decision', 'UNKNOWN')}；"
            f"故障={display_fault_code(observed.get('fault_name', 'UNKNOWN'))}；"
            f"wrapper 结果={observed.get('wrapper_result', 'UNKNOWN')}。"
        )
    timeout_status = observed.get("timeout_status") or observed.get("status_after_5s_without_heartbeat") or {}
    return (
        f"停发 heartbeat 5 秒后，状态={display_guard_state(timeout_status.get('guard_state'))}；"
        f"故障={display_fault_code(timeout_status.get('last_fault_code'))}；"
        f"active_job_id={timeout_status.get('active_job_id', 'NA')}。"
    )


def live_probe_loaded_from_cache(live_probe: dict[str, Any] | None) -> bool:
    return bool(live_probe and live_probe.get("_loaded_from_cache"))


def build_mode_snapshot(live_probe: dict[str, Any] | None) -> dict[str, Any]:
    materials = parse_markdown_key_values(PACKAGE_ROOT / "demo_materials_index.md")
    has_live = bool(live_probe and live_probe.get("reachable"))
    if has_live:
        effective_label = "在线读数可用"
        effective_tone = "live"
        if live_probe_loaded_from_cache(live_probe):
            summary = (
                "界面已从保存的成功探板记录恢复最近一次只读 SSH 结果；若需最新板卡状态，可手动再次读取。"
            )
        else:
            summary = (
                "界面已拿到新的只读 SSH 探板结果；整体仍以证据包为主，只额外展示当前板卡状态，不改变控制流。"
            )
    else:
        effective_label = "仅展示证据"
        effective_tone = "fallback"
        summary = (
            "当前没有新的在线探板结果，界面展示仓库内证据包和最近一次已验证的控制面状态。"
        )
    return {
        "default_mode": materials.get("default_mode", "offline-first, evidence-led"),
        "live_policy": materials.get("live_policy", ""),
        "effective_label": effective_label,
        "effective_tone": effective_tone,
        "summary": summary,
    }


def build_board_snapshot(live_probe: dict[str, Any] | None) -> dict[str, Any]:
    fit03_pass = load_fit_summary(
        REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "fit_summary.json"
    )
    fit03_fail = load_fit_summary(
        REPORTS_ROOT / "openamp_heartbeat_timeout_fit_20260315_015841" / "fit_summary.json"
    )
    wrapper_summary = read_json(REPORTS_ROOT / "openamp_wrapper_hook_board_smoke_20260314_005.wrapper_summary.json")
    job_done_probe = read_json(REPORTS_ROOT / "openamp_job_done_real_probe_20260315_001.json")

    timeout_status = fit03_pass["observed_result"]["timeout_status"]
    evidence_status = {
        "label": "板级证据已确认",
        "summary": (
            "真机已通过 JOB_DONE 清理路径和修复后的 FIT-03 超时路径完成验证。现有证据表明：板卡无需重启即可回到 READY。"
        ),
        "confirmed_at": fit03_pass["generated_at"],
        "trusted_current_sha": fit03_pass["trusted_current_sha"],
        "final_live_firmware_sha256": fit03_pass["live_firmware_sha256"],
        "transport": job_done_probe["transport"],
        "wrapper_board_smoke": {
            "result": wrapper_summary["result"],
            "source": wrapper_summary["job_req_response"]["source"],
            "runner_exit_code": wrapper_summary["runner_exit_code"],
        },
        "timeout_ready_state": {
            "guard_state": format_guard_state(timeout_status["guard_state"]),
            "active_job_id": timeout_status["active_job_id"],
            "last_fault": format_fault_code(timeout_status["last_fault_code"]),
            "total_fault_count": timeout_status["total_fault_count"],
        },
        "job_done_ready_state": {
            "guard_state": format_guard_state(job_done_probe["status_after_job_done"]["guard_state"]),
            "active_job_id": job_done_probe["status_after_job_done"]["active_job_id"],
            "last_fault": format_fault_code(job_done_probe["status_after_job_done"]["last_fault_code"]),
        },
        "evidence": [
            link_entry(REPORTS_ROOT / "openamp_phase5_job_done_success_2026-03-15.md", "JOB_DONE 摘要"),
            link_entry(REPORTS_ROOT / "openamp_phase5_fit03_watchdog_success_2026-03-15.md", "FIT-03 修复后摘要"),
            link_entry(REPORTS_ROOT / "openamp_job_done_real_probe_20260315_001.json", "JOB_DONE 原始探板"),
            link_entry(
                REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "remote_probe.json",
                "FIT-03 修复后远程探板",
            ),
        ],
        "history_note": fit03_fail["conclusion"],
    }

    if live_probe and live_probe.get("reachable"):
        loaded_from_cache = live_probe_loaded_from_cache(live_probe)
        summary = localize_live_probe_summary(str(live_probe.get("summary", "")), loaded_from_cache)
        current = {
            "label": "保存的只读 SSH 探板" if loaded_from_cache else "最新只读 SSH 探板",
            "summary": summary,
            "reachable": True,
            "requested_at": live_probe.get("requested_at", ""),
            "details": live_probe.get("details", {}),
            "evidence": [link_entry(REPORTS_ROOT / "openamp_demo_live_probe_latest.json", "在线探板 JSON")],
        }
    else:
        reason = live_probe.get("error", "") if live_probe else ""
        summary = "当前未拿到新的在线探板结果，界面将继续展示最近一次已验证的证据。"
        if reason:
            summary = f"{summary} 原因：{reason}"
        current = {
            "label": "暂无在线探板",
            "summary": summary,
            "reachable": False,
            "requested_at": live_probe.get("requested_at", "") if live_probe else "",
            "details": live_probe.get("details", {}) if live_probe else {},
            "evidence": [],
        }

    return {
        "evidence_status": evidence_status,
        "current_status": current,
    }


def build_milestones_snapshot() -> list[dict[str, Any]]:
    coverage_text = read_text(PACKAGE_ROOT / "coverage_matrix.md")
    rows = parse_markdown_table(coverage_text, "## Test Coverage")
    milestones = [
        {
            "stage": "P0",
            "coverage_item": "冷启动 / remoteproc / RPMsg 演示门禁",
            "mapped_id": "bring-up 门禁",
            "status": "PASS",
            "key_proof_point": (
                "基于 release_v1.4.0 派生的固件已先打通板卡启动、remoteproc 和 RPMsg 演示门禁，然后才继续收集更细的控制面里程碑证据。"
            ),
            "evidence": [
                link_entry(
                    REPORTS_ROOT / "openamp_phase5_release_v1.4.0_cold_boot_and_demo_success_2026-03-14.md",
                    "冷启动摘要",
                )
            ],
        }
    ]
    for row in rows:
        if row.get("Stage") != "P0":
            continue
        milestones.append(
            {
                "stage": row["Stage"],
                "coverage_item": localize_coverage_item(row["Coverage Item"].strip("`")),
                "mapped_id": localize_mapped_id(row["Mapped ID"].strip("`")),
                "status": row["Status"],
                "key_proof_point": row["Key Proof Point"],
                "evidence": parse_links(row["Evidence"], PACKAGE_ROOT),
            }
        )
    return milestones


def build_fit_snapshot() -> list[dict[str, Any]]:
    fit01 = load_fit_summary(REPORTS_ROOT / "openamp_wrong_sha_fit_20260315_012403" / "fit_summary.json")
    fit02 = load_fit_summary(REPORTS_ROOT / "openamp_input_contract_fit_20260315_014542" / "fit_summary.json")
    fit03_fail = load_fit_summary(REPORTS_ROOT / "openamp_heartbeat_timeout_fit_20260315_015841" / "fit_summary.json")
    fit03_pass = load_fit_summary(
        REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "fit_summary.json"
    )
    fit03_pass["history"] = {
        "label": "修复前历史",
        "status": fit03_fail["status"],
        "summary": fit03_fail["conclusion"],
        "evidence": fit03_fail["evidence"],
        "generated_at": fit03_fail["generated_at"],
    }
    fits = [fit01, fit02, fit03_pass]
    for fit in fits:
        fit["readout"] = synthesize_fit_readout(fit)
    return fits


def build_performance_snapshot() -> dict[str, Any]:
    payload = parse_markdown_key_values(REPORTS_ROOT / "inference_compare_currentsafe_chunk4_refresh_20260313_1758.md")
    end_to_end = parse_markdown_key_values(
        REPORTS_ROOT / "inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md"
    )
    speedup = parse_markdown_key_values(REPORTS_ROOT / "current_scheme_b_compare_20260311_195303.md")
    artifact_sha = payload["current_expected_sha256_configured"]

    return {
        "artifact_sha": artifact_sha,
        "positioning_note": (
            "OpenAMP FIT 使用的 trusted current SHA，也有最新解码性能报告做交叉支撑。OpenAMP wrapper 负责准入和状态控制，不替代现有推理数据通路。"
        ),
        "metrics": [
            {
                "label": "Payload 中位延迟",
                "current": f"{payload['current_run_median_ms']} ms",
                "baseline": f"{payload['baseline_run_median_ms']} ms",
                "improvement": f"{payload['improvement_pct']}%",
                "report": link_entry(
                    REPORTS_ROOT / "inference_compare_currentsafe_chunk4_refresh_20260313_1758.md",
                    "Payload 对比报告",
                ),
                "delta_ms": payload["delta_ms_current_minus_baseline"],
            },
            {
                "label": "端到端中位延迟",
                "current": f"{end_to_end['current_run_median_ms']} ms/image",
                "baseline": f"{end_to_end['baseline_run_median_ms']} ms/image",
                "improvement": f"{end_to_end['improvement_pct']}%",
                "report": link_entry(
                    REPORTS_ROOT / "inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md",
                    "端到端对比报告",
                ),
                "delta_ms": end_to_end["delta_ms_current_minus_baseline"],
            },
            {
                "label": "增量调优加速比",
                "current": speedup["incremental_speedup_vs_rebuild_only"],
                "baseline": "仅重编译 current",
                "improvement": speedup["incremental_improvement_vs_rebuild_only"],
                "report": link_entry(
                    REPORTS_ROOT / "current_scheme_b_compare_20260311_195303.md",
                    "current-only 加速报告",
                ),
                "delta_ms": speedup["incremental_vs_rebuild_only_delta"],
            },
        ],
        "micro_summary": {
            "payload_current_ms": to_float(payload["current_run_median_ms"]),
            "payload_baseline_ms": to_float(payload["baseline_run_median_ms"]),
            "payload_improvement_pct": to_float(payload["improvement_pct"]),
            "end_to_end_current_ms": to_float(end_to_end["current_run_median_ms"]),
            "end_to_end_baseline_ms": to_float(end_to_end["baseline_run_median_ms"]),
            "end_to_end_improvement_pct": to_float(end_to_end["improvement_pct"]),
            "incremental_speedup_x": to_float(speedup["incremental_speedup_vs_rebuild_only"]),
        },
    }


def speedup_x(baseline_ms: float, current_ms: float) -> float:
    if current_ms <= 0:
        return 0.0
    return round(baseline_ms / current_ms, 1)


def build_comparison_snapshot() -> dict[str, Any]:
    performance = build_performance_snapshot()
    micro = performance["micro_summary"]
    return {
        "payload": {
            "label": "Payload 推理延迟",
            "baseline_ms": micro["payload_baseline_ms"],
            "current_ms": micro["payload_current_ms"],
            "improvement_pct": micro["payload_improvement_pct"],
            "speedup_x": speedup_x(micro["payload_baseline_ms"], micro["payload_current_ms"]),
            "callout": (
                f"正式 payload 口径：{micro['payload_baseline_ms']:.1f} → "
                f"{micro['payload_current_ms']:.3f} ms"
            ),
        },
        "end_to_end": {
            "label": "端到端重建延迟",
            "baseline_ms": micro["end_to_end_baseline_ms"],
            "current_ms": micro["end_to_end_current_ms"],
            "improvement_pct": micro["end_to_end_improvement_pct"],
            "speedup_x": speedup_x(micro["end_to_end_baseline_ms"], micro["end_to_end_current_ms"]),
            "callout": (
                f"正式真实端到端口径：{micro['end_to_end_baseline_ms']:.1f} → "
                f"{micro['end_to_end_current_ms']:.3f} ms/image"
            ),
        },
        "trusted_current_sha": performance["artifact_sha"],
    }


def build_inference_sample_catalog() -> list[dict[str, Any]]:
    current_quality = quality_metrics_by_relative_path(str(QUALITY_CURRENT_REPORT))
    baseline_quality = quality_metrics_by_relative_path(str(QUALITY_BASELINE_REPORT))
    catalog: list[dict[str, Any]] = []
    for index, fixture in enumerate(PRERECORDED_SAMPLE_FIXTURES):
        current_entry = current_quality.get(fixture["relative_path"], {})
        baseline_entry = baseline_quality.get(fixture["relative_path"], {})
        catalog.append(
            {
                "index": index,
                "sample_id": fixture["sample_id"],
                "label": fixture["label"],
                "title": fixture["title"],
                "note": fixture["note"],
                "quality_preview": {
                    "current_psnr_db": current_entry.get("psnr_db"),
                    "current_ssim": current_entry.get("ssim"),
                    "baseline_psnr_db": baseline_entry.get("psnr_db"),
                    "baseline_ssim": baseline_entry.get("ssim"),
                },
            }
        )
    return catalog


def build_prerecorded_inference_result(image_index: int, variant: str) -> dict[str, Any]:
    variant_key = variant.lower()
    if image_index < 0 or image_index >= len(PRERECORDED_SAMPLE_FIXTURES):
        raise IndexError("invalid image_index")
    fixture = PRERECORDED_SAMPLE_FIXTURES[image_index]
    comparison = build_comparison_snapshot()
    current_quality = quality_metrics_by_relative_path(str(QUALITY_CURRENT_REPORT))
    baseline_quality = quality_metrics_by_relative_path(str(QUALITY_BASELINE_REPORT))
    quality_entry = (
        current_quality.get(fixture["relative_path"], {})
        if variant_key == "current"
        else baseline_quality.get(fixture["relative_path"], {})
    )
    original_path = fixture["original_path"]
    reconstructed_path = fixture["current_path"] if variant_key == "current" else fixture["baseline_path"]

    total_ms = (
        comparison["end_to_end"]["current_ms"]
        if variant_key == "current"
        else comparison["end_to_end"]["baseline_ms"]
    )
    payload_ms = (
        comparison["payload"]["current_ms"]
        if variant_key == "current"
        else comparison["payload"]["baseline_ms"]
    )
    prep_ms = round(max(total_ms - payload_ms, 0.0), 3)

    stage_timings = [
        {
            "label": "前段准备 / 链路",
            "value_ms": prep_ms,
            "emphasis": "host",
        },
        {
            "label": "板端 payload / 解码",
            "value_ms": payload_ms,
            "emphasis": "board",
        },
        {
            "label": "总计",
            "value_ms": total_ms,
            "emphasis": "total",
        },
    ]

    return {
        "status": "success",
        "execution_mode": "prerecorded",
        "source_label": "预录结果",
        "message": "当前展示使用已校验的预录图像与正式速度报告，可稳定支撑答辩演示。",
        "variant": variant_key,
        "image_index": image_index,
        "sample": {
            "sample_id": fixture["sample_id"],
            "label": fixture["label"],
            "title": fixture["title"],
            "note": fixture["note"],
        },
        "original_image_b64": image_data_uri(str(original_path)),
        "reconstructed_image_b64": image_data_uri(str(reconstructed_path)),
        "timings": {
            "payload_ms": round(payload_ms, 3),
            "prepare_ms": prep_ms,
            "total_ms": round(total_ms, 3),
            "stages": stage_timings,
        },
        "quality": {
            "psnr_db": quality_entry.get("psnr_db"),
            "ssim": quality_entry.get("ssim"),
        },
        "artifact_sha": comparison["trusted_current_sha"] if variant_key == "current" else "formal-baseline",
        "evidence": [
            link_entry(QUALITY_CURRENT_REPORT if variant_key == "current" else QUALITY_BASELINE_REPORT, "质量报告"),
            link_entry(
                fixture["current_path"] if variant_key == "current" else fixture["baseline_path"],
                "重建图像",
            ),
        ],
    }


def build_fault_catalog() -> list[dict[str, Any]]:
    fit_map = {fit["fit_id"]: fit for fit in build_fit_snapshot()}
    return [
        {
            "fault_type": "wrong_sha",
            "title": "错误 SHA 注入",
            "fit_id": "FIT-01",
            "summary": fit_map["FIT-01"]["scenario"],
        },
        {
            "fault_type": "illegal_param",
            "title": "非法参数注入",
            "fit_id": "FIT-02",
            "summary": fit_map["FIT-02"]["scenario"],
        },
        {
            "fault_type": "heartbeat_timeout",
            "title": "心跳超时注入",
            "fit_id": "FIT-03",
            "summary": fit_map["FIT-03"]["scenario"],
        },
    ]


def build_fault_replay(fault_type: str) -> dict[str, Any]:
    if fault_type == "wrong_sha":
        fit_summary = load_fit_summary(REPORTS_ROOT / "openamp_wrong_sha_fit_20260315_012403" / "fit_summary.json")
        return {
            "status": "injected",
            "execution_mode": "replay",
            "fault_type": fault_type,
            "fit_id": "FIT-01",
            "source_label": "FIT-01 回放模式",
            "message": "未进入真机注入链路，当前播放已校验的 FIT-01 日志序列。",
            "board_response": {
                "decision": "DENY",
                "fault_code": "ARTIFACT_SHA_MISMATCH",
                "guard_state": "READY",
            },
            "guard_state": "READY",
            "last_fault_code": "ARTIFACT_SHA_MISMATCH",
            "status_lamp": "red",
            "log_entries": [
                "[01:24:34] ▶ RPMsg STATUS_REQ，guard=READY",
                "[01:24:34] ▶ 发送 JOB_REQ，expected_sha=...dc0",
                "[01:24:34] ◀ JOB_ACK: DENY，fault=ARTIFACT_SHA_MISMATCH",
                "[01:24:35] ◀ STATUS_RESP: READY，last_fault=ARTIFACT_SHA_MISMATCH",
            ],
            "fit_summary": fit_summary,
        }
    if fault_type == "illegal_param":
        fit_summary = load_fit_summary(REPORTS_ROOT / "openamp_input_contract_fit_20260315_014542" / "fit_summary.json")
        return {
            "status": "injected",
            "execution_mode": "replay",
            "fault_type": fault_type,
            "fit_id": "FIT-02",
            "source_label": "FIT-02 回放模式",
            "message": "未进入真机注入链路，当前播放已校验的 FIT-02 日志序列。",
            "board_response": {
                "decision": "DENY",
                "fault_code": "ILLEGAL_PARAM_RANGE",
                "guard_state": "READY",
            },
            "guard_state": "READY",
            "last_fault_code": "ILLEGAL_PARAM_RANGE",
            "status_lamp": "red",
            "log_entries": [
                "[01:47:41] ▶ RPMsg STATUS_REQ，guard=READY",
                "[01:47:41] ▶ 发送 JOB_REQ，expected_outputs=2",
                "[01:47:41] ◀ JOB_ACK: DENY，fault=ILLEGAL_PARAM_RANGE",
                "[01:47:42] ◀ STATUS_RESP: READY，last_fault=ILLEGAL_PARAM_RANGE",
            ],
            "fit_summary": fit_summary,
        }
    fit_summary = load_fit_summary(REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "fit_summary.json")
    return {
        "status": "injected",
        "execution_mode": "replay",
        "fault_type": fault_type,
        "fit_id": "FIT-03",
        "source_label": "FIT-03 回放模式",
        "message": "未进入真机注入链路，当前播放已校验的 FIT-03 watchdog 修复后日志。",
        "board_response": {
            "decision": "ALLOW",
            "fault_code": "HEARTBEAT_TIMEOUT",
            "guard_state": "READY",
        },
        "guard_state": "READY",
        "last_fault_code": "HEARTBEAT_TIMEOUT",
        "status_lamp": "red",
        "log_entries": [
            "[02:36:17] ▶ STATUS_REQ，guard=READY",
            "[02:36:17] ▶ JOB_REQ -> JOB_ACK(ALLOW)",
            "[02:36:17] ▶ HEARTBEAT -> HEARTBEAT_ACK(ok=1)",
            "[02:36:22] ◀ STATUS_RESP: READY，last_fault=HEARTBEAT_TIMEOUT",
            "[02:36:22] ▶ SAFE_STOP 清理完成，guard 保持 READY",
        ],
        "fit_summary": fit_summary,
    }


def build_recover_replay() -> dict[str, Any]:
    return {
        "status": "recovered",
        "execution_mode": "replay",
        "source_label": "安全恢复回放",
        "message": "未进入真机恢复链路，当前展示 SAFE_STOP → READY 的预录恢复结果。",
        "board_response": {
            "decision": "ACK",
            "fault_code": "NONE",
            "guard_state": "READY",
        },
        "guard_state": "READY",
        "last_fault_code": "NONE",
        "status_lamp": "green",
        "log_entries": [
            "[02:36:22] ▶ 发送 SAFE_STOP",
            "[02:36:22] ◀ STATUS_RESP: READY，last_fault=NONE",
        ],
    }


def build_guided_demo_snapshot() -> dict[str, Any]:
    return {
        "sample_catalog": build_inference_sample_catalog(),
        "comparison": build_comparison_snapshot(),
        "fault_catalog": build_fault_catalog(),
    }


def build_operator_snapshot() -> dict[str, Any]:
    return {
        "launch_commands": [
            "bash ./session_bootstrap/scripts/run_openamp_demo.sh",
            (
                "bash ./session_bootstrap/scripts/run_openamp_demo.sh "
                "--port 8090 --probe-env ./session_bootstrap/config/phytium_pi_login.env"
            ),
            (
                "python3 ./session_bootstrap/scripts/probe_openamp_board_status.py "
                "--env ./session_bootstrap/config/phytium_pi_login.env"
            ),
        ],
        "host_side": {
            "summary": (
                "主机侧读取仓库内已保存的证据包、原始 JSON 探板、性能报告和 wrapper 摘要，不额外生成新的业务结论。"
            ),
            "items": [
                link_entry(PACKAGE_ROOT / "README.md", "证据包索引"),
                link_entry(PACKAGE_ROOT / "coverage_matrix.md", "覆盖矩阵"),
                link_entry(PACKAGE_ROOT / "demo_materials_index.md", "演示材料索引"),
                link_entry(SCRIPTS_ROOT / "openamp_control_wrapper.py", "控制 wrapper"),
                link_entry(SCRIPTS_ROOT / "openamp_rpmsg_bridge.py", "RPMsg bridge"),
            ],
        },
        "slave_side": {
            "summary": (
                "板端 / OpenAMP 侧依赖此前已在真机报告中验证的 live firmware 和 Linux RPMsg 传输。可选在线探板只读取主机名、remoteproc 状态、RPMsg 设备和固件 SHA。"
            ),
            "items": [
                link_entry(REPORTS_ROOT / "openamp_phase5_fit03_watchdog_success_2026-03-15.md", "FIT-03 修复后摘要"),
                link_entry(
                    REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "remote_probe.json",
                    "FIT-03 修复后远程探板",
                ),
                link_entry(SCRIPTS_ROOT / "connect_phytium_pi.sh", "SSH 连接脚本"),
                link_entry(SCRIPTS_ROOT / "probe_openamp_board_status.py", "只读板卡探板"),
            ],
        },
        "entrypoints": [
            link_entry(SCRIPTS_ROOT / "run_openamp_demo.sh", "演示启动脚本"),
            link_entry(SCRIPTS_ROOT / "probe_openamp_board_status.py", "板卡探板 CLI"),
            link_entry(PROJECT_ROOT / "session_bootstrap" / "demo" / "openamp_control_plane_demo" / "README.md", "演示 README"),
        ],
    }


def build_docs_snapshot() -> list[dict[str, Any]]:
    return [
        link_entry(PACKAGE_ROOT / "README.md", "OpenAMP 证据包"),
        link_entry(PACKAGE_ROOT / "summary_report.md", "总报告"),
        link_entry(PACKAGE_ROOT / "coverage_matrix.md", "覆盖矩阵"),
        link_entry(PACKAGE_ROOT / "demo_four_act_runbook.md", "四幕演示脚本"),
        link_entry(PACKAGE_ROOT / "degraded_demo_plan.md", "降级演示预案"),
        link_entry(REPORTS_ROOT / "phytium_speed_test_summary_20260313_162731.md", "性能摘要"),
        link_entry(PROJECT_ROOT / "README.md", "项目 README"),
        link_entry(PROJECT_ROOT / "session_bootstrap" / "README.md", "session_bootstrap README"),
    ]


def build_snapshot(live_probe: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = parse_markdown_key_values(PACKAGE_ROOT / "summary_report.md")
    coverage = parse_markdown_key_values(PACKAGE_ROOT / "coverage_matrix.md")
    fits = build_fit_snapshot()
    performance = build_performance_snapshot()

    total_p0 = len(build_milestones_snapshot())
    total_fit_final_pass = sum(1 for fit in fits if fit["status"] == "PASS")

    return {
        "generated_at": now_iso(),
        "project": {
            "name": "TVM MetaSchedule Execution Project",
            "focus": "OpenAMP 控制面集成演示看板",
            "package_id": summary["package_id"],
            "final_verdict": summary["final_verdict"],
            "trusted_current_sha": coverage["trusted_current_sha"],
            "final_live_firmware_sha": coverage["final_live_firmware_sha"],
        },
        "mode": build_mode_snapshot(live_probe),
        "board": build_board_snapshot(live_probe),
        "stats": {
            "p0_milestones_verified": total_p0,
            "fit_final_pass_count": total_fit_final_pass,
            "payload_current_ms": performance["micro_summary"]["payload_current_ms"],
            "end_to_end_current_ms": performance["micro_summary"]["end_to_end_current_ms"],
        },
        "milestones": build_milestones_snapshot(),
        "fits": fits,
        "performance": performance,
        "guided_demo": build_guided_demo_snapshot(),
        "operator": build_operator_snapshot(),
        "docs": build_docs_snapshot(),
    }
