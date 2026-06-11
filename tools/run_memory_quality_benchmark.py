from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ame.bronze.store import BronzeStore
from ame.core.corpus import create_corpus, require_corpus
from ame.gold.schema import GoldEdge
from ame.gold.store import GoldStore
from ame.pipeline import MemoryPipeline
from ame.query.engine import QueryEngine
from ame.silver.schema import SilverRationale
from ame.silver.store import SilverStore


DEFAULT_BENCHMARK = ROOT / "benchmark" / "adaptive_memory_engine_memory_quality_benchmark_v1.md"
DEFAULT_PRD = ROOT / "adaptive_memory_engine_prd_v2_2_integrated.md"
DEFAULT_MEMORY_MINI = ROOT / "tests" / "fixtures" / "memory-mini" / "docs"
DEFAULT_OUT = ROOT / "tests" / "out" / "memory-quality-v1"


TRIPLE_PRECISION_TARGET = 0.95
TRIPLE_RECALL_TARGET = 0.90
GROUNDING_ERROR_TARGET = 0.01
RATIONALE_RECALL_TARGET = 0.85
DECISION_CHAIN_TARGET = 0.90


FORBIDDEN_TRIPLES = [
    ("Adaptive Memory Engine", "USES", "Pinecone"),
    ("Adaptive Memory Engine", "USES", "Weaviate"),
    ("Adaptive Memory Engine", "USES", "Neo4j"),
    ("Adaptive Memory Engine", "IS_PRODUCT_OF", "OpenAI"),
    ("GraphRAG", "IS_CURRENT_CORE_OF", "Adaptive Memory Engine"),
    ("Slack Connector", "IS_INCLUDED_IN", "MVP"),
    ("Cloud Sync", "IS_INCLUDED_IN", "MVP"),
]


PRECISION_PROBES = [
    ("TP-001", "Adaptive Memory Engine", ["USES", "ADOPTS", "SELECTS"], "LightRAG"),
    ("TP-002", "LightRAG 도입 결정", ["SUPERSEDES"], "GraphRAG 직접 구현 검토"),
    ("TP-003", "Gold Layer", ["PRODUCES", "CREATES", "GENERATES"], "Timeline"),
    ("TP-004", "Gold Layer", ["PRODUCES", "CREATES", "GENERATES"], "Knowledge Graph"),
    ("TP-005", "OpenClaw", ["USES"], "Adaptive Memory Engine"),
    ("TP-006", "Hermes", ["USES"], "Adaptive Memory Engine"),
    ("TP-007", "Hardware Adaptive", ["SELECTS_MODEL_BY"], "RAM Tier"),
    ("TP-008", "Validation Gate", ["VALIDATES"], "Grounding"),
    ("TP-009", "Validation Gate", ["VALIDATES"], "Type Gate"),
    ("TP-010", "Obsidian Layer", ["EXPORTS"], "Markdown Vault"),
]


