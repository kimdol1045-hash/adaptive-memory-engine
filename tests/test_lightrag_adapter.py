import asyncio
import json
from pathlib import Path

from ame.bronze.schema import BronzeDocument
from ame.bronze.store import BronzeStore
from ame.core.config import LightRagConfig
from ame.core.errors import LightRagBackendError
from ame.gold.schema import GoldEdge, GoldNode
from ame.gold.store import GoldStore
from ame.query.result import QueryResult
from ame.storage.lightrag_adapter import CoreLightRagBackend, LightRagAdapter, effective_embedding_max_token_size


def test_lightrag_adapter_stages_custom_kg_and_status(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw uses LightRAG",
        content_hash="sha256:x",
    )
    node = GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"])
    edge = GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=["bronze_1"])

    adapter = LightRagAdapter(corpus_root, config=LightRagConfig(backend="filesystem"))
    path = asyncio.run(adapter.insert_gold([node], [edge], [doc]))

    payload = json.loads(path.read_text(encoding="utf-8"))
    status = adapter.status()
    assert payload["entities"][0]["entity_name"] == "LightRAG"
    assert status["initialized"] is True
    assert status["chunks"] == 1
    assert status["relationships"] == 1


def test_lightrag_adapter_query_uses_local_fallback(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw uses LightRAG",
        content_hash="sha256:x",
    )
    BronzeStore(corpus_root).put(doc)
    GoldStore(corpus_root).replace(
        [GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"])],
        [GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=["bronze_1"])],
    )

    result = asyncio.run(LightRagAdapter(corpus_root, config=LightRagConfig(backend="filesystem")).query("LightRAG"))

    assert "LightRAG" in result.answer
    assert result.sources[0].document == "openclaw.md"
    assert result.raw["adapter"]["mode"] == "hybrid"


class FakeCoreBackend:
    name = "lightrag-core"

    def __init__(self) -> None:
        self.initialized = False
        self.inserted = None
        self.queries: list[tuple[str, str]] = []

    async def initialize(self) -> None:
        self.initialized = True

    async def insert_custom_kg(self, custom_kg: dict) -> None:
        self.inserted = custom_kg

    async def query(self, question: str, mode: str) -> QueryResult:
        self.queries.append((question, mode))
        return QueryResult(
            answer="core answer",
            matches=["core answer"],
            raw={"adapter": {"backend": self.name, "mode": mode}},
        )

    def status(self) -> dict:
        return {"backend": self.name, "initialized": self.initialized, "package_available": True}


def test_lightrag_adapter_can_use_injected_core_backend(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw uses LightRAG",
        content_hash="sha256:x",
    )
    node = GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"])
    edge = GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=["bronze_1"])
    backend = FakeCoreBackend()

    adapter = LightRagAdapter(corpus_root, backend=backend)
    asyncio.run(adapter.insert_gold([node], [edge], [doc]))
    result = asyncio.run(adapter.query("LightRAG", mode="hybrid"))

    assert backend.initialized is True
    assert backend.inserted["relationships"][0]["src_id"] == "OpenClaw"
    assert result.answer == "core answer"
    assert adapter.status()["backend"] == "lightrag-core"


class FailingBackend(FakeCoreBackend):
    async def insert_custom_kg(self, custom_kg: dict) -> None:
        raise LightRagBackendError("embedding backend unavailable")


