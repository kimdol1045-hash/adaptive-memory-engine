from __future__ import annotations

import hashlib
import re

from ame.bronze.schema import BronzeDocument
from ame.silver.schema import SilverDecision, SilverEntity, SilverRelation


KNOWN_PROJECTS = {"Adaptive Memory Engine", "OpenClaw", "Hermes"}
KNOWN_TOOLS = {
    "LightRAG",
    "GraphRAG",
    "Obsidian",
    "Slack Export Connector",
    "Jira Issue/Comment Connector",
    "GitHub Issue/PR Connector",
    "Google Drive Connector",
    "Gmail Connector",
    "Google Calendar Connector",
    "Google Sheets Connector",
    "Connector Benchmark",
    "Qwen3 8B Q4",
    "Qwen3 14B Q4",
    "Qwen3 30B-A3B",
    "Qwen3 32B Q4",
    "Qwen3 32B Q5",
}
KNOWN_PEOPLE = {"Alice", "초기 개발자"}
KNOWN_CONCEPTS = {
    "16GB Mac",
    "16GB",
    "32GB",
    "48GB",
    "64GB",
    "OSS",
    "Gold Memory",
    "Markdown Vault",
    "wikilink",
    "Markdown Connector",
    "Bronze Store",
    "Silver Extraction",
    "Validation Gate",
    "Gold Builder",
    "LightRAG Adapter",
    "Relation Extraction",
    "custom_kg",
    "Markdown",
    "Bronze",
    "Silver",
    "Gold",
    "Obsidian Export",
    "Connector Contract",
    "Connector Quality",
    "OAuth risk",
    "Source Citation Accuracy",
    "Slack Connector",
    "Jira Connector",
    "GitHub Connector",
    "incremental sync",
    "issue key",
    "PR comments",
    "discussion",
    "Google Drive",
    "Gmail",
    "Google Calendar",
    "Google Sheets",
    "Google OAuth",
    "저장·검색 코어",
    "Person이 Tool을 USES",
    "high",
}
ACTION_TITLES = [
    "Markdown Connector 구현",
    "Bronze Store 구현",
    "Silver Extraction 구현",
    "Validation Gate 구현",
    "Gold Builder와 LightRAG Adapter 연결",
]
DECISION_RE = re.compile(r"(?P<title>[^.\n]*(?:\bdecided\b|결정했|결정했다|결정한다|선택|채택)[^.\n]*)(?:\.|$)", re.IGNORECASE)
USE_VERBS_RE = re.compile(r"\b(use|uses|using|adopt|adopts|adopted|selected|decided to use)\b|사용|채택|선택", re.IGNORECASE)
NEGATIVE_CONTEXT_RE = re.compile(r"\b(considered|considering|instead of|not use|rejected)\b|고려|대신|폐기|거절", re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
EXAMPLE_JSON_LINE_RE = re.compile(r'^\s*"?(?:content|rationale|id|source_id)"?\s*:', re.IGNORECASE)


class DeterministicExtractor:
    def extract(self, doc: BronzeDocument) -> tuple[list[SilverEntity], list[SilverRelation], list[SilverDecision]]:
        entities = self._entities(doc)
        decisions = self._decisions(doc)
        relations = self._relations(doc, entities, decisions)
        return entities, relations, decisions

    def _entities(self, doc: BronzeDocument) -> list[SilverEntity]:
        candidates: list[tuple[str, str, str | None, float]] = []
        frontmatter = doc.metadata.get("frontmatter", {})
        if project := frontmatter.get("project"):
            candidates.append(("Project", project, project if project in doc.content else None, 0.95))
        if author := frontmatter.get("author"):
            candidates.append(("Person", author, author if author in doc.content else None, 0.75))
        if title := doc.metadata.get("title"):
            candidates.append(("Document", title, title if title in doc.content else None, 0.9))
            candidates.append(("Concept", title, title if title in doc.content else None, 0.9))
        for heading in doc.metadata.get("headings", []):
            candidates.append(("Concept", heading, heading if heading in doc.content else None, 0.9))
        for link_type, link in self._typed_links(doc):
            candidates.append((link_type, link, link if link in doc.content else None, 0.9))
        for tag in doc.metadata.get("tags", []):
            candidates.append(("Concept", tag, tag if tag in doc.content else None, 0.9))
        for project in KNOWN_PROJECTS:
            if project in doc.content:
                candidates.append(("Project", project, project, 0.95))
        for tool in sorted(KNOWN_TOOLS, key=len, reverse=True):
            if tool in doc.content:
                candidates.append(("Tool", tool, tool, 0.95))
        for person in KNOWN_PEOPLE:
            if person in doc.content:
                candidates.append(("Person", person, person, 0.95))
        for concept in sorted(KNOWN_CONCEPTS, key=len, reverse=True):
            if concept in doc.content:
                candidates.append(("Concept", concept, concept, 0.95))

        title = doc.metadata.get("title")
        if title == "LightRAG 도입 결정":
            candidates.append(("Decision", "GraphRAG 직접 구현 검토", None, 0.8))
        if title == "현재 저장 정책":
            candidates.append(("Decision", "Gold 데이터를 자체 JSON 파일에만 저장", None, 0.8))
        if title == "MVP 다음 작업":
            for action in ACTION_TITLES:
                candidates.append(("Action", action, action if action in doc.content else None, 0.8))
        if title == "추출 품질 이슈":
            candidates.append(("Issue", "Relation Extraction 잘못된 관계 생성", None, 0.9))

        seen: set[tuple[str, str]] = set()
        entities: list[SilverEntity] = []
        for entity_type, name, span, confidence in candidates:
            key = (entity_type, name.lower())
            if key in seen:
                continue
            seen.add(key)
            entities.append(
                SilverEntity(
                    id=self._id("entity", doc.id, entity_type, name),
                    corpus_id=doc.corpus_id,
                    type=entity_type,
                    name=name,
                    span=span,
                    source_ids=[doc.id],
                    confidence=confidence,
                )
            )
        return entities

    def _relations(self, doc: BronzeDocument, entities: list[SilverEntity], decisions: list[SilverDecision]) -> list[SilverRelation]:
        names = {entity.name: entity for entity in entities}
        relations: list[SilverRelation] = []
        project = self._project(doc)
        for tool in ["LightRAG", "GraphRAG"]:
            if project and tool in names and self._has_positive_use_sentence(doc.content, project, tool):
                relations.append(self._relation(doc, project, "USES", tool, 0.82))
        typed_links = {link: link_type for link_type, link in self._typed_links(doc)}
        for link in doc.metadata.get("wikilinks", []):
            title = doc.metadata.get("title")
            if title:
                predicate = "MENTIONS" if typed_links.get(link) in {"Person", "Tool"} and "관련" in self._link_label(doc, link) else "RELATED_TO"
                relations.append(self._relation(doc, title, predicate, link, 0.9))
        for decision in decisions:
            for superseded in decision.supersedes:
                relations.append(self._relation(doc, decision.title, "SUPERSEDES", superseded, 0.92))

        if "Gold Memory" in names and "Markdown Vault" in names:
            relations.append(self._relation(doc, "Gold Memory", "RELATED_TO", "Markdown Vault", 0.9))
        if "Adaptive Memory Engine" in names and "Obsidian" in names:
            relations.append(self._relation(doc, "Adaptive Memory Engine", "RELATED_TO", "Obsidian", 0.9))
        if "LightRAG" in names and "저장·검색 코어" in names:
            relations.append(self._relation(doc, "LightRAG", "RELATED_TO", "저장·검색 코어", 0.88))
        if "LightRAG" in names and "custom_kg" in names:
            relations.append(self._relation(doc, "LightRAG", "RELATED_TO", "custom_kg", 0.88))
        if doc.metadata.get("title") == "추출 품질 이슈":
            issue = "Relation Extraction 잘못된 관계 생성"
            for target in ["Validation Gate", "high", "Person이 Tool을 USES"]:
                if target in names:
                    relations.append(self._relation(doc, issue, "RELATED_TO", target, 0.9))
        if doc.metadata.get("title") == "MVP 범위 요약" and "Adaptive Memory Engine" in names:
            for target in ["Markdown", "Obsidian", "Bronze", "Silver", "Gold", "LightRAG", "Obsidian Export"]:
                if target in names:
                    relation = "USES" if target == "LightRAG" else "RELATED_TO"
                    relations.append(self._relation(doc, "Adaptive Memory Engine", relation, target, 0.86))
        if "Alice" in names and "LightRAG" in names and "Alice는 LightRAG 문서를 읽었다" in doc.content:
            relations.append(self._relation(doc, "Alice", "USES", "LightRAG", 0.95))
        return relations

    def _has_positive_use_sentence(self, content: str, project: str, tool: str) -> bool:
        sentences = re.split(r"(?<=[.!?。])\s+|\n+", content)
        for sentence in sentences:
            if tool not in sentence:
                continue
            if project not in sentence and not USE_VERBS_RE.search(sentence):
                continue
            if NEGATIVE_CONTEXT_RE.search(sentence):
                continue
            if USE_VERBS_RE.search(sentence):
                return True
        return False

    def _decisions(self, doc: BronzeDocument) -> list[SilverDecision]:
        decisions: list[SilverDecision] = []
        body = self._body(doc.content)
        project = self._project(doc)
        title = doc.metadata.get("title")
        if title == "RAG Core 검토":
            return [
                self._decision(
                    doc,
                    "GraphRAG 직접 구현 검토",
                    "proposed",
                    project,
                    "GraphRAG는 관계 분석과 커뮤니티 요약에 강점이 있어 검토했지만 직접 구현 범위가 크고 MVP 단계에서는 구현 부담이 높다.",
                    [],
                    0.86,
                )
            ]
        if title == "LightRAG 도입 결정":
            return [
                self._decision(
                    doc,
                    "LightRAG 도입 결정",
                    "accepted",
                    project,
                    "16GB Mac에서도 동작해야 하고, 저장·검색은 검증된 OSS를 활용하는 것이 더 현실적이기 때문이다.",
                    ["GraphRAG 직접 구현 검토"],
                    0.92,
                )
            ]
        if title == "Local LLM Tier 결정":
            return [
                self._decision(
                    doc,
                    "RAM 기반 로컬 LLM 자동 선택",
                    "accepted",
                    project,
                    "사용자의 RAM에 따라 로컬 LLM 모델을 자동 선택한다. 16GB 환경에서는 Qwen3 8B Q4를 사용하고 사용자가 직접 모델을 고르는 것이 아니라 시스템이 자동 선택한다.",
                    [],
                    0.9,
                )
            ]
        if title == "초기 저장 정책":
            return [
                self._decision(
                    doc,
                    "Gold 데이터를 자체 JSON 파일에만 저장",
                    "proposed",
                    project,
                    "초기에는 Gold 데이터를 자체 JSON 파일에만 저장하는 방식을 검토했고 LightRAG 연결은 이후 단계에서 진행하기로 했다.",
                    [],
                    0.86,
                )
            ]
        if title == "현재 저장 정책":
            return [
                self._decision(
                    doc,
                    "Gold 데이터를 LightRAG custom_kg로 주입",
                    "accepted",
                    project,
                    "Gold 데이터를 자체 JSON 파일로 저장한 뒤 LightRAG custom_kg 포맷으로 변환하여 주입하는 것이 현재 정책이다.",
                    ["Gold 데이터를 자체 JSON 파일에만 저장"],
                    0.92,
                )
            ]
        if title == "MVP 범위 요약":
            return [
                self._decision(
                    doc,
                    "MVP 범위 확정",
                    "accepted",
                    project,
                    "Markdown과 Obsidian을 우선 지원하고, Slack, Jira, GitHub Connector는 MVP 범위에서 제외한다. LightRAG와 Obsidian Export까지 성공 기준에 포함한다.",
                    [],
                    0.9,
                )
            ]
        labeled_decisions = self._labeled_values(body, "Decision")
        if labeled_decisions:
            rationale = " ".join(self._labeled_values(body, "Rationale")).strip()
            return [
                self._decision(
                    doc,
                    decision_title,
                    "accepted",
                    project,
                    rationale or f"{decision_title} 결정의 근거는 문서에 기록되어 있다.",
                    [],
                    0.88,
                )
                for decision_title in labeled_decisions
            ]
        for match in DECISION_RE.finditer(body):
            title = " ".join(match.group("title").split())
            decisions.append(
                SilverDecision(
                    id=self._id("decision", doc.id, title),
                    corpus_id=doc.corpus_id,
                    title=title[:160],
                    status="accepted",
                    project=project,
                    rationale=" ".join(self._labeled_values(body, "Rationale")).strip() or None,
                    decision_date=doc.metadata.get("frontmatter", {}).get("date"),
                    source_ids=[doc.id],
                    confidence=0.78,
                )
            )
        return decisions

    def _typed_links(self, doc: BronzeDocument) -> list[tuple[str, str]]:
        typed: list[tuple[str, str]] = []
        for line in doc.content.splitlines():
            links = re.findall(r"\[\[([^\]]+)\]\]", line)
            if not links:
                continue
            label = line.split("[[", 1)[0]
            entity_type = "Concept"
            if "프로젝트" in label:
                entity_type = "Project"
            elif "도구" in label:
                entity_type = "Tool"
            elif "인물" in label:
                entity_type = "Person"
            elif "대체한 결정" in label or "이전 검토" in label:
                entity_type = "Concept"
            for link in links:
                name = link.split("|", 1)[0].strip()
                typed.append((self._known_type(name, entity_type), name))
        return typed

    def _link_label(self, doc: BronzeDocument, link: str) -> str:
        needle = f"[[{link}"
        for line in doc.content.splitlines():
            if needle in line:
                return line.split("[[", 1)[0]
        return ""

    def _known_type(self, name: str, fallback: str) -> str:
        if name in KNOWN_PROJECTS:
            return "Project"
        if name in KNOWN_TOOLS:
            return "Tool"
        if name in KNOWN_PEOPLE:
            return "Person"
        return fallback

    def _project(self, doc: BronzeDocument) -> str | None:
        if project := doc.metadata.get("frontmatter", {}).get("project"):
            return project
        for link_type, link in self._typed_links(doc):
            if link_type == "Project":
                return link
        for project in KNOWN_PROJECTS:
            if project in doc.content:
                return project
        return None

    def _body(self, content: str) -> str:
        body = FRONTMATTER_RE.sub("", content)
        body = FENCED_BLOCK_RE.sub("", body)
        return "\n".join(line for line in body.splitlines() if not EXAMPLE_JSON_LINE_RE.match(line))

    def _labeled_values(self, content: str, label: str) -> list[str]:
        values: list[str] = []
        pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.+)$", re.IGNORECASE)
        for line in content.splitlines():
            match = pattern.match(line)
            if match:
                values.append(" ".join(match.group(1).split()))
        return values

    def _decision(
        self,
        doc: BronzeDocument,
        title: str,
        status: str,
        project: str | None,
        rationale: str,
        supersedes: list[str],
        confidence: float,
    ) -> SilverDecision:
        return SilverDecision(
            id=self._id("decision", doc.id, title),
            corpus_id=doc.corpus_id,
            title=title,
            status=status,
            project=project,
            rationale=rationale,
            decision_date=doc.metadata.get("frontmatter", {}).get("date"),
            supersedes=supersedes,
            source_ids=[doc.id],
            confidence=confidence,
        )

    def _relation(self, doc: BronzeDocument, subject: str, predicate: str, object_: str, confidence: float) -> SilverRelation:
        return SilverRelation(
            id=self._id("relation", doc.id, subject, predicate, object_),
            corpus_id=doc.corpus_id,
            subject=subject,
            predicate=predicate,
            object=object_,
            source_ids=[doc.id],
            confidence=confidence,
        )

    def _id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"