RECALL_GROUPS = {
    "core_architecture": {
        "minimum": 9,
        "triples": [
            ("Adaptive Memory Engine", ["HAS_LAYER"], "Bronze"),
            ("Adaptive Memory Engine", ["HAS_LAYER"], "Silver"),
            ("Adaptive Memory Engine", ["HAS_LAYER"], "Gold"),
            ("Bronze Layer", ["STORES"], "Raw Data"),
            ("Silver Layer", ["EXTRACTS"], "Entity"),
            ("Silver Layer", ["EXTRACTS"], "Relation"),
            ("Silver Layer", ["EXTRACTS"], "Decision"),
            ("Gold Layer", ["PRODUCES"], "Knowledge Graph"),
            ("Gold Layer", ["PRODUCES"], "Timeline"),
            ("Gold Layer", ["PRODUCES"], "Supersession Index"),
        ],
    },
    "rag_core_decision": {
        "minimum": 5,
        "triples": [
            ("GraphRAG 직접 구현 검토", ["STATUS"], "Superseded"),
            ("LightRAG 도입 결정", ["STATUS"], "Accepted"),
            ("LightRAG 도입 결정", ["SUPERSEDES"], "GraphRAG 직접 구현 검토"),
            ("Adaptive Memory Engine", ["USES"], "LightRAG"),
            ("LightRAG", ["ROLE"], "Storage/Retrieval Core"),
        ],
    },
    "storage_policy": {
        "minimum": 4,
        "triples": [
            ("Gold 데이터를 자체 JSON 파일에만 저장", ["STATUS"], "Superseded"),
            ("Gold 데이터를 LightRAG custom_kg로 주입", ["STATUS"], "Accepted"),
            ("Gold 데이터를 LightRAG custom_kg로 주입", ["SUPERSEDES"], "Gold 데이터를 자체 JSON 파일에만 저장"),
            ("Gold Layer", ["EXPORTS_TO"], "LightRAG custom_kg"),
            ("LightRAG custom_kg", ["CONNECTS_TO"], "Memory API"),
        ],
    },
    "agent_integration": {
        "minimum": 7,
        "triples": [
            ("OpenClaw", ["USES"], "Memory API"),
            ("OpenClaw", ["USES"], "Adaptive Memory Engine"),
            ("Hermes", ["USES"], "Adaptive Memory Engine"),
            ("Hermes", ["REQUIRES"], "Personal Memory"),
            ("Agent", ["CALLS"], "memory.search"),
            ("Agent", ["CALLS"], "memory.timeline"),
            ("Agent", ["CALLS"], "memory.why"),
            ("Agent", ["CALLS"], "memory.diff"),
        ],
    },
}


GROUNDING_CASES = [
    {
        "id": "GER-001",
        "question": "현재 저장·검색 코어는 무엇인가?",
        "claims": [["LightRAG"], ["GraphRAG"], ["SUPERSEDES", "대체"]],
        "forbidden": [],
    },
    {
        "id": "GER-002",
        "question": "Adaptive Memory Engine은 Pinecone을 사용하지?",
        "claims": [["Pinecone", "존재하지"], ["LightRAG"]],
        "forbidden": [["Pinecone을 사용한다"], ["Pinecone is used"]],
    },
    {
        "id": "GER-003",
        "question": "왜 OpenClaw가 LightRAG를 사용하게 되었지?",
        "claims": [["GraphRAG"], ["16GB"], ["LightRAG"], ["OpenClaw"]],
        "forbidden": [],
    },
    {
        "id": "GER-004",
        "question": "Hermes에서 필요한 Personal Memory Type은?",
        "claims": [["Email"], ["Calendar"], ["Meeting"], ["Task"], ["Document"], ["Decision"], ["Contact"], ["Project"]],
        "forbidden": [],
    },
]


RATIONALE_CASES = [
    {
        "id": "RR-001",
        "decision": "LightRAG 도입 결정",
        "question": "왜 LightRAG를 채택했지?",
        "minimum": 4,
        "items": [[["16GB"]], [["검증", "OSS"]], [["GraphRAG", "구현", "범위"]], [["빠른", "MVP"]], [["저장", "검색", "추출", "검증"]]],
    },
    {
        "id": "RR-002",
        "decision": "Local First",
        "question": "Local First인 이유는?",
        "minimum": 4,
        "items": [[["개인", "데이터"]], [["회사", "데이터"]], [["프로젝트", "히스토리"]], [["클라우드", "기본", "저장"], ["클라우드", "기본", "아님"], ["클라우드", "기본", "않음"]], [["로컬"]]],
    },
    {
        "id": "RR-003",
        "decision": "Validation First",
        "question": "Validation First를 채택한 이유는?",
        "minimum": 4,
        "items": [[["환각"]], [["Grounding"], ["span"]], [["Type", "Gate"]], [["confidence"]], [["검증"]]],
    },
    {
        "id": "RR-004",
        "decision": "Obsidian Export 필요",
        "question": "Obsidian Export가 필요한 이유는?",
        "minimum": 3,
        "items": [[["Graph", "DB", "직접", "보지"]], [["Markdown", "노트"]], [["Gold", "Memory"]], [["Obsidian", "Vault"], ["Markdown", "Vault"]]],
    },
    {
        "id": "RR-005",
        "decision": "Slack Connector MVP 제외",
        "question": "Slack Connector가 MVP에서 제외된 이유는?",
        "minimum": 3,
        "items": [[["MVP"]], [["Memory", "Pipeline"]], [["Markdown", "Obsidian"]], [["Connector", "Expansion"], ["이후", "단계"]]],
    },
]


