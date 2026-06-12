from pathlib import Path

from ame.agent.corpus_router import suggest_corpus
from ame.core.corpus import create_corpus
from ame.core.errors import LlmClientError
from ame.core.paths import ensure_runtime_layout
from ame.core.state import CorpusStateStore
from ame.bronze.store import BronzeStore
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline


class FakeClient:
    def __init__(self) -> None:
        self.source_ids: list[str] = []

    def complete_json(self, prompt: str, payload: dict) -> dict:
        self.source_ids.append(str(payload.get("source_id")))
        return {
            "entities": [
                {"type": "Project", "name": "OpenClaw", "span": "OpenClaw", "confidence": 0.9},
                {"type": "Tool", "name": "LightRAG", "span": "LightRAG", "confidence": 0.9},
            ],
            "relations": [
                {"subject": "OpenClaw", "predicate": "USES", "object": "LightRAG", "confidence": 0.9}
            ],
        }


class FailingClient:
    def complete_json(self, prompt: str, payload: dict) -> dict:
        raise LlmClientError("test extraction failure")


class ContentEntityClient:
    def complete_json(self, prompt: str, payload: dict) -> dict:
        content = str(payload.get("content") or "")
        name = "NewMemoryPolicy" if "NewMemoryPolicy" in content else "OldMemoryPolicy"
        return {
            "entities": [{"type": "Concept", "name": name, "span": name, "confidence": 0.9}],
            "relations": [],
            "decisions": [],
        }


def test_pipeline_llm_mode_uses_client_and_records_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    corpus_root = create_corpus("openclaw")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "openclaw.md").write_text(
        "---\nproject: OpenClaw\n---\nOpenClaw decided to use LightRAG.\n",
        encoding="utf-8",
    )

    report = MemoryPipeline().ingest("openclaw", notes, mode="llm", llm_client=FakeClient())
    state = CorpusStateStore(corpus_root).read()

    assert report.mode == "llm"
    assert report.gold_edges == 3
    assert state.last_mode == "llm"


def test_pipeline_llm_mode_uses_hardware_routed_default_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("routed")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "routed.md").write_text("Hermes decided to use Adaptive Memory Engine.\n", encoding="utf-8")
    captured: dict[str, str | None] = {}

    class RoutedFakeClient(FakeClient):
        def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
            super().__init__()
            captured["model"] = model
            captured["base_url"] = base_url

    monkeypatch.setattr("ame.pipeline.OllamaClient", RoutedFakeClient)

    report = MemoryPipeline().ingest("routed", notes, mode="llm")

    assert report.mode == "llm"
    assert captured["model"] == "qwen3:8b"
    assert captured["base_url"] == "http://127.0.0.1:11434"


def test_pipeline_only_processes_current_source_documents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    corpus_root = create_corpus("current-only")
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "old.md").write_text("# Old\nOld project decided to use LegacyRAG.\n", encoding="utf-8")
    (second / "new.md").write_text("# New\nNew project decided to use LightRAG.\n", encoding="utf-8")
    first_client = FakeClient()
    second_client = FakeClient()

    first_report = MemoryPipeline().ingest("current-only", first, mode="llm", llm_client=first_client)
    second_report = MemoryPipeline().ingest("current-only", second, mode="llm", llm_client=second_client)
    state = CorpusStateStore(corpus_root).read()

    assert first_report.documents == 1
    assert second_report.documents == 2
    assert first_client.source_ids == ["old.md"]
    assert second_client.source_ids == ["new.md"]
    assert {document.source_id for document in state.documents} == {"old.md", "new.md"}


def test_pipeline_updates_same_source_as_current_view_and_keeps_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    corpus_root = create_corpus("updates")
    source = tmp_path / "notes"
    source.mkdir()
    note = source / "policy.md"
    note.write_text("# Policy\nOldMemoryPolicy is the current memory policy.\n", encoding="utf-8")

    MemoryPipeline().ingest("updates", source, mode="llm", llm_client=ContentEntityClient())
    note.write_text("# Policy\nNewMemoryPolicy is the current memory policy.\n", encoding="utf-8")
    MemoryPipeline().ingest("updates", source, mode="llm", llm_client=ContentEntityClient())

    docs = list(BronzeStore(corpus_root).list())
    active_docs = [doc for doc in docs if doc.metadata.get("active", True) is not False]
    inactive_docs = [doc for doc in docs if doc.metadata.get("active", True) is False]
    node_names = {node.name for node in GoldStore(corpus_root).nodes()}

    assert len(docs) == 2
    assert len(active_docs) == 1
    assert len(inactive_docs) == 1
    assert "NewMemoryPolicy" in node_names
    assert "OldMemoryPolicy" not in node_names
    assert list((corpus_root / "history" / "source_updates").glob("*.json"))


def test_corpus_suggestion_routes_same_source_to_existing_corpus(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("planning")
    source = tmp_path / "planning"
    source.mkdir()
    (source / "plan.md").write_text("# Plan\nOpenClaw decided to use LightRAG.\n", encoding="utf-8")
    MemoryPipeline().ingest("planning", source, mode="llm", llm_client=FakeClient())

    suggestion = suggest_corpus(source)

    assert suggestion.action == "update_existing"
    assert suggestion.selected_corpus_id == "planning"
    assert suggestion.confidence >= 0.72


def test_pipeline_rolls_back_new_corpus_outputs_when_llm_ingest_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    corpus_root = create_corpus("rollback-new")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "bad.md").write_text("# Bad\nThis document triggers a failing local LLM call.\n", encoding="utf-8")

    try:
        MemoryPipeline().ingest("rollback-new", notes, mode="llm", llm_client=FailingClient())
    except LlmClientError:
        pass
    else:
        raise AssertionError("expected LlmClientError")

    assert list(BronzeStore(corpus_root).list()) == []
    assert CorpusStateStore(corpus_root).read().last_ingest_at is None
    assert not (corpus_root / "store" / "lightrag" / "custom_kg.json").exists()


def test_pipeline_preserves_existing_corpus_when_next_ingest_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    corpus_root = create_corpus("rollback-existing")
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    good.mkdir()
    bad.mkdir()
    (good / "good.md").write_text("# Good\nOpenClaw decided to use LightRAG.\n", encoding="utf-8")
    (bad / "bad.md").write_text("# Bad\nThis document triggers a failing local LLM call.\n", encoding="utf-8")

    MemoryPipeline().ingest("rollback-existing", good, mode="llm", llm_client=FakeClient())
    before_state = CorpusStateStore(corpus_root).read()
    before_docs = [doc.source_id for doc in BronzeStore(corpus_root).list()]

    try:
        MemoryPipeline().ingest("rollback-existing", bad, mode="llm", llm_client=FailingClient())
    except LlmClientError:
        pass
    else:
        raise AssertionError("expected LlmClientError")

    after_state = CorpusStateStore(corpus_root).read()
    after_docs = [doc.source_id for doc in BronzeStore(corpus_root).list()]
    assert after_state == before_state
    assert after_docs == before_docs == ["good.md"]
