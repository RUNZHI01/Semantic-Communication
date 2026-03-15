#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import mimetypes
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse

from board_access import build_board_access_config, build_demo_default_board_access
from board_probe import DEFAULT_LIVE_PROBE_OUTPUT, is_successful_probe, load_probe_output, run_live_probe, write_probe_output
from demo_data import (
    PROJECT_ROOT,
    build_fault_replay,
    build_prerecorded_inference_result,
    build_recover_replay,
    build_snapshot,
    read_text,
    repo_relative,
    resolve_repo_path,
)
from fault_injector import query_live_status, run_fault_action, run_recover_action
from inference_runner import launch_remote_reconstruction_job


STATIC_ROOT = Path(__file__).resolve().parent / "static"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the integrated OpenAMP demo dashboard.")
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


class DashboardState:
    def __init__(
        self,
        probe_env: str | None,
        probe_timeout_sec: float,
        probe_cache_path: str | Path | None = DEFAULT_LIVE_PROBE_OUTPUT,
    ) -> None:
        self._probe_env = probe_env or None
        self._probe_timeout_sec = probe_timeout_sec
        self._probe_cache_path = probe_cache_path
        self._lock = Lock()
        self._board_access = build_demo_default_board_access(self._probe_env)
        self._last_control_status: dict[str, Any] | None = None
        self._last_inference_result: dict[str, Any] | None = None
        self._last_fault_result: dict[str, Any] | None = None
        self._inference_jobs: dict[str, dict[str, Any]] = {}

        cached_probe = load_probe_output(probe_cache_path) if probe_cache_path else None
        if is_successful_probe(cached_probe):
            self._last_live_probe = {**cached_probe, "_loaded_from_cache": True}
        else:
            self._last_live_probe = None

        initial_snapshot = build_snapshot(self._last_live_probe)
        self._trusted_current_sha = initial_snapshot["project"]["trusted_current_sha"]
        self._target_label = "cortex-a72 + neon"
        self._runtime_label = "tvm"

    def set_board_access(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            fallback = self._board_access
        config = build_board_access_config(payload, fallback=fallback)
        with self._lock:
            self._board_access = config
        return config.to_public_dict()

    def current_snapshot(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
        return build_snapshot(live_probe=live_probe)

    def current_system_status(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
            board_access = self._board_access
            control_status = self._last_control_status
            last_inference = self._last_inference_result
            last_fault = self._last_fault_result

        snapshot = build_snapshot(live_probe=live_probe)
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

        board_online = bool(live_probe and live_probe.get("reachable"))
        if board_online:
            mode_label = "在线模式"
            mode_tone = "online"
            mode_summary = "板卡 SSH 与 RPMsg 读数可用，第二幕会展示真实在线推进。"
        elif board_access.connection_ready:
            mode_label = "降级模式"
            mode_tone = "degraded"
            mode_summary = "本场会话已就绪；若真机链路暂不可用，界面会明确切回归档证据。"
        elif board_access.has_preloaded_defaults and board_access.missing_connection_fields() == ["password"]:
            mode_label = "待补全密码"
            mode_tone = "degraded"
            mode_summary = "SSH 与推理默认值已预载；补一次密码即可触发真机动作。"
        elif board_access.configured:
            mode_label = "待补全会话"
            mode_tone = "degraded"
            mode_summary = "已接入部分会话信息；补齐缺失字段后即可尝试真机动作。"
        else:
            mode_label = "离线模式"
            mode_tone = "offline"
            mode_summary = "尚未配置板卡会话，当前只展示证据与预录结果。"

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
                "last_probe_at": live_probe.get("requested_at", "") if live_probe else "",
                "status_source": status_source,
                "status_note": status_note,
            },
            "last_inference": last_inference or {},
            "last_fault": last_fault or {},
        }

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
                status_payload = query_live_status(board_access, trusted_sha=self._trusted_current_sha)
                if status_payload.get("status") == "success":
                    with self._lock:
                        self._last_control_status = status_payload
                result["control_status"] = status_payload
        return result

    def _build_inference_response(self, record: dict[str, Any], live_attempt: dict[str, Any]) -> dict[str, Any]:
        variant = str(record["variant"])
        image_index = int(record["image_index"])
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
                    "source_label": "真实在线推进",
                    "message": "OpenAMP 控制面已接入本次演示，界面正在同步板端推进阶段。",
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
                    "source_label": "真实在线推进 + 归档样例图",
                    "message": (
                        "本次演示已通过 OpenAMP 控制面完成作业下发、板端执行与结果回收；图像对比继续使用归档样例，"
                        "现场呈现更稳定。"
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
                "source_label": "回退展示（归档样例）",
                "message": (
                    f"{live_attempt.get('message', '在线推进未完成')} 当前画面已切回归档样例，"
                    "上方阶段条保留本次真机推进停留点。"
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

    def run_demo_inference(self, *, variant: str, image_index: int) -> dict[str, Any]:
        payload = build_prerecorded_inference_result(image_index, variant)
        with self._lock:
            board_access = self._board_access

        if board_access.configured:
            live_job = launch_remote_reconstruction_job(board_access, variant=variant)
            live_result = live_job.snapshot()
            record = {
                "job": live_job,
                "job_id": live_job.job_id,
                "variant": variant,
                "image_index": image_index,
            }
            with self._lock:
                self._inference_jobs[live_job.job_id] = record
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
                        "percent": 100,
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
        return payload

    def get_inference_progress(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._inference_jobs.get(job_id)
        if record is None:
            raise KeyError(job_id)
        payload = self._build_inference_response(record, record["job"].snapshot())
        with self._lock:
            if payload.get("request_state") == "completed":
                self._update_last_inference_summary(payload, record["variant"])
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
        if parsed.path == "/api/probe-board":
            payload = self.server.app_state.refresh_live_probe()
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
    app_state = DashboardState(args.probe_env, args.probe_timeout_sec)
    if args.probe_startup:
        app_state.refresh_live_probe()
    server = DemoHTTPServer((args.host, args.port), DemoRequestHandler, app_state)
    print(f"OpenAMP demo dashboard: http://{args.host}:{args.port}")
    print(f"Project root: {PROJECT_ROOT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
