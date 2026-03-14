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

from board_probe import run_live_probe
from demo_data import PROJECT_ROOT, build_snapshot, read_text, repo_relative, resolve_repo_path


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
        default=10.0,
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


class DashboardState:
    def __init__(self, probe_env: str | None, probe_timeout_sec: float) -> None:
        self._probe_env = probe_env or None
        self._probe_timeout_sec = probe_timeout_sec
        self._lock = Lock()
        self._last_live_probe: dict[str, Any] | None = None

    def current_snapshot(self) -> dict[str, Any]:
        with self._lock:
            live_probe = self._last_live_probe
        return build_snapshot(live_probe=live_probe)

    def refresh_live_probe(self) -> dict[str, Any]:
        result = run_live_probe(env_file=self._probe_env, timeout_sec=self._probe_timeout_sec)
        with self._lock:
            self._last_live_probe = result
        return result


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
        if parsed.path == "/api/health":
            self.respond_json(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/docs":
            self.respond_doc_view(parsed.query)
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/probe-board":
            payload = self.server.app_state.refresh_live_probe()
            self.respond_json(HTTPStatus.OK, payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(repo_relative(path))}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      background: linear-gradient(180deg, #f6f1e7 0%, #fdfcf8 100%);
      color: #11263c;
    }}
    header {{
      padding: 1.5rem 2rem 1rem;
      border-bottom: 1px solid rgba(17, 38, 60, 0.12);
      background: rgba(255, 255, 255, 0.72);
      backdrop-filter: blur(18px);
      position: sticky;
      top: 0;
    }}
    a {{
      color: #c55a11;
      text-decoration: none;
      font-weight: 700;
    }}
    main {{
      padding: 1.5rem 2rem 2rem;
    }}
    pre {{
      margin: 0;
      overflow: auto;
      padding: 1.25rem;
      border-radius: 16px;
      background: #0f2436;
      color: #f7efe3;
      box-shadow: 0 24px 80px rgba(15, 36, 54, 0.12);
      line-height: 1.55;
      font-size: 0.92rem;
    }}
    .path {{
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      font-size: 1.3rem;
      margin-bottom: 0.5rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="path">{html.escape(repo_relative(path))}</div>
    <a href="/">Back to dashboard</a>
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
