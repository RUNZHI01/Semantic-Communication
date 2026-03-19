#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse

from archive_replay import ArchiveSessionNotFoundError, list_archive_sessions, load_archive_session
from board_access import BoardAccessConfig, build_board_access_config, build_demo_default_board_access
from board_probe import DEFAULT_LIVE_PROBE_OUTPUT, is_successful_probe, load_probe_output, run_live_probe, write_probe_output
from demo_data import (
    PROJECT_ROOT,
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
    launch_remote_reconstruction_job,
    load_signed_manifest_summary,
)


STATIC_ROOT = Path(__file__).resolve().parent / "static"


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
        self._last_fault_result: dict[str, Any] | None = None
        self._inference_jobs: dict[str, dict[str, Any]] = {}
        self._manifest_preview_count = 0
        self._link_director = default_link_director_state()
        self._event_spine = DemoEventSpine(event_archive_root)

        cached_probe = load_probe_output(probe_cache_path) if probe_cache_path else None
        if is_successful_probe(cached_probe):
            self._last_live_probe = {**cached_probe, "_loaded_from_cache": True}
        else:
            self._last_live_probe = None

        initial_snapshot = build_snapshot(self._last_live_probe)
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
        return config.to_public_dict()

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
        return build_snapshot(live_probe=live_probe)

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

    def current_system_status(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
            board_access = self._board_access
            control_status = self._last_control_status
            last_inference = self._last_inference_result
            last_fault = self._last_fault_result

        snapshot = build_snapshot(live_probe=live_probe)
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

        return {
            "generated_at": snapshot["generated_at"],
            "board_access": board_access.to_public_dict(),
            "execution_mode": {
                "label": mode_label,
                "tone": mode_tone,
                "summary": mode_summary,
            },
            "live": {
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
            },
            "active_inference": active_inference,
            "last_inference": last_inference or {},
            "last_fault": last_fault or {},
            "job_manifest_gate": self._job_manifest_gate_status(
                board_access=current_board_access,
                admission=admission,
                support=current_support,
                active_inference=active_inference,
                control_status=control_status,
                trusted_sha=self._trusted_current_sha,
                variant="current",
            ),
            "event_spine": {
                "api_path": "/api/event-spine",
                "session_id": event_spine["session_id"],
                "event_count": event_spine["aggregate"]["event_count"],
                "last_event_at": event_spine["aggregate"]["last_event_at"],
                "archive_enabled": event_spine["aggregate"]["archive"]["enabled"],
            },
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
        payload = build_prerecorded_inference_result(image_index, variant)
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

    def run_demo_inference(self, *, variant: str, image_index: int) -> dict[str, Any]:
        payload = build_prerecorded_inference_result(image_index, variant)
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
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self.read_json_body()
        if body is None:
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
            payload = self.server.app_state.run_demo_inference(variant=variant, image_index=image_index)
            self.respond_json(HTTPStatus.OK, payload)
            return
        if parsed.path == "/api/run-baseline":
            image_index = self.coerce_int(body.get("image_index"), default=0)
            payload = self.server.app_state.run_demo_inference(variant="baseline", image_index=image_index)
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
