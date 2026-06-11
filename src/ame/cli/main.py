from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal

import typer

from ame.agent.mcp import BootstrapMcpToolbox, LocalMcpToolbox, McpStdioServer
from ame.agent.memory_api import AgentMemoryAPI
from ame.connectors.router import ConnectorRouter
from ame.connectors.google_oauth import (
    GoogleOAuthClient,
    GoogleOAuthConfig,
    GoogleOAuthError,
    GoogleTokenStore,
    exchange_and_save_google_token,
)
from ame.connectors.oauth_callback import OAuthCallbackError, new_oauth_state, run_local_oauth_login
from ame.connectors.oauth_provider import (
    ConnectedAppOAuthClient,
    ConnectedAppOAuthError,
    ConnectedAppTokenStore,
    default_config,
    exchange_and_save_connected_app_token,
    provider_spec,
)
from ame.connectors.slack_oauth import (
    SlackApiClient,
    SlackOAuthClient,
    SlackOAuthConfig,
    SlackOAuthError,
    SlackOAuthTransport,
    SlackTokenStore,
    exchange_and_save_slack_token,
)
from ame.connectors.sync_history import ConnectorSyncStore
from ame.core.config import load_config
from ame.core.errors import LightRagBackendError, LlmClientError
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ame_home, ensure_runtime_layout
from ame.core.state import CorpusStateStore
from ame.export.obsidian import ObsidianExporter
from ame.gold.store import GoldStore
from ame.hardware.profiler import HardwareProfiler
from ame.models.download import ModelDownloadError, OllamaModelInstaller
from ame.models.registry import ModelRegistry, load_default_registry
from ame.models.router import ModelRouter
from ame.pipeline import MemoryPipeline
from ame.security import redact_secrets
from ame.storage.lightrag_adapter import LightRagAdapter

app = typer.Typer(no_args_is_help=True)
export_app = typer.Typer(no_args_is_help=True)
lightrag_app = typer.Typer(no_args_is_help=True)
mcp_app = typer.Typer(no_args_is_help=True)
slack_app = typer.Typer(no_args_is_help=True)
google_app = typer.Typer(no_args_is_help=True)
models_app = typer.Typer(no_args_is_help=True)
connectors_app = typer.Typer(no_args_is_help=True)
app.add_typer(export_app, name="export")
app.add_typer(lightrag_app, name="lightrag")
app.add_typer(mcp_app, name="mcp")
app.add_typer(slack_app, name="slack")
app.add_typer(google_app, name="google")
app.add_typer(models_app, name="models")
app.add_typer(connectors_app, name="connectors")


@app.command()
def init() -> None:
    home = ensure_runtime_layout()
    typer.echo(f"AME_HOME initialized: {home}")


@app.command()
def doctor() -> None:
    home = ensure_runtime_layout()
    config = load_config()
    profile = HardwareProfiler().profile(home)
    registry = _load_registry()
    plan = ModelRouter(registry).plan(profile)
    install_plan = OllamaModelInstaller(host=config.lightrag.ollama_host, allow_cli_list=True).install_plan(plan, profile)
    connector_profiles = ConnectorRouter().profiles()
    typer.echo(f"AME_HOME: {home}")
    typer.echo("Runtime: local filesystem")
    typer.echo("Connectors: " + ", ".join(connector.name for connector in connector_profiles))
    typer.echo(f"Hardware: {profile.os} {profile.machine}, RAM {profile.total_ram_gb}GB, disk free {profile.disk_free_gb}GB")
    if profile.disk_free_gb < 30:
        typer.echo("Warning: disk free is below the 30GB local MVP recommendation.")
    typer.echo(f"Tier: {profile.tier.value}")
    typer.echo(f"Model mode: {plan.mode}")
    typer.echo(f"Extract model: {plan.models.extract.model}")
    typer.echo(f"Verify model: {plan.models.verify.model}")
    typer.echo(f"Synthesize model: {plan.models.synthesize.model}")
    typer.echo(f"Embedding model: {plan.models.embed.model}")
    typer.echo(f"Token backend: {config.security.token_backend}")
    typer.echo(f"PII redaction: {config.security.pii_redaction}")
    typer.echo(f"Ollama installed: {profile.ollama_installed}")
    typer.echo(f"Ollama model status source: {install_plan.installed_models_source or 'unavailable'}")
    typer.echo(f"Installed local LLM models: {', '.join(install_plan.installed_models) or 'n/a'}")
    typer.echo(f"Missing recommended local LLM models: {', '.join(install_plan.missing_models) or 'none'}")
    typer.echo(
        "Default AME usage is local-LLM Bronze/Silver/Gold build. "
        "Use deterministic mode only as a lightweight fallback."
    )
    if install_plan.error:
        typer.echo(f"Model status error: {install_plan.error}")


