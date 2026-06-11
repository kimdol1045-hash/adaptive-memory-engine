from __future__ import annotations

import os
import platform
from pathlib import Path

from ame.gold.ontology import write_base_ontology
from ame.models.registry import ModelRegistry
from ame.security import ensure_private_dir, ensure_private_file


def ame_home() -> Path:
    override = os.environ.get("AME_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return default_ame_home()


def default_ame_home() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path("~/Library/Application Support/ame").expanduser()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base).expanduser() / "AdaptiveMemoryEngine"
        return Path.home() / "AppData" / "Local" / "AdaptiveMemoryEngine"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "ame"
    return Path("~/.local/share/ame").expanduser()


def corpus_path(corpus_id: str) -> Path:
    return ame_home() / "corpora" / corpus_id


def ensure_runtime_layout() -> Path:
    home = ame_home()
    ensure_private_dir(home)
    (home / "models").mkdir(parents=True, exist_ok=True)
    (home / "corpora").mkdir(parents=True, exist_ok=True)
    ensure_private_dir(home / "tokens")
    ModelRegistry().write_cache(home / "registry.cache.yaml")
    config = home / "config.toml"
    if not config.exists():
        config.write_text(
            "\n".join(
                [
                    "[engine]",
                    "confidence_threshold = 0.7",
                    "",
                    "[lightrag]",
                    'backend = "auto"',
                    'query_mode = "hybrid"',
                    'ollama_host = "http://127.0.0.1:11434"',
                    'llm_model = "qwen3:8b"',
                    'embedding_model = "nomic-embed-text"',
                    "embedding_dim = 768",
                    "max_token_size = 8192",
                    "",
                    "[slack]",
                    'client_id = ""',
                    'client_secret = ""',
                    'redirect_uri = "http://localhost:8765/slack/oauth/callback"',
                    'scopes = ["channels:read", "channels:history", "groups:read", "groups:history"]',
                    "",
                    "[google]",
                    'client_id = ""',
                    'client_secret = ""',
                    'redirect_uri = "http://localhost:8765/google/oauth/callback"',
                    'scopes = [',
                    '  "https://www.googleapis.com/auth/drive.readonly",',
                    '  "https://www.googleapis.com/auth/gmail.readonly",',
                    '  "https://www.googleapis.com/auth/calendar.readonly",',
                    '  "https://www.googleapis.com/auth/spreadsheets.readonly",',
                    "]",
                    "",
                    "[security]",
                    'token_backend = "file"',
                    'pii_redaction = "off"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    ensure_private_file(config)
    return home


def ensure_corpus_layout(corpus_id: str) -> Path:
    root = corpus_path(corpus_id)
    for rel in [
        "bronze/documents",
        "silver",
        "gold",
        "ontology",
        "store/lightrag",
        "exports/obsidian",
        "connectors",
        "imports",
    ]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    corpus_file = root / "corpus.toml"
    if not corpus_file.exists():
        corpus_file.write_text(f'id = "{corpus_id}"\n', encoding="utf-8")
    write_base_ontology(root / "ontology" / "base.yaml")
    state_db = root / "state.db"
    if not state_db.exists():
        state_db.write_text("", encoding="utf-8")
    return root