def test_lightrag_adapter_records_staged_kg_when_backend_insert_fails(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    doc = BronzeDocument(
        id="bronze_1",
        corpus_id="openclaw",
        source_type="markdown",
        source_id="openclaw.md",
        content="OpenClaw uses LightRAG",
        content_hash="sha256:x",
    )
    node = GoldNode(id="node_1", corpus_id="openclaw", type="Tool", name="LightRAG", canonical_name="lightrag", source_ids=["bronze_1"])
    edge = GoldEdge(id="edge_1", corpus_id="openclaw", source="OpenClaw", relation="USES", target="LightRAG", source_ids=["bronze_1"])
    adapter = LightRagAdapter(corpus_root, backend=FailingBackend())

    try:
        asyncio.run(adapter.insert_gold([node], [edge], [doc]))
    except LightRagBackendError:
        pass
    else:
        raise AssertionError("expected LightRagBackendError")

    status = adapter.status()
    assert adapter.custom_kg_path.exists()
    assert status["chunks"] == 1
    assert status["relationships"] == 1
    assert status["backend_error"] == "embedding backend unavailable"


def test_lightrag_adapter_status_preserves_persisted_initialization(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ame.storage.lightrag_adapter.light_rag_package_available", lambda: False)
    monkeypatch.setattr(
        "ame.storage.lightrag_adapter.ollama_server_status",
        lambda host: {"ollama_host": host, "ollama_server_available": False},
    )
    adapter = LightRagAdapter(tmp_path / "corpus", config=LightRagConfig(backend="core"))
    adapter.state_path.write_text(
        json.dumps(
            {
                "backend": "lightrag-core",
                "initialized": True,
                "custom_kg_path": str(adapter.custom_kg_path),
                "chunks": 1,
                "entities": 9,
                "relationships": 4,
            }
        ),
        encoding="utf-8",
    )

    status = adapter.status()

    assert status["backend"] == "lightrag-core"
    assert status["initialized"] is True
    assert status["relationships"] == 4


def test_lightrag_adapter_core_config_reports_unavailable_when_package_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ame.storage.lightrag_adapter.light_rag_package_available", lambda: False)
    adapter = LightRagAdapter(tmp_path / "corpus", config=LightRagConfig(backend="core"))

    status = adapter.status()
    assert status["backend"] == "lightrag-core"
    assert status["available"] is False
    try:
        asyncio.run(adapter.initialize())
    except LightRagBackendError as exc:
        assert "not installed" in str(exc)
    else:
        raise AssertionError("expected LightRagBackendError")


def test_lightrag_auto_selects_core_when_package_server_and_models_available(tmp_path: Path, monkeypatch) -> None:
    class FakeInstaller:
        def __init__(self, host: str) -> None:
            self.host = host

        def installed_models(self) -> list[str]:
            return ["qwen3:8b", "nomic-embed-text:latest"]

    monkeypatch.setattr("ame.storage.lightrag_adapter.light_rag_package_available", lambda: True)
    monkeypatch.setattr(
        "ame.storage.lightrag_adapter.ollama_server_status",
        lambda host: {"ollama_host": host, "ollama_server_available": True},
    )
    monkeypatch.setattr("ame.storage.lightrag_adapter.OllamaModelInstaller", FakeInstaller)

    adapter = LightRagAdapter(tmp_path / "corpus", config=LightRagConfig(backend="auto"))

    assert adapter.status()["backend"] == "lightrag-core"


def test_nomic_embed_text_max_token_size_is_clamped_to_model_context() -> None:
    config = LightRagConfig(embedding_model="nomic-embed-text", max_token_size=8192)

    assert effective_embedding_max_token_size(config) == 2048


def test_lightrag_auto_falls_back_when_required_models_missing(tmp_path: Path, monkeypatch) -> None:
    class FakeInstaller:
        def __init__(self, host: str) -> None:
            self.host = host

        def installed_models(self) -> list[str]:
            return ["qwen3:8b"]

    monkeypatch.setattr("ame.storage.lightrag_adapter.light_rag_package_available", lambda: True)
    monkeypatch.setattr(
        "ame.storage.lightrag_adapter.ollama_server_status",
        lambda host: {"ollama_host": host, "ollama_server_available": True},
    )
    monkeypatch.setattr("ame.storage.lightrag_adapter.OllamaModelInstaller", FakeInstaller)

    adapter = LightRagAdapter(tmp_path / "corpus", config=LightRagConfig(backend="auto"))

    assert adapter.status()["backend"] == "filesystem"


class FakeQueryParam:
    def __init__(self, mode: str) -> None:
        self.mode = mode


class FakeRagCore:
    def __init__(self) -> None:
        self.initialized = False
        self.custom_kg = None
        self.query_param = None

    async def initialize_storages(self) -> None:
        self.initialized = True

    def insert_custom_kg(self, custom_kg: dict) -> None:
        self.custom_kg = custom_kg

    async def aquery(self, question: str, param: FakeQueryParam) -> str:
        self.query_param = param
        return f"answer: {question}"


def test_core_lightrag_backend_uses_core_api_methods() -> None:
    rag = FakeRagCore()
    backend = CoreLightRagBackend(rag, FakeQueryParam)

    asyncio.run(backend.initialize())
    asyncio.run(backend.insert_custom_kg({"entities": [], "relationships": [], "chunks": []}))
    result = asyncio.run(backend.query("What did OpenClaw use?", mode="hybrid"))

    assert rag.initialized is True
    assert rag.custom_kg == {"entities": [], "relationships": [], "chunks": []}
    assert rag.query_param.mode == "hybrid"
    assert result.answer == "answer: What did OpenClaw use?"


def test_core_lightrag_backend_initializes_before_query() -> None:
    rag = FakeRagCore()
    backend = CoreLightRagBackend(rag, FakeQueryParam)

    result = asyncio.run(backend.query("What did OpenClaw use?", mode="hybrid"))

    assert rag.initialized is True
    assert backend.initialized is True
    assert result.answer == "answer: What did OpenClaw use?"


class FakeNoAnswerRag(FakeRagCore):
    async def aquery(self, question: str, param: FakeQueryParam) -> None:
        return None


def test_core_lightrag_backend_rejects_empty_query_answer() -> None:
    backend = CoreLightRagBackend(FakeNoAnswerRag(), FakeQueryParam)

    try:
        asyncio.run(backend.query("What did OpenClaw use?", mode="hybrid"))
    except LightRagBackendError as exc:
        assert "returned no answer" in str(exc)
    else:
        raise AssertionError("expected LightRagBackendError")