@app.command()
def setup(
    execute: bool = typer.Option(False, "--execute", help="Pull recommended local models with Ollama."),
) -> None:
    home = ensure_runtime_layout()
    config = load_config()
    profile = HardwareProfiler().profile(home)
    registry = _load_registry()
    plan = ModelRouter(registry).plan(profile)
    installer = OllamaModelInstaller(host=config.lightrag.ollama_host, allow_cli_list=True)
    install_plan = installer.install_plan(plan, profile)

    typer.echo(f"AME_HOME: {home}")
    typer.echo(f"Hardware tier: {plan.tier}")
    typer.echo(f"Extract model: {plan.models.extract.model}")
    typer.echo(f"Verify model: {plan.models.verify.model}")
    typer.echo(f"Synthesize model: {plan.models.synthesize.model}")
    typer.echo(f"Embedding model: {plan.models.embed.model}")

    if not profile.ollama_installed:
        typer.echo("Ollama is not installed. Install Ollama first, then run `memory setup --execute`.")
        raise typer.Exit(1)

    if not install_plan.missing_models:
        typer.echo("Recommended local models are already installed.")
        return

    if not execute:
        typer.echo("Recommended model pull commands:")
        for command in install_plan.pull_commands:
            typer.echo(" ".join(command))
        typer.echo("Run `memory setup --execute` to pull them.")
        return

    results = installer.pull(install_plan.missing_models, execute=True, installed=install_plan.installed_models)
    typer.echo(json.dumps([result.model_dump(mode="json") for result in results], ensure_ascii=False, indent=2))


@app.command()
def create(corpus_id: str) -> None:
    ensure_runtime_layout()
    root = create_corpus(corpus_id)
    typer.echo(f"Corpus ready: {root}")


