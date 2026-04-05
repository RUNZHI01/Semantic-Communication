from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CRYPTO_PORT = 9527
DEFAULT_STATUS_PORT = 8080
DEFAULT_OUTPUT_DIR = "/tmp/mlkem_recv"
DEFAULT_LOG_PATH = "/tmp/tcp_server.log"
DEFAULT_CIPHER_SUITE = "SM4_GCM"

LOCAL_REPO_ROOT_KEYS = ("MLKEM_LOCAL_REPO_ROOT", "MLKEM_REPO_ROOT", "COCKPIT_REPO_ROOT")
LOCAL_SCRIPT_ROOT_KEYS = ("MLKEM_SCRIPT_ROOT",)
LOCAL_CLIENT_SCRIPT_KEYS = ("MLKEM_CLIENT_SCRIPT", "MLKEM_TCP_CLIENT_SCRIPT")
LOCAL_SERVER_SCRIPT_KEYS = ("MLKEM_SERVER_SCRIPT", "MLKEM_TCP_SERVER_SCRIPT")
OQS_INSTALL_KEYS = ("OQS_INSTALL_PATH", "MLKEM_OQS_INSTALL_PATH", "MLKEM_LIBOQS_ROOT")

REMOTE_PROJECT_ROOT_KEYS = ("MLKEM_REMOTE_PROJECT_ROOT", "OPENAMP_REMOTE_PROJECT_ROOT", "REMOTE_PROJECT_ROOT")
REMOTE_SERVER_SCRIPT_KEYS = ("MLKEM_REMOTE_SERVER_SCRIPT", "MLKEM_REMOTE_TCP_SERVER_SCRIPT")
REMOTE_STARTUP_CMD_KEYS = ("MLKEM_REMOTE_STARTUP_CMD",)
REMOTE_ACTIVATE_KEYS = ("MLKEM_REMOTE_ACTIVATE",)
REMOTE_CONDA_SH_KEYS = ("MLKEM_REMOTE_CONDA_SH",)
REMOTE_CONDA_ENV_KEYS = ("MLKEM_REMOTE_CONDA_ENV",)
REMOTE_LD_LIBRARY_KEYS = ("MLKEM_REMOTE_LD_LIBRARY_PATH",)
REMOTE_TONGSUO_BRIDGE_KEYS = ("MLKEM_REMOTE_TONGSUO_KEM_BRIDGE",)
REMOTE_PRELUDE_KEYS = ("MLKEM_REMOTE_PRELUDE", "MLKEM_REMOTE_EXTRA_ENV")
REMOTE_PYTHON_KEYS = ("MLKEM_REMOTE_PYTHON", "REMOTE_TVM_PYTHON")
REMOTE_ARTIFACT_KEYS = ("REMOTE_CURRENT_ARTIFACT",)
REMOTE_TVM_PYTHON_KEYS = ("REMOTE_TVM_PYTHON",)
REMOTE_TVM_ENABLE_KEYS = ("MLKEM_ENABLE_TVM", "MLKEM_REMOTE_ENABLE_TVM")
REMOTE_PORT_KEYS = ("MLKEM_PORT", "MLKEM_SERVER_PORT", "MLKEM_DATA_PORT", "MLKEM_TCP_PORT")
STATUS_PORT_KEYS = ("MLKEM_STATUS_PORT", "MLKEM_REMOTE_STATUS_PORT")
SUITE_KEYS = ("MLKEM_CIPHER_SUITE", "MLKEM_SUITE")
REMOTE_OUTPUT_DIR_KEYS = ("MLKEM_OUTPUT_DIR",)
REMOTE_LOG_PATH_KEYS = ("MLKEM_REMOTE_LOG_PATH",)
REMOTE_SNR_KEYS = ("MLKEM_SNR", "REMOTE_SNR_CURRENT")

LOCAL_PYTHON_KEYS = ("COCKPIT_PYTHON", "PYTHON")


def _sources(env_values: Mapping[str, str] | None) -> tuple[Mapping[str, str], Mapping[str, str]]:
    return env_values or {}, os.environ


def first_config_value(
    env_values: Mapping[str, str] | None,
    *,
    keys: Sequence[str],
    default: str = "",
) -> str:
    for mapping in _sources(env_values):
        for key in keys:
            value = str(mapping.get(key, "")).strip()
            if value:
                return value
    return default


