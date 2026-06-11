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


DEFAULT_BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part1_v4_2_scoring_friendly.md"
DEFAULT_SOURCE = ROOT / "adaptive_memory_engine_prd_v2_2_integrated.md"
DEFAULT_OUT = ROOT / "tests" / "out" / "sprint-1-5"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scoring-friendly Part 1 benchmark against local AME memory.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus-id", default="benchmark-part1")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    home = args.out / "ame-home"
    if home.exists():
        shutil.rmtree(home)
    os.environ["AME_HOME"] = str(home)

    create_corpus(args.corpus_id)
    report = MemoryPipeline().ingest(args.corpus_id, args.source, mode="deterministic")
    corpus_root = require_corpus(args.corpus_id)
    engine = QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root))
    questions = benchmark_questions(args.benchmark)

    results = []
    weighted_total = 0
    weighted_passed = 0
    by_category: dict[str, dict[str, int]] = {}

    for question in questions:
        result = engine.query(question["question"])
        answer_text = answer_with_sources(result.answer, result.sources)
        passed = passes_groups(answer_text, question["groups"])
        weight = question["weight"]
        weighted_total += weight
        if passed:
            weighted_passed += weight
        category = by_category.setdefault(
            question["category"],
            {"total": 0, "passed": 0, "weighted_total": 0, "weighted_passed": 0},
        )
        category["total"] += 1
        category["weighted_total"] += weight
        if passed:
            category["passed"] += 1
            category["weighted_passed"] += weight
        results.append(
            {
                "id": question["id"],
                "category": question["category"],
                "difficulty": question["difficulty"],
                "weight": weight,
                "question": question["question"],
                "passed": passed,
                "answer": result.answer,
                "sources": [
                    {
                        "source_id": source.source_id,
                        "document": source.document,
                        "source_type": source.source_type,
                        "metadata": source.metadata,
                    }
                    for source in result.sources
                ],
                "missing_groups": missing_groups(answer_text, question["groups"]),
            }
        )

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    for category in by_category.values():
        category["pass_rate"] = ratio(category["passed"], category["total"])
        category["weighted_pass_rate"] = ratio(category["weighted_passed"], category["weighted_total"])

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": str(args.benchmark),
        "source": str(args.source),
        "corpus_id": args.corpus_id,
        "ingest_report": {
            "documents": report.documents,
            "silver_entities": report.silver_entities,
            "silver_relations": report.silver_relations,
            "silver_decisions": report.silver_decisions,
            "silver_rationales": report.silver_rationales,
            "rejected": report.rejected,
            "gold_nodes": report.gold_nodes,
            "gold_edges": report.gold_edges,
        },
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": ratio(passed_count, total),
        "weighted_total": weighted_total,
        "weighted_passed": weighted_passed,
        "weighted_pass_rate": ratio(weighted_passed, weighted_total),
        "by_category": by_category,
        "failed_ids": [result["id"] for result in results if not result["passed"]],
        "passed_ids": [result["id"] for result in results if result["passed"]],
        "results": results,
    }

    output = args.out / "benchmark_results.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    history = args.out / "benchmark_history"
    history.mkdir(parents=True, exist_ok=True)
    snapshot = history / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"results: {output}")
    print(f"history: {snapshot}")
    print(f"passed: {passed_count}/{total}")
    print(f"weighted: {weighted_passed}/{weighted_total}")
    for name, category in sorted(by_category.items()):
        print(
            f"{name}: {category['passed']}/{category['total']} "
            f"weighted {category['weighted_passed']}/{category['weighted_total']}"
        )


def benchmark_questions(path: Path) -> list[dict]:
    blocks = re.split(r"(?=^## Q\d{3}\b)", path.read_text(encoding="utf-8"), flags=re.M)
    questions = []
    for block in blocks:
        header = re.match(r"^## (Q\d{3})\s*$", block, flags=re.M)
        if not header:
            continue
        questions.append(
            {
                "id": header.group(1),
                "category": section(block, "Category"),
                "difficulty": section(block, "Difficulty"),
                "weight": int(section(block, "Weight") or "0"),
                "question": section(block, "Question"),
                "groups": groups(block),
            }
        )
    return questions


def section(block: str, title: str) -> str:
    match = re.search(rf"^### {re.escape(title)}\s*\n(.*?)(?=^### |^---\s*$|^## Q\d{{3}}\b|\Z)", block, flags=re.M | re.S)
    if not match:
        return ""
    return match.group(1).strip()


def groups(block: str) -> list[list[str]]:
    parsed = []
    for line in section(block, "Must Contain Groups").splitlines():
        match = re.match(r"\s*-\s*Group\s+\d+:\s*(.+)$", line.strip())
        if match:
            parsed.append([part.strip() for part in match.group(1).split("|") if part.strip()])
    return parsed


def answer_with_sources(answer: str, sources: list[object]) -> str:
    source_text = "\n".join(getattr(source, "document", "") for source in sources)
    return f"{answer}\n{source_text}"


def passes_groups(answer: str, groups_: list[list[str]]) -> bool:
    return all(any(present(expression, answer) for expression in group) for group in groups_)


def missing_groups(answer: str, groups_: list[list[str]]) -> list[list[str]]:
    return [group for group in groups_ if not any(present(expression, answer) for expression in group)]


def present(expression: str, answer: str) -> bool:
    expr = normalize(expression)
    normalized_answer = normalize(answer)
    if expr in normalized_answer:
        return True
    synonyms = {
        "저장·검색": ["저장검색", "storage/retrieval", "storageandretrieval"],
        "그래프db": ["그래프데이터베이스", "graphdb"],
        "3계층": ["bronzesilvergold", "bronze/silver/gold", "bronze→silver→gold"],
        "memorypipeline": ["3계층memorypipeline", "bronze/silver/gold", "bronze→silver→gold"],
    }
    return any(normalize(alias) in normalized_answer for alias in synonyms.get(expr, []))


def normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 4)


if __name__ == "__main__":
    main()
