from pathlib import Path

from ame.core.corpus import create_corpus
from ame.core.paths import ensure_runtime_layout
from ame.core.state import CorpusStateStore
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
