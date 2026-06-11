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


DEFAULT_BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_benchmark_part3_negative_hallucination.md"
DEFAULT_PRD = ROOT / "adaptive_memory_engine_prd_v2_2_integrated.md"
DEFAULT_MEMORY_MINI = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"
DEFAULT_OUT = ROOT / "tests" / "out" / "sprint-3"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Part 3 Negative/Hallucination benchmark.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--prd", type=Path, default=DEFAULT_PRD)
    parser.add_argument("--memory-mini", type=Path, default=DEFAULT_MEMORY_MINI)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus-id", default="benchmark-part3")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    home = args.out / "ame-home"
    source_dir = args.out / "source_docs"
    if home.exists():
        shutil.rmtree(home)
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)

    shutil.copy2(args.prd, source_dir / args.prd.name)
    for source in sorted(args.memory_mini.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    os.environ["AME_HOME"] = str(home)
    create_corpus(args.corpus_id)
    report = MemoryPipeline().ingest(args.corpus_id, source_dir, mode="deterministic")
    corpus_root = require_corpus(args.corpus_id)
    engine = QueryEngine(BronzeStore(corpus_root), GoldStore(corpus_root))
    questions = benchmark_questions(args.benchmark)

    results = []
    by_category: dict[str, dict[str, int]] = {}
    for question in questions:
        result = engine.query(question["question"])
        answer_text = answer_with_sources(result.answer, result.sources)
        missing = [expression for expression in question["expected"] if not present(expression, answer_text)]
        passed = not missing
        category = by_category.setdefault(question["category"], {"total": 0, "passed": 0})
        category["total"] += 1
        if passed:
            category["passed"] += 1
        results.append(
            {
                "id": question["id"],
                "category": question["category"],
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
                "expected": question["expected"],
                "missing": missing,
            }
        )

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    for category in by_category.values():
        category["pass_rate"] = ratio(category["passed"], category["total"])

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": str(args.benchmark),
        "source_docs": str(source_dir),
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
    for name, category in sorted(by_category.items()):
        print(f"{name}: {category['passed']}/{category['total']}")


def benchmark_questions(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## (Q\d{3})\s*$", text, flags=re.M))
    questions = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end]
        questions.append(
            {
                "id": match.group(1),
                "category": category_before(text, start),
                "question": inline_value(block, "Question"),
                "expected": expected_lines(block),
            }
        )
    return questions


def category_before(text: str, position: int) -> str:
    categories = re.findall(r"^# Category [^\n]+", text[:position], flags=re.M)
    if not categories:
        return "Uncategorized"
    return categories[-1].lstrip("# ").strip()


def inline_value(block: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", block, flags=re.M)
    return match.group(1).strip() if match else ""


def expected_lines(block: str) -> list[str]:
    match = re.search(r"^Expected Answer:\s*\n(.*?)(?=^## Q\d{3}\b|^# Category |^# Success Criteria|\Z)", block, flags=re.M | re.S)
    if not match:
        return []
    return [line.strip() for line in match.group(1).splitlines() if line.strip() and line.strip() != "---"]


def answer_with_sources(answer: str, sources: list[object]) -> str:
    source_text = "\n".join(getattr(source, "document", "") for source in sources)
    return f"{answer}\n{source_text}"


def present(expression: str, answer: str) -> bool:
    return normalize(expression) in normalize(answer)


def normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("\u00a0", "")


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 4)


if __name__ == "__main__":
    main()
