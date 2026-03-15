from __future__ import annotations

from typing import Any


_AUTH_PATTERNS = (
    "permission denied",
    "publickey,password",
    "please try again",
    "authentication failed",
    "access denied",
)

_CONFIG_PATTERNS = (
    "no such file or directory",
    "could not resolve hostname",
    "name or service not known",
    "host key verification failed",
    "connection refused",
    "no route to host",
    "network is unreachable",
    "bad configuration option",
)

_TIMEOUT_PATTERNS = (
    "timed out",
    "timeout",
)

_MESSAGE_TEMPLATES = {
    "probe": {
        "auth_error": "板卡 SSH 认证失败，请检查用户名、密码或 SSH 端口设置。",
        "config_error": "板卡探测配置不可用，请检查环境文件、主机和端口设置。",
        "timeout": "板卡探测超时，请确认板卡在线后重试。",
        "error": "板卡探测失败，请查看诊断信息。",
    },
    "inference": {
        "auth_error": "远端推理认证失败，请检查板卡用户名、密码或 SSH 端口设置。",
        "config_error": "远端推理配置不完整或不可用，请检查连接信息和推理环境参数。",
        "timeout": "远端推理超时，请确认板卡在线后重试。",
        "error": "远端推理执行失败，请查看诊断信息。",
    },
    "status": {
        "auth_error": "远端状态查询认证失败，请检查板卡用户名、密码或 SSH 端口设置。",
        "config_error": "远端状态查询配置不可用，请检查板卡连接信息和本机脚本环境。",
        "timeout": "远端状态查询超时，请确认板卡在线后重试。",
        "error": "远端状态查询失败，请查看诊断信息。",
    },
    "fault": {
        "auth_error": "远端故障注入认证失败，请检查板卡用户名、密码或 SSH 端口设置。",
        "config_error": "远端故障注入配置不可用，请检查板卡连接信息和本机脚本环境。",
        "timeout": "远端故障注入超时，请确认板卡在线后重试。",
        "error": "远端故障注入失败，请查看诊断信息。",
    },
    "recover": {
        "auth_error": "远端恢复认证失败，请检查板卡用户名、密码或 SSH 端口设置。",
        "config_error": "远端恢复配置不可用，请检查板卡连接信息和本机脚本环境。",
        "timeout": "远端恢复超时，请确认板卡在线后重试。",
        "error": "远端恢复失败，请查看诊断信息。",
    },
}

_FALLBACK_SUFFIX = {
    "inference": " 当前已回退到预录结果。",
    "fault": " 当前已切换到回放结果。",
    "recover": " 当前已切换到安全恢复回放。",
}

_ACTION_KIND = {
    "probe": "probe",
    "inference": "inference",
    "status": "status",
    "wrong_sha": "fault",
    "illegal_param": "fault",
    "heartbeat_timeout": "fault",
    "recover": "recover",
}


def _normalize_text(*values: str) -> str:
    return "\n".join(str(value or "").strip().lower() for value in values if str(value or "").strip())


def classify_status_category(
    *,
    status: str,
    stdout: str = "",
    stderr: str = "",
    error: str = "",
    missing_fields: list[str] | None = None,
) -> str:
    if status == "success":
        return "success"
    if status == "timeout":
        return "timeout"
    if missing_fields:
        return "config_error"

    text = _normalize_text(stderr, stdout, error)
    if any(pattern in text for pattern in _AUTH_PATTERNS):
        return "auth_error"
    if any(pattern in text for pattern in _TIMEOUT_PATTERNS):
        return "timeout"
    if status == "launch_error":
        return "config_error"
    if any(pattern in text for pattern in _CONFIG_PATTERNS):
        return "config_error"
    return "error"


def build_operator_message(action: str, status_category: str, *, include_fallback: bool = False) -> str:
    action_kind = _ACTION_KIND.get(action, action)
    templates = _MESSAGE_TEMPLATES.get(action_kind, _MESSAGE_TEMPLATES["status"])
    message = templates.get(status_category, templates["error"])
    if include_fallback:
        message += _FALLBACK_SUFFIX.get(action_kind, "")
    return message


def build_diagnostics(
    *,
    stdout: str = "",
    stderr: str = "",
    error: str = "",
    returncode: int | None = None,
    missing_fields: list[str] | None = None,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    if stdout.strip():
        diagnostics["stdout"] = stdout.strip()
    if stderr.strip():
        diagnostics["stderr"] = stderr.strip()
    if error.strip():
        diagnostics["error"] = error.strip()
    if returncode is not None:
        diagnostics["returncode"] = returncode
    if missing_fields:
        diagnostics["missing_fields"] = list(missing_fields)
    return diagnostics
