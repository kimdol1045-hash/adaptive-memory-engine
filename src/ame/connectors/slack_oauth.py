from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from ame.connectors.sync_history import ConnectorSyncStore
from ame.core.paths import ame_home, ensure_corpus_layout
from ame.pipeline import MemoryPipeline
from ame.security import token_vault


SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_ACCESS_URL = "https://slack.com/api/oauth.v2.access"
SLACK_API_URL = "https://slack.com/api"
DEFAULT_SLACK_SCOPES = [
    "channels:read",
    "channels:history",
    "groups:read",
    "groups:history",
]


class SlackOAuthError(RuntimeError):
    pass


class SlackOAuthConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/slack/oauth/callback"
    scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_SLACK_SCOPES))


class SlackToken(BaseModel):
    team_id: str
    access_token: str
    team_name: str | None = None
    bot_user_id: str | None = None
    authed_user_id: str | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SlackSyncState(BaseModel):
    team_id: str
    last_ts_by_channel: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime | None = None


class SlackHttpClient(Protocol):
    def post_json(self, url: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        ...

    def get_json(self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        ...


class UrlLibSlackHttpClient:
    def post_json(self, url: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=encoded, headers=headers or {}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_json(self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
        request_url = f"{url}?{query}" if query else url
        request = urllib.request.Request(request_url, headers=headers or {}, method="GET")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


class SlackTokenStore:
    def __init__(self, path: Path | None = None, backend: str = "file"):
        self.path = path or ame_home() / "tokens" / "slack.json"
        self.vault = token_vault("slack", self.path, backend=backend)  # type: ignore[arg-type]

    def save(self, token: SlackToken) -> SlackToken:
        data = self._read()
        data[token.team_id] = token.model_dump(mode="json")
        self.vault.save(data)
        return token

    def load(self, team_id: str) -> SlackToken:
        data = self._read()
        row = data.get(team_id)
        if not isinstance(row, dict):
            raise SlackOAuthError(f"Slack token not found for team_id={team_id}")
        return SlackToken.model_validate(row)

    def revoke(self, team_id: str) -> bool:
        data = self._read()
        existed = team_id in data
        data.pop(team_id, None)
        if data:
            self.vault.save(data)
        else:
            self.vault.delete()
        return existed

    def _read(self) -> dict[str, Any]:
        return self.vault.load()


class SlackSyncStateStore:
    def __init__(self, corpus_root: Path):
        self.path = corpus_root / "connectors" / "slack_oauth_state.json"

    def load(self, team_id: str) -> SlackSyncState:
        if not self.path.exists():
            return SlackSyncState(team_id=team_id)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        state = SlackSyncState.model_validate(data)
        if state.team_id != team_id:
            return SlackSyncState(team_id=team_id)
        return state

    def save(self, state: SlackSyncState) -> SlackSyncState:
        state.updated_at = datetime.now(timezone.utc)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state


class SlackOAuthClient:
    def __init__(self, config: SlackOAuthConfig, http: SlackHttpClient | None = None):
        self.config = config
        self.http = http or UrlLibSlackHttpClient()

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": ",".join(self.config.scopes),
            "state": state,
        }
        return f"{SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> SlackToken:
        payload = self.http.post_json(
            SLACK_OAUTH_ACCESS_URL,
            {
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
            },
        )
        if not payload.get("ok"):
            raise SlackOAuthError(f"Slack OAuth exchange failed: {payload.get('error', 'unknown_error')}")
        team = payload.get("team") or {}
        authed_user = payload.get("authed_user") or {}
        team_id = str(team.get("id") or payload.get("team_id") or "")
        access_token = str(payload.get("access_token") or "")
        if not team_id or not access_token:
            raise SlackOAuthError("Slack OAuth response did not include team_id or access_token")
        return SlackToken(
            team_id=team_id,
            team_name=team.get("name"),
            access_token=access_token,
            bot_user_id=payload.get("bot_user_id"),
            authed_user_id=authed_user.get("id"),
            scopes=_split_scopes(payload.get("scope")),
        )


class SlackApiClient:
    def __init__(self, token: SlackToken, http: SlackHttpClient | None = None):
        self.token = token
        self.http = http or UrlLibSlackHttpClient()

    def conversations_list(self, *, types: str = "public_channel,private_channel", limit: int = 200) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload = self._get("conversations.list", {"types": types, "limit": limit, "cursor": cursor})
            rows.extend(_dict_rows(payload.get("channels")))
            cursor = _next_cursor(payload)
            if not cursor:
                return rows

    def conversations_history(
        self,
        channel_id: str,
        *,
        oldest: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload = self._get(
                "conversations.history",
                {"channel": channel_id, "oldest": oldest, "inclusive": False, "limit": limit, "cursor": cursor},
            )
            rows.extend(_dict_rows(payload.get("messages")))
            cursor = _next_cursor(payload)
            if not cursor:
                return rows

    def conversations_replies(self, channel_id: str, ts: str, *, limit: int = 200) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload = self._get(
                "conversations.replies",
                {"channel": channel_id, "ts": ts, "limit": limit, "cursor": cursor},
            )
            rows.extend(_dict_rows(payload.get("messages")))
            cursor = _next_cursor(payload)
            if not cursor:
                return rows

    def _get(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = self.http.get_json(
            f"{SLACK_API_URL}/{method}",
            params,
            headers={"Authorization": f"Bearer {self.token.access_token}"},
        )
        if not payload.get("ok"):
            raise SlackOAuthError(f"Slack API {method} failed: {payload.get('error', 'unknown_error')}")
        return payload


class SlackOAuthSyncReport(BaseModel):
    corpus_id: str
    team_id: str
    export_path: Path
    channels: int
    messages: int
    ingested_documents: int = 0
    sync_run_id: str | None = None


class SlackOAuthTransport:
    def __init__(self, api: SlackApiClient):
        self.api = api

    def sync(
        self,
        corpus_id: str,
        *,
        channels: list[str] | None = None,
        ingest: bool = True,
    ) -> SlackOAuthSyncReport:
        started_at = datetime.now(timezone.utc)
        corpus_root = ensure_corpus_layout(corpus_id)
        sync_store = ConnectorSyncStore(corpus_root)
        state_store = SlackSyncStateStore(corpus_root)
        state = state_store.load(self.api.token.team_id)
        selected = set(channels or [])
        export_root = corpus_root / "imports" / "slack-oauth" / self.api.token.team_id
        export_root.mkdir(parents=True, exist_ok=True)

        channel_count = 0
        message_count = 0
        ingested = 0
        try:
            for channel in self.api.conversations_list():
                channel_id = str(channel.get("id") or "")
                channel_name = str(channel.get("name") or channel_id)
                if not channel_id:
                    continue
                if selected and channel_id not in selected and channel_name not in selected:
                    continue
                rows, latest_ts = self._sync_channel(channel_id, channel_name, state)
                if not rows:
                    continue
                channel_count += 1
                message_count += len(rows)
                target = export_root / _safe_path_part(channel_name) / "oauth.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
                if latest_ts:
                    state.last_ts_by_channel[channel_id] = latest_ts

            state_store.save(state)
            if ingest and message_count:
                report = MemoryPipeline().ingest(corpus_id, export_root, profile="slack-export")
                ingested = report.documents
            run = sync_store.record(
                connector="slack-oauth",
                status="success",
                started_at=started_at,
                source=self.api.token.team_id,
                counts={"channels": channel_count, "messages": message_count, "ingested_documents": ingested},
                metadata={"team_id": self.api.token.team_id, "channels_filter": ",".join(channels or [])},
            )
            return SlackOAuthSyncReport(
                corpus_id=corpus_id,
                team_id=self.api.token.team_id,
                export_path=export_root,
                channels=channel_count,
                messages=message_count,
                ingested_documents=ingested,
                sync_run_id=run.id,
            )
        except Exception as exc:
            sync_store.record(
                connector="slack-oauth",
                status="failed",
                started_at=started_at,
                source=self.api.token.team_id,
                counts={"channels": channel_count, "messages": message_count, "ingested_documents": ingested},
                metadata={"team_id": self.api.token.team_id, "channels_filter": ",".join(channels or [])},
                error=str(exc),
            )
            raise

    def _sync_channel(
        self,
        channel_id: str,
        channel_name: str,
        state: SlackSyncState,
    ) -> tuple[list[dict[str, Any]], str | None]:
        oldest = state.last_ts_by_channel.get(channel_id)
        rows: list[dict[str, Any]] = []
        latest_ts: str | None = oldest
        for message in self.api.conversations_history(channel_id, oldest=oldest):
            row = self._message_row(message, channel_id, channel_name)
            if row:
                rows.append(row)
                latest_ts = _max_ts(latest_ts, row["ts"])
            if message.get("reply_count") or message.get("thread_ts"):
                for reply in self.api.conversations_replies(channel_id, str(message.get("ts"))):
                    if str(reply.get("ts")) == str(message.get("ts")):
                        continue
                    reply_row = self._message_row(reply, channel_id, channel_name, parent_ts=str(message.get("ts")))
                    if reply_row:
                        rows.append(reply_row)
                        latest_ts = _max_ts(latest_ts, reply_row["ts"])
        rows.sort(key=lambda row: _ts_as_float(row["ts"]))
        return rows, latest_ts

    def _message_row(
        self,
        message: dict[str, Any],
        channel_id: str,
        channel_name: str,
        parent_ts: str | None = None,
    ) -> dict[str, Any] | None:
        text = str(message.get("text") or "").strip()
        ts = str(message.get("ts") or "")
        if not text or not ts:
            return None
        return {
            "ts": ts,
            "user": message.get("user") or message.get("username") or message.get("bot_id") or "unknown",
            "text": text,
            "thread_ts": parent_ts or message.get("thread_ts"),
            "channel_id": channel_id,
            "channel_name": channel_name,
            "source": "slack-oauth",
        }


def load_slack_token(team_id: str, store_path: Path | None = None) -> SlackToken:
    return SlackTokenStore(store_path).load(team_id)


def exchange_and_save_slack_token(
    code: str,
    config: SlackOAuthConfig,
    *,
    store_path: Path | None = None,
    token_backend: str = "file",
    http: SlackHttpClient | None = None,
) -> SlackToken:
    token = SlackOAuthClient(config, http=http).exchange_code(code)
    return SlackTokenStore(store_path, backend=token_backend).save(token)


def _split_scopes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _next_cursor(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("response_metadata")
    if not isinstance(metadata, dict):
        return None
    cursor = metadata.get("next_cursor")
    return str(cursor) if cursor else None


def _safe_path_part(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return clean or "channel"


def _ts_as_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0


def _max_ts(left: str | None, right: str) -> str:
    if left is None:
        return right
    return right if _ts_as_float(right) > _ts_as_float(left) else left
