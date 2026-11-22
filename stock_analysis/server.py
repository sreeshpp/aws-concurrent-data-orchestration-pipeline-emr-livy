"""Serve Fact Desk. No market-data calls and no model calls."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from stock_analysis.report import ReportError, build_report

ROOT = Path(__file__).resolve().parent / "static"
MAX_BODY = 8_192

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class DeskHandler(BaseHTTPRequestHandler):
    server_version = "FactDesk/0.1"

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/api/health":
            self._json(200, {"status": "ok", "market_data": "not_connected", "llm": "not_called"})
            return
        if path == "/":
            self._file(ROOT / "index.html")
            return
        if path.startswith("/static/"):
            relative = path[len("/static/") :]
            if not relative or ".." in relative.split("/"):
                self._json(404, {"error": "Not found."})
                return
            self._file(ROOT / relative)
            return
        self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/report":
            self._json(404, {"error": "Not found."})
            return
        length_header = self.headers.get("Content-Length", "0")
        try:
            length = int(length_header)
        except ValueError:
            self._json(400, {"error": "Content-Length must be a number."})
            return
        if length < 0 or length > MAX_BODY:
            self._json(413, {"error": "Request is too large."})
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "Send a JSON object."})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "Send a JSON object."})
            return
        try:
            report = build_report(payload)
        except ReportError as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception:
            self._json(500, {"error": "The note could not be built."})
            return
        self._json(200, report)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _file(self, path: Path) -> None:
        if not path.is_file():
            self._json(404, {"error": "Not found."})
            return
        body = path.read_bytes()
        content_type = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Fact Desk equity note.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), DeskHandler)
    print(f"Fact Desk at http://{args.host}:{args.port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
