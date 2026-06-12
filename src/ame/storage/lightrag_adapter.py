from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Protocol
from urllib.request import urlopen

from ame.bronze.schema import BronzeDocument
from ame.bronze.store import BronzeStore
from ame.core.config import LightRagConfig, load_config
from ame.core.errors import LightRagBackendError
from ame.gold.schema import GoldEdge, GoldNode
from ame.gold.store import GoldStore
from ame.models.download import ModelDownloadError, OllamaModelInstaller, is_model_installed
from ame.query.engine import QueryEngine
from ame.query.result import QueryResult
from ame.storage.custom_kg import to_custom_kg


class LightRagBackend(Protocol):
    name: str

    async def initialize(self) -> None:
        ...

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        ...

    async def query(self, question: str, mode: str) -> QueryResult:
        ...

    def status(self) -> dict:
        ...


class FilesystemLightRagBackend:
    name = "filesystem"

    def __init__(self, corpus_root: Path, config: LightRagConfig | None = None):
        self.corpus_root = corpus_root
        self.config = config or LightRagConfig()

    async def initialize(self) -> None:
        return None

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        return None

    async def query(self, question: str, mode: str) -> QueryResult:
        result = QueryEngine(BronzeStore(self.corpus_root), GoldStore(self.corpus_root)).query(question)
        raw = result.raw or {}
        raw["adapter"] = {"backend": self.name, "mode": mode}
        result.raw = raw
        return result

    def status(self) -> dict:
        return {
            "backend": self.name,
            "package_available": light_rag_package_available(),
            **ollama_server_status(self.config.ollama_host),
        }


class UnavailableLightRagBackend:
    name = "lightrag-core"

    def __init__(self, reason: str, config: LightRagConfig | None = None):
        self.reason = reason
        self.config = config or LightRagConfig()

    async def initialize(self) -> None:
        raise LightRagBackendError(self.reason)

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        raise LightRagBackendError(self.reason)

    async def query(self, question: str, mode: str) -> QueryResult:
        raise LightRagBackendError(self.reason)

    def status(self) -> dict:
        return {
            "backend": self.name,
            "package_available": light_rag_package_available(),
            "available": False,
            "error": self.reason,
            **ollama_server_status(self.config.ollama_host),
        }


class DeferredCoreLightRagBackend:
    name = "lightrag-core"

    def __init__(self, corpus_root: Path, config: LightRagConfig):
        self.corpus_root = corpus_root
        self.config = config
        self.backend: CoreLightRagBackend | None = None

    async def initialize(self) -> None:
        await self._backend().initialize()

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        await self._backend().insert_custom_kg(custom_kg)

    async def query(self, question: str, mode: str) -> QueryResult:
        return await self._backend().query(question, mode)

    def status(self) -> dict:
        if self.backend is not None:
            return self.backend.status()
        package_available = light_rag_package_available()
        status = {
            "backend": self.name,
            "package_available": package_available,
            "initialized": False,
            "available": package_available,
            **ollama_server_status(self.config.ollama_host),
        }
        if not package_available:
            status["error"] = "LightRAG core package is not installed."
        return status

    def _backend(self) -> CoreLightRagBackend:
        if self.backend is None:
            self.backend = CoreLightRagBackend.from_config(self.corpus_root, self.config)
        return self.backend


