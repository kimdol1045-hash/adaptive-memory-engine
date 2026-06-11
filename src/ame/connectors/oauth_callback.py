from __future__ import annotations

import secrets
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer


class OAuthCallbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthCallbackResult:
    code: str
    state: str


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def run_local_oauth_login(
    authorization_url: str,
    redirect_uri: str,
    expected_state: str,
    *,
    open_browser: bool = True,
    timeout_seconds: int = 180,
) -> OAuthCallbackResult:
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise OAuthCallbackError("Local OAuth login requires an http://localhost redirect URI")
    if not parsed.port:
        raise OAuthCallbackError("Local OAuth login redirect URI must include a port")

    server = _OAuthCallbackServer((parsed.hostname, parsed.port), _OAuthCallbackHandler)
    server.expected_state = expected_state
    server.timeout = timeout_seconds
    try:
        if open_browser:
            webbrowser.open(authorization_url)
        server.handle_request()
    finally:
        server.server_close()

    if server.error:
        raise OAuthCallbackError(server.error)
    if server.result is None:
        raise OAuthCallbackError("OAuth login timed out before receiving a callback")
    return server.result


class _OAuthCallbackServer(HTTPServer):
    expected_state: str
    result: OAuthCallbackResult | None = None
    error: str | None = None


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        state = _single(query, "state")
        code = _single(query, "code")
        error = _single(query, "error")

        if error:
            self.server.error = f"OAuth provider returned error: {error}"  # type: ignore[attr-defined]
            self._respond(400, "OAuth login failed. You can close this window.")
            return
        if state != self.server.expected_state:  # type: ignore[attr-defined]
            self.server.error = "OAuth callback state did not match"  # type: ignore[attr-defined]
            self._respond(400, "OAuth login state mismatch. You can close this window.")
            return
        if not code:
            self.server.error = "OAuth callback did not include code"  # type: ignore[attr-defined]
            self._respond(400, "OAuth login did not include a code. You can close this window.")
            return

        self.server.result = OAuthCallbackResult(code=code, state=state)  # type: ignore[attr-defined]
        self._respond(200, "OAuth login complete. You can close this window.")

    def log_message(self, format: str, *args) -> None:
        return

    def _respond(self, status: int, message: str) -> None:
        payload = (
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>Adaptive Memory Engine</title></head>"
            f"<body><h1>{message}</h1></body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _single(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0] if values else ""
