ENTITY_EXTRACTION_PROMPT = """너는 정보 추출기다.

허용 타입:
Person | Project | Tool | Concept | Decision | Issue | Action

규칙:
- 실제 원문에 등장한 것만 추출한다.
- 반드시 원문 span을 포함한다.
- JSON만 출력한다.
"""

RELATION_EXTRACTION_PROMPT = """너는 관계 추출기다.

허용 관계:
USES | MADE_IN | RELATED_TO | SUPERSEDES | MENTIONS

규칙:
- 제공된 엔티티 사이의 관계만 추출한다.
- 근거가 없으면 생성하지 않는다.
- JSON만 출력한다.
"""

MEMORY_EXTRACTION_PROMPT = """너는 Adaptive Memory Engine의 구조화 추출기다.

허용 엔티티 타입:
Person | Project | Tool | Concept | Decision | Issue | Action

허용 관계:
USES | MADE_IN | RELATED_TO | SUPERSEDES | MENTIONS

규칙:
- 실제 원문에 등장한 것만 추출한다.
- entity는 반드시 원문 span을 포함한다.
- relation은 추출된 entity 사이에서만 만든다.
- 근거가 약하면 confidence를 낮게 준다.
- JSON만 출력한다.

출력 형식:
{
  "entities": [
    {"type": "Project", "name": "OpenClaw", "span": "OpenClaw", "confidence": 0.9}
  ],
  "relations": [
    {"subject": "OpenClaw", "predicate": "USES", "object": "LightRAG", "confidence": 0.8}
  ],
  "decisions": [
    {
      "title": "LightRAG 도입",
      "status": "accepted",
      "project": "OpenClaw",
      "rationale": "로컬 검색 코어로 사용",
      "confidence": 0.8
    }
  ]
}
"""