DECISION_CHAIN_CASES = [
    {
        "id": "DCA-001",
        "question": "RAG Core 선택은 어떻게 바뀌었지?",
        "steps": [[["GraphRAG", "검토"]], [["16GB", "구현", "범위"]], [["LightRAG", "도입", "결정"]], [["현재", "저장", "검색", "코어"]]],
    },
    {
        "id": "DCA-002",
        "question": "Gold 저장 정책은 어떻게 바뀌었지?",
        "steps": [[["JSON", "파일"]], [["LightRAG", "custom_kg"]], [["Gold", "JSON", "custom_kg", "변환"]], [["Memory", "API", "연결"]]],
    },
    {
        "id": "DCA-003",
        "question": "왜 OpenClaw가 Adaptive Memory Engine을 사용하게 되었지?",
        "steps": [[["OpenClaw", "장기", "기억"]], [["Adaptive", "Memory", "Engine", "Memory", "Layer"]], [["LightRAG", "저장", "검색", "코어"]], [["OpenClaw", "Agent", "Memory", "API"]]],
    },
    {
        "id": "DCA-004",
        "question": "Hermes가 Adaptive Memory Engine과 연결되는 이유는?",
        "steps": [[["Hermes", "Personal", "Memory", "OS"]], [["Email", "Calendar", "Meeting", "Task", "Document"]], [["Adaptive", "Memory", "Engine", "Personal", "Memory", "Layer"]], [["장기", "개인", "기억"]]],
    },
    {
        "id": "DCA-005",
        "question": "검증된 Memory는 어떤 과정을 거쳐 만들어지지?",
        "steps": [[["Raw", "Data", "저장"]], [["Bronze", "원본", "보존"]], [["Silver", "Entity", "Relation", "Decision"]], [["Validation", "Gate", "Grounding", "Type", "Confidence"]], [["Gold", "Knowledge", "Graph", "Timeline"]]],
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Memory Quality Benchmark v1.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--prd", type=Path, default=DEFAULT_PRD)
    parser.add_argument("--memory-mini", type=Path, default=DEFAULT_MEMORY_MINI)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--corpus-id", default="memory-quality-v1")
    args = parser.parse_args()

    payload = run_benchmark(args.benchmark, args.prd, args.memory_mini, args.out, args.corpus_id)
    output = args.out / "benchmark_results.json"
    history = args.out / "benchmark_history"
    snapshot = history / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    print(f"results: {output}")
    print(f"history: {snapshot}")
    for name, metric in payload["metrics"].items():
        print(f"{name}: {metric['score']} target={metric['target']} passed={metric['passed']}")
    print(f"overall: {payload['overall']['quality_grade']} passed={payload['overall']['passed']}")


def run_benchmark(benchmark: Path, prd: Path, memory_mini: Path, out: Path, corpus_id: str) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    home = out / "ame-home"
    source_dir = out / "source_docs"
    if home.exists():
        shutil.rmtree(home)
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True)

    shutil.copy2(prd, source_dir / prd.name)
    for source in sorted(memory_mini.glob("*.md")):
        shutil.copy2(source, source_dir / source.name)

    os.environ["AME_HOME"] = str(home)
    create_corpus(corpus_id)
    report = MemoryPipeline().ingest(corpus_id, source_dir, mode="deterministic")
    corpus_root = require_corpus(corpus_id)
    bronze = BronzeStore(corpus_root)
    gold = GoldStore(corpus_root)
    silver = SilverStore(corpus_root)
    engine = QueryEngine(bronze, gold)
    edges = gold.edges()
    rationales = silver.rationales()

    metrics = {
        "triple_precision": evaluate_triple_precision(edges),
        "triple_recall": evaluate_triple_recall(edges),
        "grounding_error_rate": evaluate_grounding_error_rate(engine),
        "rationale_recall": evaluate_rationale_recall(engine, rationales),
        "decision_chain_accuracy": evaluate_decision_chain_accuracy(engine),
    }
    passed_metrics = sum(1 for metric in metrics.values() if metric["passed"])
    all_passed = passed_metrics == len(metrics)
    grade = quality_grade(metrics, passed_metrics)
    payload = {
        "benchmark": "memory_quality_benchmark_v1",
        "benchmark_spec": str(benchmark),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "corpus_id": corpus_id,
        "source_docs": str(source_dir),
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
        "metrics": metrics,
        "overall": {"passed": all_passed, "quality_grade": grade, "passed_metrics": passed_metrics, "total_metrics": len(metrics)},
    }

    output = out / "benchmark_results.json"
    history = out / "benchmark_history"
    history.mkdir(parents=True, exist_ok=True)
    snapshot = history / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def evaluate_triple_precision(edges: list[GoldEdge]) -> dict[str, Any]:
    false_positive = [
        {"subject": subject, "predicate": predicate, "object": object_}
        for subject, predicate, object_ in FORBIDDEN_TRIPLES
        if has_edge(edges, subject, [predicate], object_)
    ]
    probes = [
        {"id": probe_id, "matched": has_edge(edges, subject, predicates, object_), "subject": subject, "predicates": predicates, "object": object_}
        for probe_id, subject, predicates, object_ in PRECISION_PROBES
    ]
    extracted_total = len(edges)
    fp_count = len(false_positive)
    true_positive = max(0, extracted_total - fp_count)
    score = ratio(true_positive, extracted_total)
    return {
        "score": score,
        "target": TRIPLE_PRECISION_TARGET,
        "passed": score >= TRIPLE_PRECISION_TARGET and all(probe["matched"] for probe in probes),
        "true_positive": true_positive,
        "false_positive": fp_count,
        "extracted_total": extracted_total,
        "forbidden_present": false_positive,
        "precision_probes": probes,
    }


def evaluate_triple_recall(edges: list[GoldEdge]) -> dict[str, Any]:
    details = {}
    true_positive = 0
    gold_total = 0
    for group_name, group in RECALL_GROUPS.items():
        triples = []
        matched = 0
        for subject, predicates, object_ in group["triples"]:
            found = has_edge(edges, subject, predicates, object_)
            triples.append({"subject": subject, "predicates": predicates, "object": object_, "matched": found})
            matched += int(found)
        total = len(group["triples"])
        true_positive += matched
        gold_total += total
        details[group_name] = {
            "matched": matched,
            "total": total,
            "minimum": group["minimum"],
            "passed": matched >= group["minimum"],
            "triples": triples,
        }
    score = ratio(true_positive, gold_total)
    return {
        "score": score,
        "target": TRIPLE_RECALL_TARGET,
        "passed": score >= TRIPLE_RECALL_TARGET and all(group["passed"] for group in details.values()),
        "true_positive": true_positive,
        "false_negative": gold_total - true_positive,
        "gold_total": gold_total,
        "groups": details,
    }


def evaluate_grounding_error_rate(engine: QueryEngine) -> dict[str, Any]:
    total_claims = 0
    unsupported = 0
    details = []
    for case in GROUNDING_CASES:
        result = engine.query(case["question"])
        text = result.answer
        missing = [claim for claim in case["claims"] if not contains_any_group(text, claim)]
        forbidden = [claim for claim in case["forbidden"] if contains_all(text, claim)]
        total_claims += len(case["claims"])
        unsupported += len(missing) + len(forbidden)
        details.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answer": result.answer,
                "missing_claims": missing,
                "forbidden_claims": forbidden,
                "sources": [source.model_dump() for source in result.sources],
                "raw": result.raw,
            }
        )
    score = ratio(unsupported, total_claims)
    return {
        "score": score,
        "target": GROUNDING_ERROR_TARGET,
        "passed": score <= GROUNDING_ERROR_TARGET,
        "unsupported_claims": unsupported,
        "total_claims": total_claims,
        "details": details,
    }


