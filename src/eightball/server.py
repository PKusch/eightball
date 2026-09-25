"""A small local web server: the ball as an API, and the page in web/index.html."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .answers import all_answers
from .backend import BackendError
from .engine import Ball

MAX_BODY = 8_000
MAX_QUESTION = 500
PAGE = Path(__file__).resolve().parents[2] / "web" / "index.html"


def make_handler(ball: Ball, cors: bool):
    lock = threading.Lock()  # one question at a time: the model is the bottleneck anyway

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet
            pass

        def _send(self, status: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if cors:
                self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj) -> None:
            self._send(status, json.dumps(obj).encode())

        def do_OPTIONS(self):
            self.send_response(204)
            if cors:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/healthz":
                self._json(200, {"ok": True, "backend": getattr(ball.backend, "name", "unknown")})
            elif path == "/v1/answers":
                self._json(200, all_answers())
            elif path in ("/", "/index.html"):
                if PAGE.exists():
                    self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
                else:
                    self._json(404, {"error": "web/index.html not found next to the package"})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path.split("?")[0] != "/v1/ask":
                return self._json(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", 0))
            except ValueError:
                return self._json(400, {"error": "bad Content-Length"})
            if n <= 0 or n > MAX_BODY:
                return self._json(413 if n > MAX_BODY else 400, {"error": "send a small JSON body"})
            try:
                body = json.loads(self.rfile.read(n))
                question = body["question"]
                if not isinstance(question, str):
                    raise TypeError
            except (ValueError, KeyError, TypeError):
                return self._json(400, {"error": 'body must be {"question": "..."}'})
            if not question.strip():
                return self._json(400, {"error": "ask a question"})
            if len(question) > MAX_QUESTION:
                return self._json(400, {"error": f"keep the question under {MAX_QUESTION} characters"})
            try:
                with lock:
                    self._json(200, ball.ask(question))
            except BackendError as e:
                self._json(502, {"error": str(e)})

    return Handler


def serve(ball: Ball, host: str = "127.0.0.1", port: int = 8787, cors: bool = False) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(ball, cors))
    print(f"eightball on http://{host}:{port}  (backend: {getattr(ball.backend, 'name', '?')})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
