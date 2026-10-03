from __future__ import annotations

import secrets
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class LoopbackCallbackResult:
    code: str | None
    state: str | None
    error: str | None
    error_description: str | None


def allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_accepting(host: str, port: int, timeout_seconds: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.05):
                return
        except OSError:
            time.sleep(0.01)
    raise TimeoutError(f"Loopback server did not accept connections on {host}:{port}")


def constant_time_equal(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@dataclass
class LoopbackOAuthServer:
    host: str
    port: int
    redirect_uri: str
    expected_state: str
    _server: HTTPServer
    _thread: threading.Thread
    _done: threading.Event
    _result: LoopbackCallbackResult | None = None

    @classmethod
    def start(cls, *, expected_state: str, callback_path: str = "/oauth/callback") -> LoopbackOAuthServer:
        port = allocate_loopback_port()
        host = "127.0.0.1"
        redirect_uri = f"http://{host}:{port}{callback_path}"
        done_event = threading.Event()
        holder = cls(
            host=host,
            port=port,
            redirect_uri=redirect_uri,
            expected_state=expected_state,
            _server=None,  # type: ignore[arg-type]
            _thread=None,  # type: ignore[arg-type]
            _done=done_event,
        )

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                state = (params.get("state") or [None])[0]
                code = (params.get("code") or [None])[0]
                error = (params.get("error") or [None])[0]
                error_description = (params.get("error_description") or [None])[0]

                if state is None or not constant_time_equal(state, expected_state):
                    holder._finish(
                        LoopbackCallbackResult(
                            code=None,
                            state=state,
                            error="invalid_state",
                            error_description="state mismatch",
                        ),
                    )
                    self._write_response(400, "Authorization failed.", "Return to terminal for details.")
                    return

                if error:
                    holder._finish(
                        LoopbackCallbackResult(
                            code=None,
                            state=state,
                            error=error,
                            error_description=error_description,
                        ),
                    )
                    self._write_response(400, "Authorization failed.", "Return to terminal for details.")
                    return

                if not code:
                    holder._finish(
                        LoopbackCallbackResult(
                            code=None,
                            state=state,
                            error="missing_code",
                            error_description=None,
                        ),
                    )
                    self._write_response(400, "Authorization failed.", "Return to terminal for details.")
                    return

                holder._finish(
                    LoopbackCallbackResult(code=code, state=state, error=None, error_description=None),
                )
                self._write_response(
                    200,
                    "Authorization received.",
                    "You can close this tab and return to the terminal.",
                )

            def _write_response(self, status: int, title: str, body: str) -> None:
                html = f"<html><body><h1>{title}</h1><p>{body}</p></body></html>"
                payload = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        def _finish(result: LoopbackCallbackResult) -> None:
            holder._result = result
            holder._done.set()

        holder._finish = _finish

        server = HTTPServer((host, port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _wait_until_accepting(host, port)
        holder._server = server
        holder._thread = thread
        return holder

    def wait_for_result(self, timeout_seconds: float = 300.0) -> LoopbackCallbackResult:
        if not self._done.wait(timeout=timeout_seconds):
            raise TimeoutError("Timed out waiting for OAuth loopback callback")
        if self._result is None:
            raise RuntimeError("OAuth callback completed without result")
        return self._result

    def shutdown(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5.0)
        self._server.server_close()