class CoreLightRagBackend:
    name = "lightrag-core"

    def __init__(self, rag: object, query_param_cls: type | None = None, config: LightRagConfig | None = None):
        self.rag = rag
        self.query_param_cls = query_param_cls
        self.config = config or LightRagConfig()
        self.effective_max_token_size = effective_embedding_max_token_size(self.config)
        self.initialized = False

    @classmethod
    def from_config(cls, corpus_root: Path, config: LightRagConfig) -> CoreLightRagBackend:
        if not light_rag_package_available():
            raise LightRagBackendError("LightRAG core package is not installed.")
        try:
            from lightrag import LightRAG, QueryParam
            from lightrag.llm.ollama import ollama_embed, ollama_model_complete
            from lightrag.utils import Tokenizer, wrap_embedding_func_with_attrs
        except ImportError as exc:
            raise LightRagBackendError(f"LightRAG core imports failed: {exc}") from exc

        @wrap_embedding_func_with_attrs(
            embedding_dim=config.embedding_dim,
            max_token_size=effective_embedding_max_token_size(config),
            model_name=config.embedding_model,
        )
        async def embedding_func(texts: list[str]):
            return await ollama_embed.func(texts, embed_model=config.embedding_model, host=config.ollama_host)

        try:
            rag = LightRAG(
                working_dir=str(corpus_root / "store" / "lightrag" / "core"),
                llm_model_func=ollama_model_complete,
                llm_model_name=config.llm_model,
                llm_model_kwargs={"host": config.ollama_host},
                embedding_func=embedding_func,
                tokenizer=Tokenizer("ame-char", CharTokenizer()),
            )
        except Exception as exc:
            raise LightRagBackendError(f"LightRAG core initialization failed: {exc}") from exc
        return cls(rag, QueryParam, config)

    async def initialize(self) -> None:
        method = getattr(self.rag, "initialize_storages", None)
        if method is not None:
            try:
                await _maybe_await(method())
            except Exception as exc:
                raise LightRagBackendError(f"LightRAG storage initialization failed: {exc}") from exc
        self.initialized = True

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        method = getattr(self.rag, "ainsert_custom_kg", None) or getattr(self.rag, "insert_custom_kg", None)
        if method is None:
            raise LightRagBackendError("LightRAG core object does not expose insert_custom_kg.")
        try:
            await _maybe_await(method(custom_kg))
        except Exception as exc:
            raise LightRagBackendError(f"LightRAG custom KG insert failed: {exc}") from exc

    async def query(self, question: str, mode: str) -> QueryResult:
        if not self.initialized:
            await self.initialize()
        param = self.query_param_cls(mode=mode) if self.query_param_cls is not None else None
        method = getattr(self.rag, "aquery", None) or getattr(self.rag, "query", None)
        if method is None:
            raise LightRagBackendError("LightRAG core object does not expose query.")
        try:
            raw_answer = await _maybe_await(method(question, param=param))
        except Exception as exc:
            raise LightRagBackendError(f"LightRAG query failed: {exc}") from exc
        if raw_answer is None:
            raise LightRagBackendError("LightRAG query returned no answer.")
        answer = raw_answer if isinstance(raw_answer, str) else json.dumps(raw_answer, ensure_ascii=False)
        return QueryResult(
            answer=answer,
            matches=[answer],
            sources=[],
            confidence=None,
            raw={"adapter": {"backend": self.name, "mode": mode}},
        )

    def status(self) -> dict:
        return {
            "backend": self.name,
            "package_available": light_rag_package_available(),
            "initialized": self.initialized,
            "max_token_size": self.config.max_token_size,
            "effective_max_token_size": self.effective_max_token_size,
            **ollama_server_status(self.config.ollama_host),
        }


