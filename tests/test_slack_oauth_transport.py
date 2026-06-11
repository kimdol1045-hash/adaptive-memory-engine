import json
import stat
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.connectors.slack_oauth import (
    SLACK_AUTHORIZE_URL,
    SlackApiClient,
    SlackOAuthError,
    SlackOAuthClient,
    SlackOAuthConfig,
    SlackOAuthTransport,
    SlackToken,
    SlackTokenStore,
    exchange_and_save_slack_token,
)
from ame.connectors.sync_history import ConnectorSyncStore
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ensure_runtime_layout


class FakeSlackHttp:
    def __init__(self) -> None:
        self.get_calls: list[tuple[str, dict, dict]] = []
        self.post_calls: list[tuple[str, dict, dict]] = []

    def post_json(self, url: str, data: dict, headers: dict | None = None) -> dict:
        self.post_calls.append((url, dict(data), dict(headers or {})))
        return {
            "ok": True,
            "access_token": "xoxb-test",
            "scope": "channels:read,channels:history",
            "team": {"id": "T1", "name": "Hermes"},
            "bot_user_id": "B1",
            "authed_user": {"id": "U1"},
        }

    def get_json(self, url: str, params: dict, headers: dict | None = None) -> dict:
        self.get_calls.append((url, dict(params), dict(headers or {})))
        if url.endswith("/conversations.list"):
            return {"ok": True, "channels": [{"id": "C1", "name": "architecture"}]}
        if url.endswith("/conversations.history"):
            if params.get("oldest"):
                return {"ok": True, "messages": []}
            return {
                "ok": True,
                "messages": [
                    {
                        "ts": "1717890000.0001",
                        "user": "U1",
                        "text": "Hermes decided to use Slack OAuth Transport for live memory ingestion.",
                        "reply_count": 1,
                    }
                ],
            }
        if url.endswith("/conversations.replies"):
            return {
                "ok": True,
                "messages": [
                    {"ts": params["ts"], "user": "U1", "text": "parent"},
                    {
                        "ts": "1717890001.0002",
                        "user": "U2",
                        "text": "Rationale: OAuth Transport preserves the connector contract after export validation.",
                    },
                ],
            }
        raise AssertionError(f"unexpected Slack API url: {url}")


class FailingSlackHttp:
    def get_json(self, url: str, params: dict, headers: dict | None = None) -> dict:
        return {"ok": False, "error": "invalid_auth"}


def test_slack_oauth_authorization_url_and_token_store(tmp_path: Path) -> None:
    config = SlackOAuthConfig(
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="http://localhost/callback",
        scopes=["channels:read", "channels:history"],
    )

    auth_url = SlackOAuthClient(config).authorization_url("state-1")
    parsed = urlparse(auth_url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == SLACK_AUTHORIZE_URL
    assert query["client_id"] == ["client-1"]
    assert query["redirect_uri"] == ["http://localhost/callback"]
    assert query["scope"] == ["channels:read,channels:history"]
    assert query["state"] == ["state-1"]

    store_path = tmp_path / "tokens" / "slack.json"
    token = exchange_and_save_slack_token("code-1", config, store_path=store_path, http=FakeSlackHttp())

    assert token.team_id == "T1"
    assert token.access_token == "xoxb-test"
    assert SlackTokenStore(store_path).load("T1").team_name == "Hermes"
    assert stat.S_IMODE(store_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store_path.parent.stat().st_mode) == 0o700
    assert SlackTokenStore(store_path).revoke("T1") is True
    with pytest.raises(SlackOAuthError):
        SlackTokenStore(store_path).load("T1")


def test_slack_oauth_transport_exports_increments_and_ingests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("slack-oauth")
    fake_http = FakeSlackHttp()
    token = SlackToken(team_id="T1", team_name="Hermes", access_token="xoxb-test")
    transport = SlackOAuthTransport(SlackApiClient(token, http=fake_http))

    report = transport.sync("slack-oauth")

    assert report.channels == 1
    assert report.messages == 2
    assert report.ingested_documents == 2
    assert report.sync_run_id
    export_file = report.export_path / "architecture" / "oauth.json"
    rows = json.loads(export_file.read_text(encoding="utf-8"))
    assert rows[0]["source"] == "slack-oauth"
    assert rows[1]["thread_ts"] == "1717890000.0001"

    docs = list(BronzeStore(require_corpus("slack-oauth")).list())
    assert len(docs) == 2
    assert docs[0].source_type == "slack"
    assert any("Slack OAuth Transport for live memory ingestion" in doc.content for doc in docs)
    state_file = require_corpus("slack-oauth") / "connectors" / "slack_oauth_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["last_ts_by_channel"]["C1"] == "1717890001.0002"
    runs = ConnectorSyncStore(require_corpus("slack-oauth")).list(connector="slack-oauth")
    assert runs[0].id == report.sync_run_id
    assert runs[0].status == "success"
    assert runs[0].counts["messages"] == 2

    second_report = transport.sync("slack-oauth")

    assert second_report.messages == 0
    history_calls = [params for url, params, _headers in fake_http.get_calls if url.endswith("/conversations.history")]
    assert history_calls[-1]["oldest"] == "1717890001.0002"

    cli = CliRunner().invoke(app, ["sync-status", "slack-oauth", "--connector", "slack-oauth"])
    assert cli.exit_code == 0
    payload = json.loads(cli.output)
    assert payload[0]["connector"] == "slack-oauth"
    assert payload[0]["status"] == "success"


def test_slack_oauth_transport_records_failed_sync(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("slack-fail")
    token = SlackToken(team_id="T1", team_name="Hermes", access_token="xoxb-bad")
    transport = SlackOAuthTransport(SlackApiClient(token, http=FailingSlackHttp()))

    with pytest.raises(SlackOAuthError):
        transport.sync("slack-fail")

    runs = ConnectorSyncStore(require_corpus("slack-fail")).list(connector="slack-oauth")
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert "invalid_auth" in (runs[0].error or "")
