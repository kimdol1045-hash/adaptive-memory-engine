from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from ame.core.paths import ame_home
from ame.security import token_vault


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuthConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/google/oauth/callback"
    scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_GOOGLE_SCOPES))
    access_type: str = "offline"
    prompt: str = "consent"


class GoogleToken(BaseModel):
    account_id: str
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoogleHttpClient(Protocol):
    def post_json(self, url: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        ...


class UrlLibGoogleHttpClient:
    def post_json(self, url: str, data: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=encoded, headers=headers or {}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


class GoogleTokenStore:
    def __init__(self, path: Path | None = None, backend: str = "file"):
        self.path = path or ame_home() / "tokens" / "google.json"
        self.vault = token_vault("google", self.path, backend=backend)  # type: ignore[arg-type]

    def save(self, token: GoogleToken) -> GoogleToken:
        data = self._read()
        data[token.account_id] = token.model_dump(mode="json")
        self.vault.save(data)
        return token

    def load(self, account_id: str) -> GoogleToken:
        data = self._read()
        row = data.get(account_id)
        if not isinstance(row, dict):
            raise GoogleOAuthError(f"Google token not found for account_id={account_id}")
        return GoogleToken.model_validate(row)

    def revoke(self, account_id: str) -> bool:
        data = self._read()
        existed = account_id in data
        data.pop(account_id, None)
        if data:
            self.vault.save(data)
        else:
            self.vault.delete()
        return existed

    def _read(self) -> dict[str, Any]:
        return self.vault.load()


class GoogleOAuthClient:
    def __init__(self, config: GoogleOAuthConfig, http: GoogleHttpClient | None = None):
        self.config = config
        self.http = http or UrlLibGoogleHttpClient()

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "access_type": self.config.access_type,
            "prompt": self.config.prompt,
            "include_granted_scopes": "true",
        }
        return f"{GOOGLE_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, account_id: str = "default") -> GoogleToken:
        payload = self.http.post_json(
            GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if error := payload.get("error"):
            raise GoogleOAuthError(f"Google OAuth exchange failed: {error}")
        access_token = str(payload.get("access_token") or "")
        if not access_token:
            raise GoogleOAuthError("Google OAuth response did not include access_token")
        return GoogleToken(
            account_id=account_id,
            access_token=access_token,
            refresh_token=payload.get("refresh_token"),
            token_type=str(payload.get("token_type") or "Bearer"),
            expires_in=payload.get("expires_in"),
            scopes=_split_scopes(payload.get("scope")) or list(self.config.scopes),
        )


def exchange_and_save_google_token(
    code: str,
    config: GoogleOAuthConfig,
    *,
    account_id: str = "default",
    store_path: Path | None = None,
    token_backend: str = "file",
    http: GoogleHttpClient | None = None,
) -> GoogleToken:
    token = GoogleOAuthClient(config, http=http).exchange_code(code, account_id=account_id)
    return GoogleTokenStore(store_path, backend=token_backend).save(token)


def _split_scopes(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [item for item in str(value).replace(",", " ").split() if item]