class LightRagAdapter:
    """LightRAG boundary with a local filesystem fallback.

    The MVP always stages a LightRAG-compatible custom_kg payload. Until the
    external LightRAG runtime is wired in, query uses the same Gold/Bronze data
    through a local fallback so the CLI contract is stable.
    """

    def __init__(self, corpus_root: Path, backend: LightRagBackend | None = None, config: LightRagConfig | None = None):
        self.corpus_root = corpus_root
        self.root = corpus_root / "store" / "lightrag"
        self.custom_kg_path = self.root / "custom_kg.json"
        self.state_path = self.root / "adapter_state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config or load_config().lightrag
        self.backend = backend or self._select_backend(self.config)

    async def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        await self.backend.initialize()
        state = {"initialized": True}
        state.update(self.backend.status())
        self._write_state(**state)

    async def insert_gold(self, nodes: list[GoldNode], edges: list[GoldEdge], chunks: list[BronzeDocument] | None = None) -> Path:
        payload = to_custom_kg(nodes, edges, chunks)
        self.custom_kg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        state = {
            "initialized": False,
            "custom_kg_path": str(self.custom_kg_path),
            "chunks": len(payload["chunks"]),
            "entities": len(payload["entities"]),
            "relationships": len(payload["relationships"]),
        }
        state.update(self.backend.status())
        self._write_state(**state)
        try:
            await self.backend.initialize()
            await self.backend.insert_custom_kg(payload)
        except LightRagBackendError as exc:
            failed_state = dict(state)
            failed_state.update(self.backend.status())
            failed_state["backend_error"] = str(exc)
            self._write_state(**failed_state)
            raise
        state["initialized"] = True
        state["backend_error"] = None
        state.update(self.backend.status())
        self._write_state(**state)
        return self.custom_kg_path

    async def query(self, question: str, mode: str = "hybrid") -> QueryResult:
        return await self.backend.query(question, mode)

    def sync(self, nodes: list[GoldNode], edges: list[GoldEdge], chunks: list[BronzeDocument] | None = None) -> Path:
        return _run_sync(self.insert_gold(nodes, edges, chunks))

    def status(self) -> dict:
        backend_status = self.backend.status()
        current = {"initialized": False, "custom_kg_path": str(self.custom_kg_path), **backend_status}
        if not self.state_path.exists():
            return current
        persisted = json.loads(self.state_path.read_text(encoding="utf-8"))
        current.update(persisted)
        current.update(backend_status)
        if persisted.get("initialized") is True and backend_status.get("initialized") is False:
            current["initialized"] = True
        return current

    def _select_backend(self, config: LightRagConfig) -> LightRagBackend:
        if config.backend == "filesystem":
            return FilesystemLightRagBackend(self.corpus_root, config)
        if config.backend == "core":
            return DeferredCoreLightRagBackend(self.corpus_root, config)
        if self._core_backend_available(config):
            return DeferredCoreLightRagBackend(self.corpus_root, config)
        return FilesystemLightRagBackend(self.corpus_root, config)

    def _core_backend_available(self, config: LightRagConfig) -> bool:
        if not light_rag_package_available():
            return False
        status = ollama_server_status(config.ollama_host)
        if not status.get("ollama_server_available"):
            return False
        try:
            installed = OllamaModelInstaller(host=config.ollama_host).installed_models()
        except ModelDownloadError:
            return False
        return is_model_installed(config.llm_model, installed) and is_model_installed(config.embedding_model, installed)

    def _write_state(self, **values: object) -> None:
        state = {
            "backend": "filesystem",
            "initialized": False,
            "custom_kg_path": str(self.custom_kg_path),
        }
        if self.state_path.exists():
            state.update(json.loads(self.state_path.read_text(encoding="utf-8")))
        state.update(values)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def light_rag_package_available() -> bool:
    return importlib.util.find_spec("lightrag") is not None


def ollama_server_status(host: str) -> dict:
    url = f"{host.rstrip('/')}/api/tags"
    try:
        with urlopen(url, timeout=2) as response:
            return {
                "ollama_host": host,
                "ollama_server_available": 200 <= response.status < 300,
            }
    except Exception as exc:
        return {
            "ollama_host": host,
            "ollama_server_available": False,
            "ollama_server_error": str(exc),
        }


def effective_embedding_max_token_size(config: LightRagConfig) -> int:
    model = config.embedding_model.casefold()
    if model.startswith("nomic-embed-text"):
        return min(config.max_token_size, 2048)
    return config.max_token_size


class CharTokenizer:
    def encode(self, content: str) -> list[int]:
        return [ord(char) for char in content]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


def _run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise LightRagBackendError("LightRagAdapter.sync cannot run inside an active event loop; use insert_gold instead.")