def parse_int_config(raw_value: str, default: int) -> int:
    value = str(raw_value or "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_bool_config(raw_value: str, default: bool) -> bool:
    value = str(raw_value or "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_existing_path(raw_path: str, *, base_dir: Path | None = None) -> Path | None:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        seed_dir = base_dir or PROJECT_ROOT
        candidate = (seed_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.exists():
        return candidate
    return None


def _append_unique(paths: list[Path], seen: set[Path], candidate: Path | None) -> None:
    if candidate is None:
        return
    resolved = candidate.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    paths.append(resolved)


def _candidate_base_dirs(
    env_values: Mapping[str, str] | None,
    *,
    extra_roots: Sequence[Path | str] = (),
) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    for mapping in _sources(env_values):
        for key in (*LOCAL_REPO_ROOT_KEYS, *LOCAL_SCRIPT_ROOT_KEYS):
            raw_value = str(mapping.get(key, "")).strip()
            if not raw_value:
                continue
            _append_unique(paths, seen, _resolve_existing_path(raw_value))

    for raw_root in extra_roots:
        _append_unique(paths, seen, _resolve_existing_path(str(raw_root)))

    for default_root in (PROJECT_ROOT, Path.cwd(), PROJECT_ROOT.parent, Path.cwd().parent):
        if default_root.exists():
            _append_unique(paths, seen, default_root)

    return paths


def resolve_local_asset(
    relative_path: str,
    *,
    env_values: Mapping[str, str] | None = None,
    explicit_path_keys: Sequence[str] = (),
    explicit_root_keys: Sequence[str] = (),
    extra_roots: Sequence[Path | str] = (),
) -> tuple[Path | None, list[Path]]:
    searched: list[Path] = []
    seen: set[Path] = set()
    relative = Path(relative_path)

    for mapping in _sources(env_values):
        for key in explicit_path_keys:
            raw_value = str(mapping.get(key, "")).strip()
            if not raw_value:
                continue
            candidate = _resolve_existing_path(raw_value)
            _append_unique(searched, seen, candidate or (PROJECT_ROOT / raw_value).resolve())
            if candidate is not None:
                return candidate, searched
        for key in explicit_root_keys:
            raw_value = str(mapping.get(key, "")).strip()
            if not raw_value:
                continue
            root = _resolve_existing_path(raw_value)
            if root is None:
                unresolved = (PROJECT_ROOT / raw_value).resolve()
                _append_unique(searched, seen, unresolved / relative)
                continue
            candidate = root / relative
            _append_unique(searched, seen, candidate)
            if candidate.exists():
                return candidate.resolve(), searched

    base_dirs = _candidate_base_dirs(env_values, extra_roots=extra_roots)
    for root in base_dirs:
        candidate = root / relative
        _append_unique(searched, seen, candidate)
        if candidate.exists():
            return candidate.resolve(), searched

    sibling_parents = [root.parent for root in base_dirs if root.parent.exists()]
    sibling_parent_seen: set[Path] = set()
    for sibling_parent in sibling_parents:
        resolved_parent = sibling_parent.resolve()
        if resolved_parent in sibling_parent_seen:
            continue
        sibling_parent_seen.add(resolved_parent)
        try:
            children = sorted(path for path in resolved_parent.iterdir() if path.is_dir())
        except OSError:
            continue
        for child in children:
            candidate = child / relative
            _append_unique(searched, seen, candidate)
            if candidate.exists():
                return candidate.resolve(), searched

    return None, searched


def resolve_local_crypto_client(
    env_values: Mapping[str, str] | None = None,
    *,
    extra_roots: Sequence[Path | str] = (),
) -> tuple[Path | None, list[Path]]:
    return resolve_local_asset(
        "scripts/tcp_client.py",
        env_values=env_values,
        explicit_path_keys=LOCAL_CLIENT_SCRIPT_KEYS,
        explicit_root_keys=(*LOCAL_REPO_ROOT_KEYS, *LOCAL_SCRIPT_ROOT_KEYS),
        extra_roots=extra_roots,
    )


def resolve_local_crypto_server(
    env_values: Mapping[str, str] | None = None,
    *,
    extra_roots: Sequence[Path | str] = (),
) -> tuple[Path | None, list[Path]]:
    return resolve_local_asset(
        "scripts/tcp_server.py",
        env_values=env_values,
        explicit_path_keys=LOCAL_SERVER_SCRIPT_KEYS,
        explicit_root_keys=(*LOCAL_REPO_ROOT_KEYS, *LOCAL_SCRIPT_ROOT_KEYS),
        extra_roots=extra_roots,
    )


def resolve_local_oqs_install(
    env_values: Mapping[str, str] | None = None,
    *,
    extra_roots: Sequence[Path | str] = (),
) -> tuple[Path | None, list[Path]]:
    return resolve_local_asset(
        "liboqs-dist",
        env_values=env_values,
        explicit_path_keys=OQS_INSTALL_KEYS,
        explicit_root_keys=(*LOCAL_REPO_ROOT_KEYS, *LOCAL_SCRIPT_ROOT_KEYS),
        extra_roots=extra_roots,
    )


def build_local_crypto_client_command(
    env_values: Mapping[str, str] | None,
    *,
    host: str,
    input_path: Path,
    client_script: Path,
) -> tuple[list[str], dict[str, str]]:
    python_command = first_config_value(env_values, keys=LOCAL_PYTHON_KEYS, default=sys.executable or "python3")
    suite = first_config_value(env_values, keys=SUITE_KEYS, default=DEFAULT_CIPHER_SUITE)
    crypto_port = parse_int_config(
        first_config_value(env_values, keys=REMOTE_PORT_KEYS),
        DEFAULT_CRYPTO_PORT,
    )

    env = dict(os.environ)
    oqs_install = first_config_value(env_values, keys=OQS_INSTALL_KEYS)
    if oqs_install:
        env["OQS_INSTALL_PATH"] = oqs_install
    else:
        detected_oqs_root, _ = resolve_local_oqs_install(env_values, extra_roots=(client_script.parent.parent,))
        if detected_oqs_root is not None:
            env["OQS_INSTALL_PATH"] = str(detected_oqs_root)

    command = [
        python_command,
        str(client_script),
        "--host",
        host,
        "--port",
        str(crypto_port),
        "--input",
        str(input_path),
        "--suite",
        suite,
    ]
    return command, env


def _derive_remote_server_script(
    env_values: Mapping[str, str] | None,
    *,
    local_server_script: Path | None,
) -> str:
    explicit_remote_script = first_config_value(env_values, keys=REMOTE_SERVER_SCRIPT_KEYS)
    if explicit_remote_script:
        return explicit_remote_script

    remote_project_root = first_config_value(env_values, keys=REMOTE_PROJECT_ROOT_KEYS)
    if remote_project_root:
        if local_server_script is not None:
            try:
                relative_script = local_server_script.resolve().relative_to(local_server_script.resolve().parents[1])
            except ValueError:
                relative_script = Path("scripts/tcp_server.py")
        else:
            relative_script = Path("scripts/tcp_server.py")
        return f"{remote_project_root.rstrip('/')}/{relative_script.as_posix()}"

    return "~/tcp_server.py"


def build_remote_crypto_server_command(
    env_values: Mapping[str, str] | None,
    *,
    local_server_script: Path | None = None,
) -> str:
    explicit_command = first_config_value(env_values, keys=REMOTE_STARTUP_CMD_KEYS)
    if explicit_command:
        return explicit_command

    remote_python = first_config_value(env_values, keys=REMOTE_PYTHON_KEYS, default="python3")
    remote_server_script = _derive_remote_server_script(env_values, local_server_script=local_server_script)
    suite = first_config_value(env_values, keys=SUITE_KEYS, default=DEFAULT_CIPHER_SUITE)
    output_dir = first_config_value(env_values, keys=REMOTE_OUTPUT_DIR_KEYS, default=DEFAULT_OUTPUT_DIR)
    log_path = first_config_value(env_values, keys=REMOTE_LOG_PATH_KEYS, default=DEFAULT_LOG_PATH)
    crypto_port = parse_int_config(first_config_value(env_values, keys=REMOTE_PORT_KEYS), DEFAULT_CRYPTO_PORT)
    status_port_raw = first_config_value(env_values, keys=STATUS_PORT_KEYS)
    enable_tvm = parse_bool_config(first_config_value(env_values, keys=REMOTE_TVM_ENABLE_KEYS), True)

    server_argv: list[str] = [
        remote_python,
        remote_server_script,
        "--host",
        "0.0.0.0",
        "--port",
        str(crypto_port),
        "--output-dir",
        output_dir,
        "--suite",
        suite,
    ]
    if status_port_raw:
        server_argv.extend(["--status-port", str(parse_int_config(status_port_raw, DEFAULT_STATUS_PORT))])
    else:
        server_argv.extend(["--status-port", str(DEFAULT_STATUS_PORT)])
    if enable_tvm:
        server_argv.append("--tvm")
        remote_tvm_python = first_config_value(env_values, keys=REMOTE_TVM_PYTHON_KEYS)
        if remote_tvm_python:
            server_argv.extend(["--tvm-python", remote_tvm_python])
        remote_artifact = first_config_value(env_values, keys=REMOTE_ARTIFACT_KEYS)
        if remote_artifact:
            server_argv.extend(["--artifact-path", remote_artifact])
        snr = first_config_value(env_values, keys=REMOTE_SNR_KEYS, default="10")
        server_argv.extend(["--snr", snr])

    command_steps: list[str] = []
    # 仅在 remote_python 不是绝对路径时才需要 conda activate（绝对路径已自带环境，无需激活）
    remote_python_is_abs = remote_python.startswith("/")
    activate_command = first_config_value(env_values, keys=REMOTE_ACTIVATE_KEYS)
    if activate_command and not remote_python_is_abs:
        command_steps.append(activate_command)
    elif not remote_python_is_abs:
        conda_env = first_config_value(env_values, keys=REMOTE_CONDA_ENV_KEYS)
        conda_sh = first_config_value(env_values, keys=REMOTE_CONDA_SH_KEYS)
        if conda_env and conda_sh:
            command_steps.append(
                f"if [ -f {shlex.quote(conda_sh)} ]; then . {shlex.quote(conda_sh)} && "
                f"conda activate {shlex.quote(conda_env)}; fi"
            )
        elif conda_env:
            command_steps.append(
                "if command -v conda >/dev/null 2>&1; then "
                f'eval "$(conda shell.bash hook)" >/dev/null 2>&1 && conda activate {shlex.quote(conda_env)}; fi'
            )

    ld_library_path = first_config_value(env_values, keys=REMOTE_LD_LIBRARY_KEYS)
    if ld_library_path:
        command_steps.append(
            f"export LD_LIBRARY_PATH={shlex.quote(ld_library_path)}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"
        )

    tongsuo_bridge = first_config_value(env_values, keys=REMOTE_TONGSUO_BRIDGE_KEYS)
    if tongsuo_bridge:
        command_steps.append(f"export TONGSUO_KEM_BRIDGE={shlex.quote(tongsuo_bridge)}")

    remote_prelude = first_config_value(env_values, keys=REMOTE_PRELUDE_KEYS)
    if remote_prelude:
        command_steps.append(remote_prelude)

    server_command = " ".join(shlex.quote(str(arg)) for arg in server_argv)
    command_steps.append(f"nohup {server_command} </dev/null > {shlex.quote(log_path)} 2>&1 &")
    return f"bash -c {shlex.quote('; '.join(command_steps))}"


def run_ssh_command(
    *,
    host: str,
    user: str,
    password: str,
    port: str | int,
    remote_command: str,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    ssh_command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "BatchMode=no",
        "-o",
        "PreferredAuthentications=password,keyboard-interactive",
        "-p",
        str(port),
        f"{user}@{host}",
        remote_command,
    ]
    env = dict(os.environ)
    askpass_path: Path | None = None

    if password and shutil.which("sshpass"):
        env["SSHPASS"] = password
        command = ["sshpass", "-e", *ssh_command]
    elif password:
        fd, raw_path = tempfile.mkstemp(prefix="mlkem-askpass-", suffix=".sh", text=True)
        askpass_path = Path(raw_path)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\n")
            handle.write(f"printf '%s\\n' {shlex.quote(password)}\n")
        askpass_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        env["SSH_ASKPASS"] = str(askpass_path)
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env.setdefault("DISPLAY", "codex-askpass:0")
        command = ssh_command
    else:
        command = ssh_command

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    finally:
        if askpass_path is not None:
            try:
                askpass_path.unlink()
            except OSError:
                pass
