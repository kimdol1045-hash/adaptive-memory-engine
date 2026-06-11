from pathlib import Path

from ame.agent.memory_api import AgentMemoryAPI
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ensure_runtime_layout
from ame.hermes.memory import HermesMemoryStore


def test_generic_agent_writeback_records_decision_and_rationale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("agent")
    api = AgentMemoryAPI(require_corpus("agent"))

    write = api.write_decision("Hermes Memory Write-back 채택", "Hermes가 새 결정을 장기 기억에 저장해야 하기 때문이다.", project="Hermes")
    why = api.why("Hermes Memory Write-back")
    timeline = api.timeline("Hermes")

    assert write.ingested is True
    assert "Hermes Memory Write-back 채택" in why.answer
    assert "Hermes Memory Write-back 채택" in timeline.answer


def test_hermes_personal_memory_types_recall_and_next_actions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("hermes")
    store = HermesMemoryStore("hermes")

    store.write("Project", "AME", "Adaptive Memory Engine 작업", tags=["ame"])
    store.write("Decision", "Slack export 먼저", "OAuth 전에 export connector를 검증하기로 결정", tags=["connector"])
    store.write("Task", "이번 주 우선순위", "Next priority is Jira connector.", tags=["priority"])

    assert len(store.recall_project("AME").memories) == 1
    assert len(store.recall_decisions("Slack").memories) == 1
    assert store.recall_next_actions().memories[0].type == "Task"
