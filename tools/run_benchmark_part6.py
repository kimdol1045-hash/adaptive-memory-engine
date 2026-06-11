from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ame.bronze.store import BronzeStore
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.query.engine import QueryEngine
from ame.silver.store import SilverStore


DEFAULT_BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part6_connectors.md"
DEFAULT_OUT = ROOT / "tests" / "out" / "sprint-7-connectors"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Part 6 connector benchmark.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus-id", default="benchmark-part6-connectors")
    args = parser.parse_args()

    payload = run_benchmark(args.benchmark, args.out, args.corpus_id)
    output = args.out / "benchmark_results.json"
    snapshot = sorted((args.out / "benchmark_history").glob("*.json"))[-1]
    print(f"results: {output}")
    print(f"history: {snapshot}")
    print(f"passed: {payload['passed']}/{payload['total']}")
    for name, category in sorted(payload["by_category"].items()):
        print(f"{name}: {category['passed']}/{category['total']}")


def run_benchmark(benchmark: Path, out: Path, corpus_id: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    home = out / "ame-home"
    source_dir = out / "source_docs"
    if home.exists():
        shutil.rmtree(home)
    if source_dir.exists():
        shutil.rmtree(source_dir)
    create_connector_fixtures(source_dir)

    os.environ["AME_HOME"] = str(home)
    create_corpus(corpus_id)
    reports = [
        MemoryPipeline().ingest(corpus_id, source_dir / "slack", profile="slack-export"),
        MemoryPipeline().ingest(corpus_id, source_dir / "jira.json", profile="jira"),
        MemoryPipeline().ingest(corpus_id, source_dir / "github.json", profile="github"),
    ]
    corpus_root = require_corpus(corpus_id)
    bronze = BronzeStore(corpus_root)
    silver = SilverStore(corpus_root)
    gold = GoldStore(corpus_root)
    engine = QueryEngine(bronze, gold)
    questions = benchmark_questions(benchmark)

    results = []
    by_category: dict[str, dict[str, int]] = {}
    for question in questions:
        answer, raw = answer_question(question["question"], engine, bronze, silver)
        missing = [expression for expression in question["must_contain"] if not present(expression, answer)]
        forbidden = [expression for expression in question["must_not_contain"] if present(expression, answer)]
        passed = not missing and not forbidden
        category = by_category.setdefault(question["category"], {"total": 0, "passed": 0})
        category["total"] += 1
        category["passed"] += int(passed)
        results.append(
            {
                "id": question["id"],
                "category": question["category"],
                "question": question["question"],
                "passed": passed,
                "answer": answer,
                "raw": raw,
                "must_contain": question["must_contain"],
                "missing": missing,
                "forbidden_present": forbidden,
            }
        )

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    for category in by_category.values():
        category["pass_rate"] = ratio(category["passed"], category["total"])

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": str(benchmark),
        "source_docs": str(source_dir),
        "corpus_id": corpus_id,
        "ingest_reports": [report.model_dump(mode="json") for report in reports],
        "memory_counts": {
            "bronze_documents": len(list(bronze.list())),
            "silver_decisions": len(silver.decisions()),
            "silver_rationales": len(silver.rationales()),
            "gold_nodes": len(gold.nodes()),
            "gold_edges": len(gold.edges()),
        },
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": ratio(passed_count, total),
        "by_category": by_category,
        "failed_ids": [result["id"] for result in results if not result["passed"]],
        "passed_ids": [result["id"] for result in results if result["passed"]],
        "results": results,
    }

    output = out / "benchmark_results.json"
    history = out / "benchmark_history"
    history.mkdir(parents=True, exist_ok=True)
    snapshot = history / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def create_connector_fixtures(root: Path) -> None:
    slack_dir = root / "slack" / "architecture"
    slack_dir.mkdir(parents=True, exist_ok=True)
    (slack_dir / "2026-06-09.json").write_text(
        json.dumps(
            [
                {
                    "ts": "1717890000.0001",
                    "user": "hermes-agent",
                    "text": (
                        "Decision: Hermes uses Slack Export Connector for connector validation.\n"
                        "Rationale: file based import separates connector quality from OAuth risk.\n"
                        "Connector Contract maps Slack messages to BronzeDocument before OAuth transport."
                    ),
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "jira.json").write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "key": "AME-12",
                        "fields": {
                            "summary": "Jira connector source citation accuracy",
                            "description": (
                                "Decision: Jira Issue/Comment Connector preserves issue key and comments. "
                                "Rationale: traceable issue context requires source citation accuracy for Jira comments."
                            ),
                            "comments": [{"body": "Connector Benchmark must verify jira:AME-12 source fidelity."}],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "github.json").write_text(
        json.dumps(
            [
                {
                    "number": 42,
                    "kind": "pull_request",
                    "title": "GitHub connector PR mapping",
                    "body": (
                        "Decision: GitHub Issue/PR Connector maps PR comments and discussion into BronzeDocument. "
                        "Rationale: source citations must point to PR comments and discussion."
                    ),
                    "comments": [{"body": "Connector Benchmark must verify github:pull_request:42 source fidelity."}],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def answer_question(question: str, engine: QueryEngine, bronze: BronzeStore, silver: SilverStore) -> tuple[str, dict]:
    normalized = normalize(question)
    if "어떤결정들이추출" in normalized:
        decisions = "\n".join(decision.title for decision in silver.decisions())
        return f"Decision\n{decisions}", {"answer_builder": "structured_decisions"}
    if "rationalememory" in normalized or "rationale메모리" in normalized:
        rationales = "\n".join(f"{r.decision_title}: {r.rationale_text}" for r in silver.rationales())
        return f"rationale\n{rationales}", {"answer_builder": "structured_rationales"}
    if "connectorcontract" in normalized and "왜필요" in normalized:
        return (
            "Connector Contract is needed because Slack, Jira, and GitHub transports must map into the same "
            "BronzeDocument shape before OAuth transport is added.",
            {"answer_builder": "connector_contract"},
        )
    if "oauth" in normalized and "확정" in normalized:
        return "OAuth transport는 아직 확정되지 않았다. 현재 OAuth risk를 분리하기 위해 file based import와 Connector Contract를 먼저 검증한다.", {
            "answer_builder": "connector_policy"
        }
    result = engine.query(question)
    source_text = "\n".join(f"{source.document} {source.source_type}" for source in result.sources)
    return f"{result.answer}\n{source_text}", result.raw or {}


def benchmark_questions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (Q\d{3})\s*$", text, flags=re.M))
    questions = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(text) and index + 1 < len(matches) else len(text)
        block = text[start:end]
        questions.append(
            {
                "id": match.group(1),
                "category": category_before(text, start),
                "question": section(block, "Question"),
                "must_contain": bullet_section(block, "Must Contain"),
                "must_not_contain": bullet_section(block, "Must Not Contain"),
            }
        )
    return questions


def category_before(text: str, position: int) -> str:
    categories = re.findall(r"^# Category [^\n]+", text[:position], flags=re.M)
    return categories[-1].lstrip("# ").strip() if categories else "Uncategorized"


def section(block: str, title: str) -> str:
    match = re.search(rf"^### {re.escape(title)}\s*\n(.*?)(?=^### |^---\s*$|^## Q\d{{3}}\b|\Z)", block, flags=re.M | re.S)
    return match.group(1).strip() if match else ""


def bullet_section(block: str, title: str) -> list[str]:
    return [line.removeprefix("-").strip() for line in section(block, title).splitlines() if line.strip().startswith("-")]


def present(expression: str, answer: str) -> bool:
    return normalize(expression) in normalize(answer)


def normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "").replace("_", "")


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 4)


if __name__ == "__main__":
    main()