def evaluate_rationale_recall(engine: QueryEngine, rationales: list[SilverRationale]) -> dict[str, Any]:
    retrieved = 0
    expected = 0
    details = []
    for case in RATIONALE_CASES:
        result = engine.query(case["question"])
        structured = structured_rationale_text(rationales, case["decision"])
        combined_text = f"{structured}\n{result.answer}"
        matches = [item_present(combined_text, item) for item in case["items"]]
        item_count = sum(1 for matched in matches if matched)
        retrieved += item_count
        expected += len(case["items"])
        details.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answer": result.answer,
                "structured_rationale": structured,
                "retrieved": item_count,
                "expected": len(case["items"]),
                "minimum": case["minimum"],
                "passed": item_count >= case["minimum"],
                "item_matches": matches,
            }
        )
    score = ratio(retrieved, expected)
    return {
        "score": score,
        "target": RATIONALE_RECALL_TARGET,
        "passed": score >= RATIONALE_RECALL_TARGET and all(detail["passed"] for detail in details),
        "retrieved": retrieved,
        "expected": expected,
        "details": details,
    }


def structured_rationale_text(rationales: list[SilverRationale], decision_title: str) -> str:
    decision = normalize(decision_title)
    matched = [
        rationale
        for rationale in rationales
        if decision in normalize(rationale.decision_title) or normalize(rationale.decision_title) in decision
    ]
    return "\n".join(f"{rationale.rationale_text} ({rationale.category})" for rationale in matched)


