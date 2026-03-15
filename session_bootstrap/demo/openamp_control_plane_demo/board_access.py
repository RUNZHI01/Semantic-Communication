from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

HOST_KEYS = ("REMOTE_HOST", "PHYTIUM_PI_HOST")
USER_KEYS = ("REMOTE_USER", "PHYTIUM_PI_USER")
PASSWORD_KEYS = ("REMOTE_PASS", "PHYTIUM_PI_PASSWORD")
PORT_KEYS = ("REMOTE_SSH_PORT", "PHYTIUM_PI_PORT")

INFERENCE_SHARED_REQUIRED_KEYS = (
    "REMOTE_TVM_PYTHON",
    "REMOTE_INPUT_DIR",
    "REMOTE_OUTPUT_BASE",
)
INFERENCE_VARIANT_REQUIRED_KEYS = {
    "baseline": ("REMOTE_SNR_BASELINE", "REMOTE_BATCH_BASELINE"),
    "current": ("REMOTE_SNR_CURRENT", "REMOTE_BATCH_CURRENT"),
}


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_local_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / raw_path).resolve()
    else:
        path = path.resolve()
    return path


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env_file(raw_path: str | None) -> tuple[Path | None, dict[str, str]]:
    if not raw_path:
        return None, {}
    path = resolve_local_path(raw_path.strip())
    if not path.exists() or not path.is_file():
        raise ValueError(f"env 文件不存在: {repo_relative(path)}")
    return path, parse_env_text(path.read_text(encoding="utf-8"))


def first_non_empty(mapping: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(mapping.get(key, "")).strip()
        if value:
            return value
    return ""


def normalize_port(raw: str) -> str:
    value = (raw or "22").strip() or "22"
    try:
        port = int(value)
    except ValueError as err:
        raise ValueError("SSH 端口必须是整数。") from err
    if port < 1 or port > 65535:
        raise ValueError("SSH 端口必须在 1 到 65535 之间。")
    return str(port)


@dataclass(frozen=True)
class BoardAccessConfig:
    host: str
    user: str
    password: str
    port: str
    env_file: Path | None
    env_values: dict[str, str]
    source_summary: str

    @property
    def configured(self) -> bool:
        return bool(self.host or self.user or self.password or self.env_file)

    @property
    def connection_ready(self) -> bool:
        return bool(self.host and self.user and self.password)

    @property
    def probe_ready(self) -> bool:
        return self.connection_ready

    def missing_connection_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.host:
            missing.append("host")
        if not self.user:
            missing.append("user")
        if not self.password:
            missing.append("password")
        return missing

    def missing_inference_fields(self, variant: str) -> list[str]:
        missing = self.missing_connection_fields()
        for key in INFERENCE_SHARED_REQUIRED_KEYS + INFERENCE_VARIANT_REQUIRED_KEYS.get(variant, ()):
            if not str(self.env_values.get(key, "")).strip():
                missing.append(key)
        return missing

    def build_env(self) -> dict[str, str]:
        values = dict(self.env_values)
        if self.host:
            values["REMOTE_HOST"] = self.host
            values["PHYTIUM_PI_HOST"] = self.host
        if self.user:
            values["REMOTE_USER"] = self.user
            values["PHYTIUM_PI_USER"] = self.user
        if self.password:
            values["REMOTE_PASS"] = self.password
            values["PHYTIUM_PI_PASSWORD"] = self.password
        if self.port:
            values["REMOTE_SSH_PORT"] = self.port
            values["PHYTIUM_PI_PORT"] = self.port
        return values

    def build_subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self.build_env())
        return env

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "connection_ready": self.connection_ready,
            "probe_ready": self.probe_ready,
            "inference_ready": not self.missing_inference_fields("current"),
            "host": self.host,
            "user": self.user,
            "port": int(self.port),
            "env_file": repo_relative(self.env_file) if self.env_file else "",
            "has_password": bool(self.password),
            "missing_connection_fields": self.missing_connection_fields(),
            "missing_inference_fields": self.missing_inference_fields("current"),
            "source_summary": self.source_summary,
        }


def build_board_access_config(payload: dict[str, Any]) -> BoardAccessConfig:
    raw_payload = {str(key): str(value or "").strip() for key, value in payload.items()}
    env_file, env_values = load_env_file(raw_payload.get("env_file"))

    host = raw_payload.get("host") or first_non_empty(env_values, HOST_KEYS)
    user = raw_payload.get("user") or first_non_empty(env_values, USER_KEYS)
    password = raw_payload.get("password") or first_non_empty(env_values, PASSWORD_KEYS)
    port = normalize_port(raw_payload.get("port") or first_non_empty(env_values, PORT_KEYS) or "22")

    merged_env = dict(env_values)
    if host:
        merged_env["REMOTE_HOST"] = host
        merged_env["PHYTIUM_PI_HOST"] = host
    if user:
        merged_env["REMOTE_USER"] = user
        merged_env["PHYTIUM_PI_USER"] = user
    if password:
        merged_env["REMOTE_PASS"] = password
        merged_env["PHYTIUM_PI_PASSWORD"] = password
    merged_env["REMOTE_SSH_PORT"] = port
    merged_env["PHYTIUM_PI_PORT"] = port

    source_parts: list[str] = []
    if env_file:
        source_parts.append(f"env 文件 {repo_relative(env_file)}")
    if any(raw_payload.get(field) for field in ("host", "user", "password", "port")):
        source_parts.append("网页表单")
    if not source_parts:
        source_parts.append("未配置")

    return BoardAccessConfig(
        host=host,
        user=user,
        password=password,
        port=port,
        env_file=env_file,
        env_values=merged_env,
        source_summary=" + ".join(source_parts),
    )