@app.command()
def ingest(
    corpus_id: str,
    source_path: Path,
    mode: Literal["deterministic", "llm"] = "deterministic",
    profile: str | None = None,
) -> None:
    try:
        report = MemoryPipeline().ingest(corpus_id, source_path, mode=mode, profile=profile)
    except LlmClientError as exc:
        typer.echo(f"LLM extraction failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    except LightRagBackendError as exc:
        typer.echo(f"LightRAG adapter failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Ingested {report.documents} document(s) in {report.mode} mode, "
        f"{report.gold_nodes} node(s), {report.gold_edges} edge(s), "
        f"{report.rejected} rejected item(s)."
    )
    typer.echo(f"LightRAG custom KG staged: {report.custom_kg_path}")


@app.command()
def load(
    corpus_id: str,
    source_path: Path,
    mode: Literal["deterministic", "llm"] = "llm",
    profile: str | None = None,
) -> None:
    ensure_runtime_layout()
    create_corpus(corpus_id)
    try:
        report = MemoryPipeline().ingest(corpus_id, source_path, mode=mode, profile=profile)
    except LlmClientError as exc:
        typer.echo(f"LLM extraction failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    except LightRagBackendError as exc:
        typer.echo(f"LightRAG adapter failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Loaded {report.documents} document(s) into {corpus_id}, "
        f"{report.gold_nodes} node(s), {report.gold_edges} edge(s), "
        f"{report.rejected} rejected item(s)."
    )
    typer.echo(f"LightRAG custom KG staged: {report.custom_kg_path}")


@app.command()
def connect(
    corpus_id: str | None = typer.Argument(None),
    client: Literal["generic", "codex", "claude"] = "generic",
    ame_home_path: Path | None = typer.Option(None, "--ame-home", help="AME_HOME to put in the MCP client env."),
) -> None:
    home = (ame_home_path or ame_home()).expanduser().resolve()
    args = ["mcp", "stdio"] if corpus_id is None else ["mcp", "stdio", corpus_id]
    if corpus_id is not None:
        require_corpus(corpus_id)
    server = {
        "command": "memory",
        "args": args,
        "env": {"AME_HOME": str(home)},
    }
    name = "adaptive-memory-engine"
    if client == "generic":
        payload = server
    else:
        payload = {"mcpServers": {name: server}}
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def query(corpus_id: str, question: str, mode: str = "hybrid") -> None:
    root = require_corpus(corpus_id)
    try:
        result = asyncio.run(LightRagAdapter(root).query(question, mode=mode))
    except LightRagBackendError as exc:
        typer.echo(f"LightRAG adapter failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(result.answer)
    if result.sources:
        typer.echo("")
        typer.echo("Sources:")
        for source in result.sources:
            typer.echo(f"- {source.document} ({source.source_id})")


@app.command()
def chat(
    corpus_id: str,
    mode: str = typer.Option("hybrid", "--mode", help="LightRAG query mode."),
    sources: bool = typer.Option(True, "--sources/--no-sources", help="Show sources after each answer."),
) -> None:
    root = require_corpus(corpus_id)
    typer.echo(f"AME chat: {corpus_id}")
    typer.echo("Type /exit to quit, /help for commands.")
    while True:
        try:
            question = input("ame> ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            typer.echo("bye")
            return
        if not question:
            continue
        if question in {"/exit", "/quit", "exit", "quit", "q"}:
            typer.echo("bye")
            return
        if question == "/help":
            typer.echo("/exit  quit chat")
            typer.echo("/help  show commands")
            continue
        try:
            result = asyncio.run(LightRagAdapter(root).query(question, mode=mode))
        except LightRagBackendError as exc:
            typer.echo(f"LightRAG adapter failed: {exc}", err=True)
            continue
        typer.echo(result.answer)
        if sources and result.sources:
            typer.echo("")
            typer.echo("Sources:")
            for source in result.sources:
                typer.echo(f"- {source.document} ({source.source_id})")
        typer.echo("")


@app.command()
def retrieve(corpus_id: str, query: str, k: int = 8) -> None:
    root = require_corpus(corpus_id)
    result = AgentMemoryAPI(root).retrieve(query, k=k)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@app.command()
def graph(corpus_id: str, entity: str) -> None:
    root = require_corpus(corpus_id)
    result = AgentMemoryAPI(root).graph(entity)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@app.command()
def decisions(
    corpus_id: str,
    project: str | None = None,
    all: bool = typer.Option(False, "--all"),
    date_from: str | None = typer.Option(None, "--from"),
    date_to: str | None = typer.Option(None, "--to"),
) -> None:
    root = require_corpus(corpus_id)
    result = AgentMemoryAPI(root).decisions(project=project, current_only=not all, date_from=date_from, date_to=date_to)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@app.command("write-decision")
def write_decision(
    corpus_id: str,
    title: str,
    rationale: str,
    project: str | None = None,
    source: str = "writeback",
    participants: list[str] = typer.Option([], "--participant"),
) -> None:
    root = require_corpus(corpus_id)
    result = AgentMemoryAPI(root).write_decision(
        title=title,
        rationale=rationale,
        project=project,
        participants=participants,
        source=source,
    )
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@app.command("write-note")
def write_note(corpus_id: str, title: str, content: str) -> None:
    root = require_corpus(corpus_id)
    result = AgentMemoryAPI(root).write_note(title=title, content=content)
    typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@app.command("sync-status")
def sync_status(
    corpus_id: str,
    connector: str | None = typer.Option(None, "--connector"),
    limit: int = typer.Option(10, "--limit", min=1),
) -> None:
    root = require_corpus(corpus_id)
    runs = ConnectorSyncStore(root).list(connector=connector, limit=limit)
    typer.echo(json.dumps([run.model_dump(mode="json") for run in runs], ensure_ascii=False, indent=2))


@models_app.command("status")
def models_status() -> None:
    profile = HardwareProfiler().profile(_profile_disk_path())
    registry = _load_registry()
    plan = ModelRouter(registry).plan(profile)
    install_plan = OllamaModelInstaller(host=load_config().lightrag.ollama_host, allow_cli_list=True).install_plan(plan, profile)
    typer.echo(
        json.dumps(
            {
                "hardware": profile.model_dump(mode="json"),
                "plan": plan.model_dump(mode="json"),
                "install": install_plan.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@models_app.command("pull")
def models_pull(
    model: list[str] = typer.Option([], "--model", help="Model name to pull. Repeat for multiple models."),
    all_models: bool = typer.Option(False, "--all", help="Plan every required Ollama model for this hardware tier."),
    execute: bool = typer.Option(False, "--execute", help="Run ollama pull. Without this, only prints planned commands."),
) -> None:
    profile = HardwareProfiler().profile(_profile_disk_path())
    registry = _load_registry()
    plan = ModelRouter(registry).plan(profile)
    installer = OllamaModelInstaller(host=load_config().lightrag.ollama_host, allow_cli_list=True)
    install_plan = installer.install_plan(plan, profile)
    targets = model or (install_plan.required_models if all_models else install_plan.missing_models)
    try:
        results = installer.pull(targets, execute=execute, installed=install_plan.installed_models)
    except ModelDownloadError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps([result.model_dump(mode="json") for result in results], ensure_ascii=False, indent=2))


@connectors_app.command("profiles")
def connector_profiles() -> None:
    profiles = ConnectorRouter().profiles()
    typer.echo(json.dumps([profile.model_dump(mode="json") for profile in profiles], ensure_ascii=False, indent=2))


@connectors_app.command("diff")
def connector_diff(
    corpus_id: str,
    source_path: Path,
    profile: str = typer.Option("obsidian", "--profile"),
) -> None:
    root = require_corpus(corpus_id)
    runtime = ConnectorRouter().runtime(source_path, profile)
    diff = runtime.diff(root.name, source_path)
    payload = diff.model_dump(mode="json")
    payload["counts"] = diff.counts
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@connectors_app.command("sync")
def connector_sync(
    corpus_id: str,
    source_path: Path,
    profile: str = typer.Option("obsidian", "--profile"),
) -> None:
    ensure_runtime_layout()
    create_corpus(corpus_id)
    runtime = ConnectorRouter().runtime(source_path, profile)
    report = runtime.sync(corpus_id, source_path)
    typer.echo(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))


@connectors_app.command("login")
def connector_login(
    provider: str,
    account_id: str = typer.Option("default", "--account-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated OAuth scopes."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-browser"),
    timeout: int = typer.Option(180, "--timeout", min=10),
) -> None:
    try:
        token = _connector_login(
            provider,
            account_id=account_id,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            open_browser=open_browser,
            timeout=timeout,
        )
    except (OAuthCallbackError, SlackOAuthError, GoogleOAuthError, ConnectedAppOAuthError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(redact_secrets(token), ensure_ascii=False, indent=2))


@connectors_app.command("revoke-token")
def connector_revoke_token(
    provider: str,
    account_id: str = typer.Option("default", "--account-id"),
) -> None:
    try:
        normalized = provider.casefold().replace("_", "-")
        if normalized == "google":
            revoked = GoogleTokenStore(backend=_token_backend()).revoke(account_id)
        elif normalized == "slack":
            revoked = SlackTokenStore(backend=_token_backend()).revoke(account_id)
        else:
            revoked = ConnectedAppTokenStore(provider, backend=_token_backend()).revoke(account_id)
    except (SlackOAuthError, GoogleOAuthError, ConnectedAppOAuthError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps({"provider": provider, "account_id": account_id, "revoked": revoked}, ensure_ascii=False, indent=2))


@connectors_app.command("token-status")
def connector_token_status(
    provider: str,
    account_id: str = typer.Option("default", "--account-id"),
) -> None:
    try:
        normalized = provider.casefold().replace("_", "-")
        if normalized == "google":
            token = GoogleTokenStore(backend=_token_backend()).load(account_id)
        elif normalized == "slack":
            token = SlackTokenStore(backend=_token_backend()).load(account_id)
        else:
            token = ConnectedAppTokenStore(provider, backend=_token_backend()).load(account_id)
    except (SlackOAuthError, GoogleOAuthError, ConnectedAppOAuthError):
        typer.echo(json.dumps({"provider": provider, "account_id": account_id, "connected": False}, ensure_ascii=False, indent=2))
        return
    typer.echo(
        json.dumps(
            redact_secrets({"provider": provider, "account_id": account_id, "connected": True, "token": token.model_dump(mode="json")}),
            ensure_ascii=False,
            indent=2,
        )
    )


@slack_app.command("auth-url")
def slack_auth_url(
    state: str = "ame",
    client_id: str | None = typer.Option(None, "--client-id"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Slack OAuth scopes."),
) -> None:
    ensure_runtime_layout()
    config = _slack_config(client_id=client_id, redirect_uri=redirect_uri, scopes=scopes)
    _require_option(config.client_id, "--client-id or [slack].client_id")
    typer.echo(SlackOAuthClient(config).authorization_url(state))


@slack_app.command("exchange-code")
def slack_exchange_code(
    code: str,
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Slack OAuth scopes."),
) -> None:
    ensure_runtime_layout()
    config = _slack_config(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scopes=scopes)
    _require_option(config.client_id, "--client-id or [slack].client_id")
    _require_option(config.client_secret, "--client-secret or [slack].client_secret")
    try:
        token = exchange_and_save_slack_token(code, config, token_backend=_token_backend())
    except SlackOAuthError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(redact_secrets(token.model_dump(mode="json")), ensure_ascii=False, indent=2))


@slack_app.command("login")
def slack_login(
    team_id: str = typer.Option("default", "--team-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Slack OAuth scopes."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-browser"),
    timeout: int = typer.Option(180, "--timeout", min=10),
) -> None:
    try:
        token = _connector_login(
            "slack",
            account_id=team_id,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            open_browser=open_browser,
            timeout=timeout,
        )
    except (OAuthCallbackError, SlackOAuthError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(redact_secrets(token), ensure_ascii=False, indent=2))


@slack_app.command("sync")
def slack_sync(
    corpus_id: str,
    team_id: str,
    channels: list[str] = typer.Option([], "--channel", help="Channel id or name. Repeat for multiple channels."),
    no_ingest: bool = typer.Option(False, "--no-ingest"),
) -> None:
    ensure_runtime_layout()
    create_corpus(corpus_id)
    try:
        token = SlackTokenStore(backend=_token_backend()).load(team_id)
        report = SlackOAuthTransport(SlackApiClient(token)).sync(
            corpus_id,
            channels=channels or None,
            ingest=not no_ingest,
        )
    except SlackOAuthError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))


@slack_app.command("revoke-token")
def slack_revoke_token(team_id: str) -> None:
    revoked = SlackTokenStore(backend=_token_backend()).revoke(team_id)
    typer.echo(json.dumps({"provider": "slack", "team_id": team_id, "revoked": revoked}, ensure_ascii=False, indent=2))


@google_app.command("auth-url")
def google_auth_url(
    state: str = "ame",
    client_id: str | None = typer.Option(None, "--client-id"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Google OAuth scopes."),
) -> None:
    ensure_runtime_layout()
    config = _google_config(client_id=client_id, redirect_uri=redirect_uri, scopes=scopes)
    _require_option(config.client_id, "--client-id or [google].client_id", provider="Google OAuth")
    typer.echo(GoogleOAuthClient(config).authorization_url(state))


@google_app.command("exchange-code")
def google_exchange_code(
    code: str,
    account_id: str = typer.Option("default", "--account-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Google OAuth scopes."),
) -> None:
    ensure_runtime_layout()
    config = _google_config(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scopes=scopes)
    _require_option(config.client_id, "--client-id or [google].client_id", provider="Google OAuth")
    _require_option(config.client_secret, "--client-secret or [google].client_secret", provider="Google OAuth")
    try:
        token = exchange_and_save_google_token(code, config, account_id=account_id, token_backend=_token_backend())
    except GoogleOAuthError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(redact_secrets(token.model_dump(mode="json")), ensure_ascii=False, indent=2))


@google_app.command("login")
def google_login(
    account_id: str = typer.Option("default", "--account-id"),
    client_id: str | None = typer.Option(None, "--client-id"),
    client_secret: str | None = typer.Option(None, "--client-secret"),
    redirect_uri: str | None = typer.Option(None, "--redirect-uri"),
    scopes: str | None = typer.Option(None, "--scopes", help="Comma-separated Google OAuth scopes."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-browser"),
    timeout: int = typer.Option(180, "--timeout", min=10),
) -> None:
    try:
        token = _connector_login(
            "google",
            account_id=account_id,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            open_browser=open_browser,
            timeout=timeout,
        )
    except (OAuthCallbackError, GoogleOAuthError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(redact_secrets(token), ensure_ascii=False, indent=2))


@google_app.command("revoke-token")
def google_revoke_token(account_id: str = typer.Option("default", "--account-id")) -> None:
    revoked = GoogleTokenStore(backend=_token_backend()).revoke(account_id)
    typer.echo(json.dumps({"provider": "google", "account_id": account_id, "revoked": revoked}, ensure_ascii=False, indent=2))


@app.command()
def serve(corpus_id: str, mcp: bool = typer.Option(False, "--mcp")) -> None:
    root = require_corpus(corpus_id)
    if not mcp:
        typer.echo("Only MCP stdio mode is available in this build. Use --mcp.")
        raise typer.Exit(1)
    McpStdioServer(root).run()


@app.command()
def stats(corpus_id: str) -> None:
    root = require_corpus(corpus_id)
    state = CorpusStateStore(root).read()
    typer.echo(f"Corpus: {corpus_id}")
    typer.echo(f"Last ingest: {state.last_ingest_at or 'never'}")
    typer.echo(f"Mode: {state.last_mode or 'n/a'}")
    for key in ["documents", "silver_entities", "silver_relations", "silver_decisions", "silver_rationales", "rejected", "gold_nodes", "gold_edges"]:
        typer.echo(f"{key}: {state.counts.get(key, 0)}")


@app.command("inspect")
def inspect_corpus(corpus_id: str) -> None:
    root = require_corpus(corpus_id)
    state = CorpusStateStore(root).read()
    typer.echo(f"Corpus: {corpus_id}")
    typer.echo(f"Source path: {state.last_source_path or 'n/a'}")
    for document in state.documents:
        typer.echo(f"- {document.id} {document.source_id} {document.content_hash}")


@export_app.command("obsidian")
def export_obsidian(corpus_id: str, output_dir: Path) -> None:
    root = require_corpus(corpus_id)
    count = ObsidianExporter(GoldStore(root)).export(output_dir)
    typer.echo(f"Exported {count} note(s): {output_dir}")


@lightrag_app.command("status")
def lightrag_status(corpus_id: str) -> None:
    root = require_corpus(corpus_id)
    status = LightRagAdapter(root).status()
    typer.echo(f"Backend: {status.get('backend')}")
    typer.echo(f"Package available: {status.get('package_available')}")
    typer.echo(f"Ollama host: {status.get('ollama_host')}")
    typer.echo(f"Ollama server available: {status.get('ollama_server_available')}")
    if status.get("ollama_server_error"):
        typer.echo(f"Ollama server error: {status.get('ollama_server_error')}")
    typer.echo(f"Initialized: {status.get('initialized')}")
    if status.get("error"):
        typer.echo(f"Error: {status.get('error')}")
    if status.get("backend_error"):
        typer.echo(f"Backend error: {status.get('backend_error')}")
    typer.echo(f"custom_kg: {status.get('custom_kg_path', 'n/a')}")
    typer.echo(f"chunks: {status.get('chunks', 0)}")
    typer.echo(f"entities: {status.get('entities', 0)}")
    typer.echo(f"relationships: {status.get('relationships', 0)}")


@mcp_app.command("manifest")
def mcp_manifest(corpus_id: str) -> None:
    root = require_corpus(corpus_id)
    typer.echo(json.dumps(LocalMcpToolbox.manifest(root.name), ensure_ascii=False, indent=2))


@mcp_app.command("bootstrap-manifest")
def mcp_bootstrap_manifest() -> None:
    typer.echo(json.dumps(BootstrapMcpToolbox.manifest(), ensure_ascii=False, indent=2))


@mcp_app.command("call")
def mcp_call(corpus_id: str, tool_name: str, arguments_json: str = typer.Argument("{}")) -> None:
    root = require_corpus(corpus_id)
    try:
        arguments = json.loads(arguments_json)
        result = LocalMcpToolbox(root).call(tool_name, arguments)
    except (json.JSONDecodeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@mcp_app.command("stdio")
def mcp_stdio(corpus_id: str | None = typer.Argument(None)) -> None:
    root = require_corpus(corpus_id) if corpus_id is not None else None
    McpStdioServer(root).run()


def _slack_config(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
    scopes: str | None = None,
) -> SlackOAuthConfig:
    stored = load_config().slack
    return SlackOAuthConfig(
        client_id=client_id if client_id is not None else stored.client_id,
        client_secret=client_secret if client_secret is not None else stored.client_secret,
        redirect_uri=redirect_uri if redirect_uri is not None else stored.redirect_uri,
        scopes=_parse_scopes(scopes) if scopes is not None else list(stored.scopes),
    )


def _google_config(
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
    scopes: str | None = None,
) -> GoogleOAuthConfig:
    stored = load_config().google
    return GoogleOAuthConfig(
        client_id=client_id if client_id is not None else stored.client_id,
        client_secret=client_secret if client_secret is not None else stored.client_secret,
        redirect_uri=redirect_uri if redirect_uri is not None else stored.redirect_uri,
        scopes=_parse_scopes(scopes) if scopes is not None else list(stored.scopes),
    )


def _connector_login(
    provider: str,
    *,
    account_id: str,
    client_id: str | None,
    client_secret: str | None,
    redirect_uri: str | None,
    scopes: str | None,
    open_browser: bool,
    timeout: int,
) -> dict:
    normalized = provider.casefold().replace("_", "-")
    if normalized == "google":
        config = _google_config(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scopes=scopes)
        _require_option(config.client_id, "--client-id or [google].client_id", provider="Google OAuth")
        _require_option(config.client_secret, "--client-secret or [google].client_secret", provider="Google OAuth")
        state = new_oauth_state()
        url = GoogleOAuthClient(config).authorization_url(state)
        code = _wait_for_oauth_code(url, config.redirect_uri, state, open_browser=open_browser, timeout=timeout)
        token = exchange_and_save_google_token(code, config, account_id=account_id, token_backend=_token_backend())
        return token.model_dump(mode="json")
    if normalized == "slack":
        config = _slack_config(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scopes=scopes)
        _require_option(config.client_id, "--client-id or [slack].client_id")
        _require_option(config.client_secret, "--client-secret or [slack].client_secret")
        state = new_oauth_state()
        url = SlackOAuthClient(config).authorization_url(state)
        code = _wait_for_oauth_code(url, config.redirect_uri, state, open_browser=open_browser, timeout=timeout)
        token = exchange_and_save_slack_token(code, config, token_backend=_token_backend())
        return token.model_dump(mode="json")

    spec = provider_spec(provider)
    config = default_config(
        spec.name,
        client_id=client_id or "",
        client_secret=client_secret or "",
        redirect_uri=redirect_uri,
        scopes=_parse_scopes(scopes) if scopes is not None else None,
    )
    _require_option(config.client_id, f"--client-id for {spec.name}", provider=f"{spec.name} OAuth")
    _require_option(config.client_secret, f"--client-secret for {spec.name}", provider=f"{spec.name} OAuth")
    state = new_oauth_state()
    url = ConnectedAppOAuthClient(config, spec=spec).authorization_url(state)
    code = _wait_for_oauth_code(url, config.redirect_uri, state, open_browser=open_browser, timeout=timeout)
    token = exchange_and_save_connected_app_token(spec.name, code, config, account_id=account_id, token_backend=_token_backend())
    return token.model_dump(mode="json")


def _wait_for_oauth_code(authorization_url: str, redirect_uri: str, state: str, *, open_browser: bool, timeout: int) -> str:
    if not open_browser:
        typer.echo(f"Open this URL to connect: {authorization_url}")
    else:
        typer.echo("Opening browser for OAuth login...")
    result = run_local_oauth_login(
        authorization_url,
        redirect_uri,
        state,
        open_browser=open_browser,
        timeout_seconds=timeout,
    )
    return result.code


def _load_registry() -> ModelRegistry:
    return load_default_registry()


def _profile_disk_path() -> Path:
    home = ame_home()
    return home if home.exists() else Path.home()


def _parse_scopes(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _token_backend() -> str:
    return load_config().security.token_backend


def _require_option(value: str, label: str, provider: str = "Slack OAuth") -> None:
    if not value:
        typer.echo(f"Missing required {provider} setting: {label}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
