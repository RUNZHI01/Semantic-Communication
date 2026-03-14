from __future__ import annotations

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
        if target.startswith("http://") or target.startswith("https://"):
            links.append({"label": label, "path": target, "external": True})
            continue
        resolved = (base_dir / target).resolve()
        links.append({"label": label, "path": repo_relative(resolved), "external": False})
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
        links.append(link_entry(resolve_repo_path(raw), key.replace("_", " ")))
    return {
        "fit_id": payload["fit_id"],
        "status": payload["status"],
        "scenario": payload["scenario"],
        "risk_item": payload["risk_item"],
        "trusted_current_sha": payload.get("trusted_current_sha", ""),
        "live_firmware_sha256": payload.get("live_firmware_sha256", ""),
        "generated_at": payload["generated_at"],
        "board_access": payload.get("board_access", {}),
        "observed_result": payload.get("observed_result", {}),
        "conclusion": payload.get("conclusion", ""),
        "evidence": links,
        "run_id": payload["run_id"],
    }


def synthesize_fit_readout(summary: dict[str, Any]) -> str:
    fit_id = summary["fit_id"]
    observed = summary.get("observed_result", {})
    if fit_id == "FIT-01":
        return (
            f"Decision {observed.get('decision', 'UNKNOWN')}; "
            f"fault {observed.get('fault_name', 'UNKNOWN')}; "
            f"guard stayed {observed.get('guard_final', 'UNKNOWN')}."
        )
    if fit_id == "FIT-02":
        return (
            f"Decision {observed.get('decision', 'UNKNOWN')}; "
            f"fault {observed.get('fault_name', 'UNKNOWN')}; "
            f"wrapper result {observed.get('wrapper_result', 'UNKNOWN')}."
        )
    timeout_status = observed.get("timeout_status") or observed.get("status_after_5s_without_heartbeat") or {}
    return (
        f"Timeout status {format_guard_state(timeout_status.get('guard_state'))}; "
        f"fault {format_fault_code(timeout_status.get('last_fault_code'))}; "
        f"active_job_id={timeout_status.get('active_job_id', 'NA')}."
    )


