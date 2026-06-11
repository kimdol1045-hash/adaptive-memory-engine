# Product User Flow

이 문서는 Adaptive Memory Engine을 CLI로 배포했을 때 사용자가 실제로 경험해야 하는 흐름을 정리합니다.

목표는 사용자가 자신의 컴퓨터에서 로컬 LLM을 설치하고, 개인 문서를 Bronze/Silver/Gold 3계층으로 정리한 뒤, Claude Code나 Codex에서 구축된 RAG memory pool에 질문하는 것입니다.

## 의도한 사용자 흐름

1. 사용자가 Claude Code나 Codex를 터미널에서 엽니다.
2. Adaptive Memory Engine을 설치합니다.
3. `memory doctor`로 컴퓨터 사양을 진단합니다.
4. `memory setup`으로 사양에 맞는 로컬 LLM과 embedding model을 추천받습니다.
5. `memory setup --execute`로 Ollama 모델을 다운로드합니다.
6. `memory load <corpus> <docs>`로 문서 폴더를 읽힙니다.
7. 엔진이 `$AME_HOME/corpora/<corpus>` 아래에 corpus 폴더를 만들고 Bronze/Silver/Gold memory를 구축합니다.
8. `memory connect <corpus> --client codex` 또는 `--client claude`로 MCP 연결 설정을 출력합니다.
9. Claude Code나 Codex가 `memory mcp stdio <corpus>`를 MCP server로 실행합니다.
10. 사용자가 질문하면 Claude Code나 Codex는 구축된 local RAG memory pool에서 `memory_search`, `memory_retrieve`, `memory_graph`, `memory_decisions` 같은 tool을 호출해 답변합니다.

## 사용자가 실행하는 명령

```bash
pip install adaptive-memory-engine
export AME_HOME="$PWD/.ame"

memory doctor
memory setup
memory setup --execute

memory load my-docs ./docs
memory connect my-docs --client codex
```

Windows PowerShell에서는 환경변수를 다음처럼 설정합니다.

```powershell
$env:AME_HOME = "$PWD\.ame"
memory doctor
memory setup
memory setup --execute
memory load my-docs .\docs
memory connect my-docs --client codex
```

`AME_HOME`을 지정하지 않으면 기본 runtime 위치는 OS별로 달라집니다.

- macOS: `~/Library/Application Support/ame`
- Windows: `%LOCALAPPDATA%\AdaptiveMemoryEngine`
- Linux: `$XDG_DATA_HOME/ame` 또는 `~/.local/share/ame`

Claude Code나 Codex에 등록되는 MCP server command는 다음 형태입니다.

```json
{
  "mcpServers": {
    "adaptive-memory-engine": {
      "command": "memory",
      "args": ["mcp", "stdio", "my-docs"],
      "env": {
        "AME_HOME": "/absolute/path/to/.ame"
      }
    }
  }
}
```

## 3계층 build 책임

Bronze:

- 원본 문서 저장
- source path, hash, metadata 보존
- 재추출과 검증의 기준 제공

Silver:

- 로컬 LLM 중심 계층
- entity, relation, decision, rationale 추출
- grounding, confidence, type validation 대상 생성

Gold:

- graph, timeline, ontology, supersedes 구조 생성
- 검색과 agent tool 호출에 사용할 memory pool 구성
- LightRAG custom KG staging

## Codex/Claude Code 역할

Codex나 Claude Code는 문서 전체를 매번 다시 읽는 것이 아닙니다.

기본 흐름에서는 이미 구축된 local memory pool을 MCP tool로 조회합니다.  
모델은 조회된 memory result를 바탕으로 추론하고 답변합니다.

즉, 제품의 핵심은 다음 분리입니다.

```text
Local AME
  -> 문서 수집
  -> 로컬 LLM 기반 Silver 추출
  -> Gold memory pool 구축
  -> MCP tools 제공

Codex / Claude Code
  -> MCP tools 호출
  -> 검색된 memory를 바탕으로 답변/작업 수행
```

## Fallback

`memory load --mode deterministic`은 기본 제품 흐름이 아닙니다.

이 모드는 다음 상황에서만 사용합니다.

- 테스트
- 데모
- 로컬 LLM 설치 전 smoke check
- 저사양 환경에서 최소 기능 확인

정식 사용자 경험은 `memory setup --execute` 이후 `memory load`를 실행하는 local-LLM first 흐름입니다.
