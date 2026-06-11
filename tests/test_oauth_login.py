from pathlib import Path

import ame.connectors.oauth_callback as oauth_callback
from ame.connectors.oauth_callback import OAuthCallbackResult, run_local_oauth_login
from ame.connectors.oauth_provider import (
    ConnectedAppOAuthClient,
    ConnectedAppTokenStore,
    default_config,
    exchange_and_save_connected_app_token,
)
from ame.connectors.router import ConnectorRouter


class FakeConnectedAppHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, dict, bool]] = []

    def post_json(self, url: str, data: dict, headers: dict | None = None, *, json_body: bool = False) -> dict:
        self.calls.append((url, dict(data), dict(headers or {}), json_body))
        return {
            "access_token": "app-token",
            "refresh_token": "app-refresh",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read:user",
        }


def test_local_oauth_callback_receives_code_and_validates_state(monkeypatch) -> None:
    class FakeServer:
        def __init__(self, address, handler) -> None:
            self.address = address
            self.handler = handler
            self.expected_state = ""
            self.timeout = 0
            self.result = None
            self.error = None

        def handle_request(self) -> None:
            self.result = OAuthCallbackResult(code="code-1", state=self.expected_state)

        def server_close(self) -> None:
            pass

    monkeypatch.setattr(oauth_callback, "_OAuthCallbackServer", FakeServer)

    result = run_local_oauth_login(
        "https://example.com/auth",
        "http://localhost:8765/google/oauth/callback",
        "state-1",
        open_browser=False,
        timeout_seconds=5,
    )

    assert result.code == "code-1"
    assert result.state == "state-1"


def test_connected_app_oauth_provider_exchange_store_and_revoke(tmp_path: Path) -> None:
    config = default_config("github", client_id="client-1", client_secret="secret-1", redirect_uri="http://localhost/callback")
    client = ConnectedAppOAuthClient(config, http=FakeConnectedAppHttp())
    auth_url = client.authorization_url("state-1")
    store_path = tmp_path / "tokens" / "github.json"

    token = exchange_and_save_connected_app_token(
        "github",
        "code-1",
        config,
        account_id="andan",
        store_path=store_path,
        http=FakeConnectedAppHttp(),
    )
    loaded = ConnectedAppTokenStore("github", store_path).load("andan")

    assert "github.com/login/oauth/authorize" in auth_url
    assert token.access_token == "app-token"
    assert loaded.refresh_token == "app-refresh"
    assert ConnectedAppTokenStore("github", store_path).revoke("andan") is True


def test_notion_provider_uses_basic_auth_and_json_token_request() -> None:
    fake = FakeConnectedAppHttp()
    config = default_config("notion", client_id="client-1", client_secret="secret-1", redirect_uri="http://localhost/callback")

    ConnectedAppOAuthClient(config, http=fake).exchange_code("code-1")

    url, _data, headers, json_body = fake.calls[0]
    assert url == "https://api.notion.com/v1/oauth/token"
    assert headers["Authorization"].startswith("Basic ")
    assert json_body is True


def test_connector_profiles_include_common_oauth_bootstrap_apps() -> None:
    names = {profile.name for profile in ConnectorRouter().profiles()}

    assert {"google-oauth", "slack-oauth", "github-oauth", "notion-oauth", "jira-oauth"} <= names