def build_mode_snapshot(live_probe: dict[str, Any] | None) -> dict[str, Any]:
    materials = parse_markdown_key_values(PACKAGE_ROOT / "demo_materials_index.md")
    has_live = bool(live_probe and live_probe.get("reachable"))
    if has_live:
        effective_label = "Live cue active"
        effective_tone = "live"
        summary = (
            "A fresh read-only SSH probe is available. The dashboard is still evidence-led, "
            "but it can show a current board read without touching the control flow."
        )
    else:
        effective_label = "Fallback evidence mode"
        effective_tone = "fallback"
        summary = (
            "No fresh live probe is attached. The dashboard renders the board-backed evidence "
            "package and last proven control-plane state."
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
        "label": "Board-backed ready state proved",
        "summary": (
            "The control plane was proven on real hardware through JOB_DONE cleanup and the "
            "post-fix FIT-03 timeout path. Current evidence shows the board can return to READY "
            "without rebooting."
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
            link_entry(REPORTS_ROOT / "openamp_phase5_job_done_success_2026-03-15.md", "job done summary"),
            link_entry(REPORTS_ROOT / "openamp_phase5_fit03_watchdog_success_2026-03-15.md", "fit-03 post-fix summary"),
            link_entry(REPORTS_ROOT / "openamp_job_done_real_probe_20260315_001.json", "job done raw probe"),
            link_entry(
                REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "remote_probe.json",
                "fit-03 post-fix remote probe",
            ),
        ],
        "history_note": fit03_fail["conclusion"],
    }

    if live_probe and live_probe.get("reachable"):
        current = {
            "label": "Fresh read-only SSH probe",
            "summary": live_probe.get("summary", ""),
            "reachable": True,
            "requested_at": live_probe.get("requested_at", ""),
            "details": live_probe.get("details", {}),
            "evidence": [],
        }
    else:
        reason = live_probe.get("error", "") if live_probe else "No live probe executed."
        current = {
            "label": "No fresh live probe",
            "summary": reason or "Using last proven evidence instead of a live board read.",
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
            "coverage_item": "cold boot / remoteproc / rpmsg demo gate",
            "mapped_id": "bring-up gate",
            "status": "PASS",
            "key_proof_point": (
                "release_v1.4.0-derived firmware cleared the board boot, remoteproc, and RPMsg "
                "demo entry gate before the finer control-plane milestones were collected."
            ),
            "evidence": [
                link_entry(
                    REPORTS_ROOT / "openamp_phase5_release_v1.4.0_cold_boot_and_demo_success_2026-03-14.md",
                    "cold boot summary",
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
                "coverage_item": row["Coverage Item"].strip("`"),
                "mapped_id": row["Mapped ID"].strip("`"),
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
        "label": "pre-fix history",
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
            "The same trusted current SHA used by the OpenAMP FITs is also backed by the latest "
            "validated decoder performance reports. The OpenAMP wrapper only gates admission and "
            "status; it does not replace the existing inference data path."
        ),
        "metrics": [
            {
                "label": "Payload median",
                "current": f"{payload['current_run_median_ms']} ms",
                "baseline": f"{payload['baseline_run_median_ms']} ms",
                "improvement": f"{payload['improvement_pct']}%",
                "report": link_entry(
                    REPORTS_ROOT / "inference_compare_currentsafe_chunk4_refresh_20260313_1758.md",
                    "payload compare report",
                ),
                "delta_ms": payload["delta_ms_current_minus_baseline"],
            },
            {
                "label": "End-to-end median",
                "current": f"{end_to_end['current_run_median_ms']} ms/image",
                "baseline": f"{end_to_end['baseline_run_median_ms']} ms/image",
                "improvement": f"{end_to_end['improvement_pct']}%",
                "report": link_entry(
                    REPORTS_ROOT / "inference_real_reconstruction_compare_currentsafe_chunk4_refresh_20260313_1758.md",
                    "end-to-end compare report",
                ),
                "delta_ms": end_to_end["delta_ms_current_minus_baseline"],
            },
            {
                "label": "Incremental tuning speedup",
                "current": speedup["incremental_speedup_vs_rebuild_only"],
                "baseline": "rebuild-only current",
                "improvement": speedup["incremental_improvement_vs_rebuild_only"],
                "report": link_entry(
                    REPORTS_ROOT / "current_scheme_b_compare_20260311_195303.md",
                    "current-only speedup report",
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
                "The host side reads the evidence package, raw JSON probes, performance reports, "
                "and wrapper summaries already stored in this repo."
            ),
            "items": [
                link_entry(PACKAGE_ROOT / "README.md", "evidence package index"),
                link_entry(PACKAGE_ROOT / "coverage_matrix.md", "coverage matrix"),
                link_entry(PACKAGE_ROOT / "demo_materials_index.md", "demo materials index"),
                link_entry(SCRIPTS_ROOT / "openamp_control_wrapper.py", "control wrapper"),
                link_entry(SCRIPTS_ROOT / "openamp_rpmsg_bridge.py", "rpmsg bridge"),
            ],
        },
        "slave_side": {
            "summary": (
                "The slave/OpenAMP side depends on the live firmware and Linux RPMsg transport that "
                "were already verified in the board-backed reports. The optional live probe only "
                "reads hostname, remoteproc state, RPMsg devices, and firmware SHA."
            ),
            "items": [
                link_entry(REPORTS_ROOT / "openamp_phase5_fit03_watchdog_success_2026-03-15.md", "fit-03 post-fix summary"),
                link_entry(
                    REPORTS_ROOT / "openamp_heartbeat_timeout_fit_watchdogfix_20260315_023410" / "remote_probe.json",
                    "fit-03 post-fix remote probe",
                ),
                link_entry(SCRIPTS_ROOT / "connect_phytium_pi.sh", "ssh connector"),
                link_entry(SCRIPTS_ROOT / "probe_openamp_board_status.py", "read-only board probe"),
            ],
        },
        "entrypoints": [
            link_entry(SCRIPTS_ROOT / "run_openamp_demo.sh", "demo launcher"),
            link_entry(SCRIPTS_ROOT / "probe_openamp_board_status.py", "board probe CLI"),
            link_entry(PROJECT_ROOT / "session_bootstrap" / "demo" / "openamp_control_plane_demo" / "README.md", "demo README"),
        ],
    }


def build_docs_snapshot() -> list[dict[str, Any]]:
    return [
        link_entry(PACKAGE_ROOT / "README.md", "OpenAMP evidence package"),
        link_entry(PACKAGE_ROOT / "summary_report.md", "summary report"),
        link_entry(PACKAGE_ROOT / "coverage_matrix.md", "coverage matrix"),
        link_entry(PACKAGE_ROOT / "demo_four_act_runbook.md", "four-act runbook"),
        link_entry(PACKAGE_ROOT / "degraded_demo_plan.md", "degraded demo plan"),
        link_entry(REPORTS_ROOT / "phytium_speed_test_summary_20260313_162731.md", "speed summary"),
        link_entry(PROJECT_ROOT / "README.md", "project README"),
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
            "focus": "OpenAMP control-plane integrated demo surface",
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
        "operator": build_operator_snapshot(),
        "docs": build_docs_snapshot(),
    }