def evaluate_decision_chain_accuracy(engine: QueryEngine) -> dict[str, Any]:
    correct = 0
    expected = 0
    details = []
    for case in DECISION_CHAIN_CASES:
        result = engine.query(case["question"])
        matches = [item_present(result.answer, step) for step in case["steps"]]
        step_count = sum(1 for matched in matches if matched)
        correct += step_count
        expected += len(case["steps"])
        details.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answer": result.answer,
                "correct_steps": step_count,
                "expected_steps": len(case["steps"]),
                "passed": step_count == len(case["steps"]),
                "step_matches": matches,
                "raw": result.raw,
            }
        )
    score = ratio(correct, expected)
    return {
        "score": score,
        "target": DECISION_CHAIN_TARGET,
        "passed": score >= DECISION_CHAIN_TARGET and all(detail["passed"] for detail in details),
        "correct_steps": correct,
        "expected_steps": expected,
        "details": details,
    }


def has_edge(edges: list[GoldEdge], subject: str, predicates: list[str], object_: str) -> bool:
    return any(
        contains_loose(edge.source, subject)
        and edge.relation in predicates
        and contains_loose(edge.target, object_)
        for edge in edges
    )


def contains_loose(value: str, expected: str) -> bool:
    normalized_value = normalize(value)
    normalized_expected = normalize(expected)
    return normalized_expected in normalized_value or normalized_value in normalized_expected


def item_present(text: str, alternatives: list[list[str]]) -> bool:
    return any(contains_all(text, tokens) for tokens in alternatives)


def contains_any_group(text: str, tokens: list[str]) -> bool:
    return any(contains_all(text, [token]) for token in tokens)


def contains_all(text: str, tokens: list[str]) -> bool:
    normalized_text = normalize(text)
    return all(normalize(token) in normalized_text for token in tokens)


def normalize(text: str) -> str:
    return re.sub(r"[\s_\-./·:()\"'`]+", "", text.casefold())


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else round(numerator / denominator, 4)


def quality_grade(metrics: dict[str, dict[str, Any]], passed_metrics: int) -> str:
    if all(metric["passed"] for metric in metrics.values()) and metrics["grounding_error_rate"]["score"] <= 0.005:
        return "A+"
    if all(metric["passed"] for metric in metrics.values()):
        return "A"
    if passed_metrics == 4:
        return "B"
    if passed_metrics == 3:
        return "C"
    return "Fail"


if __name__ == "__main__":
    main()
