from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from ame.core.paths import ame_home
from ame.security import token_vault


TokenRequestStyle = Literal["form", "json"]
ClientAuthStyle = Literal["body", "basic"]


class ConnectedAppOAuthError(RuntimeError):
    pass


class OAuthProviderSpec(BaseModel):
    name: str
    authorize_url: str
    token_url: str
    default_redirect_uri: str
    default_scopes: list[str] = Field(default_factory=list)
    scope_separator: str = " "
    auth_extra: dict[str, str] = Field(default_factory=dict)
    token_request_style: TokenRequestStyle = "form"
    client_auth_style: ClientAuthStyle = "body"


class ConnectedAppOAuthConfig(BaseModel):
    provider: str
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str
    scopes: list[str] = Field(default_factory=list)


class ConnectedAppToken(BaseModel):
    provider: str
    account_id: str
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    scopes: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectedAppHttpClient(Protocol):
    def post_json(
        self,
        url: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
        *,
        json_body: bool = False,
    ) -> dict[str, Any]:
        ...


class UrlLibConnectedAppHttpClient:
    def post_json(
        self,
        url: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
        *,
        json_body: bool = False,
    ) -> dict[str, Any]:
        request_headers = dict(headers or {})
        if json_body:
            body = json.dumps(data).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        else:
            body = urllib.parse.urlencode(data).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        request_headers.setdefault("Accept", "application/json")
        request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


PROVIDER_SPECS: dict[str, OAuthProviderSpec] = {
    "github": OAuthProviderSpec(
        name="github",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        default_redirect_uri="http://localhost:8765/github/oauth/callback",
        default_scopes=["read:user"],
    ),
    "notion": OAuthProviderSpec(
        name="notion",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        default_redirect_uri="http://localhost:8765/notion/oauth/callback",
        default_scopes=[],
        auth_extra={"owner": "user"},
        token_request_style="json",
        client_auth_style="basic",
    ),
    "jira": OAuthProviderSpec(
        name="jira",
        authorize_url="https://auth.atlassian.com/authorize",
        token_url="https://auth.atlassian.com/oauth/token",
        default_redirect_uri="http://localhost:8765/jira/oauth/callback",
        default_scopes=["read:jira-work", "read:jira-user", "offline_access"],
        auth_extra={"audience": "api.atlassian.com", "prompt": "consent"},
        token_request_style="json",
    ),
}


def provider_spec(provider: str) -> OAuthProviderSpec:
    normalized = provider.casefold().replace("_", "-")
    aliases = {"atlassian": "jira", "github-oauth": "github", "notion-oauth": "notion", "jira-oauth": "jira"}
    normalized = aliases.get(normalized, normalized)
    spec = PROVIDER_SPECS.get(normalized)
    if not spec:
        raise ConnectedAppOAuthError(f"Unsupported connected app provider: {provider}")
    return spec


class ConnectedAppOAuthClient:
    def __init__(self, config: ConnectedAppOAuthConfig, spec: OAuthProviderSpec | None = None, http: ConnectedAppHttpClient | None = None):
        self.config = config
        self.spec = spec or provider_spec(config.provider)
        self.http = http or UrlLibConnectedAppHttpClient()

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "state": state,
            **self.spec.auth_extra,
        }
        if self.config.scopes:
            params["scope"] = self.spec.scope_separator.join(self.config.scopes)
        return f"{self.spec.authorize_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str, account_id: str = "default") -> ConnectedAppToken:
        headers: dict[str, str] = {}
        payload = {
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }
        if self.spec.client_auth_style == "basic":
            auth = f"{self.config.client_id}:{self.config.client_secret}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(auth).decode('ascii')}"
        else:
            payload["client_id"] = self.config.client_id
            payload["client_secret"] = self.config.client_secret

        response = self.http.post_json(
            self.spec.token_url,
            payload,
            headers=headers,
            json_body=self.spec.token_request_style == "json",
        )
        if error := response.get("error"):
            raise ConnectedAppOAuthError(f"{self.spec.name} OAuth exchange failed: {error}")
        access_token = str(response.get("access_token") or "")
        if not access_token:
            raise ConnectedAppOAuthError(f"{self.spec.name} OAuth response did not include access_token")
        return ConnectedAppToken(
            provider=self.spec.name,
            account_id=account_id,
            access_token=access_token,
            refresh_token=response.get("refresh_token"),
            token_type=str(response.get("token_type") or "Bearer"),
            expires_in=response.get("expires_in"),
            scopes=_split_scopes(response.get("scope")) or list(self.config.scopes),
            raw={key: value for key, value in response.items() if key not in {"access_token", "refresh_token"}},
        )


class ConnectedAppTokenStore:
    def __init__(self, provider: str, path: Path | None = None, backend: str = "file"):
        self.provider = provider_spec(provider).name
        self.path = path or ame_home() / "tokens" / f"{self.provider}.json"
        self.vault = token_vault(self.provider, self.path, backend=backend)  # type: ignore[arg-type]

    def save(self, token: ConnectedAppToken) -> ConnectedAppToken:
        data = self._read()
        data[token.account_id] = token.model_dump(mode="json")
        self.vault.save(data)
        return token

    def load(self, account_id: str = "default") -> ConnectedAppToken:
        data = self._read()
        row = data.get(account_id)
        if not isinstance(row, dict):
            raise ConnectedAppOAuthError(f"{self.provider} token not found for account_id={account_id}")
        return ConnectedAppToken.model_validate(row)

    def revoke(self, account_id: str = "default") -> bool:
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


def exchange_and_save_connected_app_token(
    provider: str,
    code: str,
    config: ConnectedAppOAuthConfig,
    *,
    account_id: str = "default",
    store_path: Path | None = None,
    token_backend: str = "file",
    http: ConnectedAppHttpClient | None = None,
) -> ConnectedAppToken:
    spec = provider_spec(provider)
    token = ConnectedAppOAuthClient(config, spec=spec, http=http).exchange_code(code, account_id=account_id)
    return ConnectedAppTokenStore(spec.name, store_path, backend=token_backend).save(token)


def default_config(provider: str, *, client_id: str = "", client_secret: str = "", redirect_uri: str | None = None, scopes: list[str] | None = None) -> ConnectedAppOAuthConfig:
    spec = provider_spec(provider)
    return ConnectedAppOAuthConfig(
        provider=spec.name,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri or spec.default_redirect_uri,
        scopes=list(spec.default_scopes if scopes is None else scopes),
    )


def _split_scopes(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [item for item in str(value).replace(",", " ").split() if item]
