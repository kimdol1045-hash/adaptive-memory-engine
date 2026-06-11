from __future__ import annotations

from ame.context_budget import ContextBudgetOptimizer, ContextItem


def test_context_budget_optimizer_compresses_and_restores_locally() -> None:
    items = [
        ContextItem(
            source_id="decision-1",
            priority=0.9,
            content="\n".join(
                [
                    "Decision: Chronicle uses durable sync runner.",
                    "Rationale: provider workers need repeatable attempts.",
                    "Implementation details are intentionally verbose. " * 20,
                ]
            ),
            metadata={"provider": "google"},
        ),
        ContextItem(
            source_id="note-1",
            priority=0.1,
            content="Low priority background note. " * 30,
        ),
    ]

    result = ContextBudgetOptimizer().optimize(items, budget_chars=160)
    restored = ContextBudgetOptimizer().restore(result)

    assert result.optimized_chars <= 160
    assert result.items[0].source_id == "decision-1"
    assert result.items[0].compression == "extractive"
    assert "Decision: Chronicle uses durable sync runner." in result.items[0].content
    assert result.archive[result.items[0].original_hash] == items[0].content
    assert restored[0].content == items[0].content
    assert restored[0].metadata == {"provider": "google"}


def test_context_budget_optimizer_leaves_small_context_uncompressed() -> None:
    items = [ContextItem(source_id="small", content="Decision: keep the source intact.", priority=1.0)]

    result = ContextBudgetOptimizer().optimize(items, budget_chars=200)

    assert result.items[0].compression == "none"
    assert result.items[0].content == items[0].content
    assert result.archive == {}
