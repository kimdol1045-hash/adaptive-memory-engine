# Adaptive Memory Engine Core

[English](README.en.md)

Adaptive Memory Engine Core는 로컬 문서를 Bronze/Silver/Gold 구조로 정리하고,
그 결과를 Codex, Claude Code 같은 MCP 클라이언트에서 바로 사용할 수 있게 해주는
local-first CLI 메모리 엔진입니다.

현재는 alpha 단계이며, 패키지는 TestPyPI를 통해 베타 배포하고 있습니다.

## 핵심 흐름

목표 사용 흐름은 다음과 같습니다.

```text
Claude Code 또는 Codex 터미널 실행
  -> AME 설치
  -> 컴퓨터 사양 진단
  -> 로컬 LLM 추천
  -> 모델 다운로드
  -> 내 문서 로드
  -> Bronze/Silver/Gold RAG 메모리 구축
  -> 터미널 chat 모드 또는 MCP로 질문
```

## 지원 환경

AME는 같은 `memory` CLI로 macOS, Windows, Linux에서 동작하도록 설계되어 있습니다.

- macOS: 기본 런타임 경로는 `~/Library/Application Support/ame`입니다.
- Windows: 기본 런타임 경로는 `%LOCALAPPDATA%\AdaptiveMemoryEngine`입니다.
- Linux: `$XDG_DATA_HOME/ame` 또는 `~/.local/share/ame`을 사용합니다.

로컬 LLM 모델 다운로드와 실행을 위해서는 Ollama가 설치되어 있고 `PATH`에서 실행 가능해야 합니다.

## 설치

베타 패키지는 TestPyPI에서 설치할 수 있습니다.

```bash
pipx install adaptive-memory-engine \
  --pip-args="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/"
```

소스에서 직접 설치하려면 다음 명령어를 사용합니다.

```bash
git clone https://github.com/kimdol1045-hash/adaptive-memory-engine.git
cd adaptive-memory-engine
python3 -m pip install -e ".[dev]"
```

개발 환경에서 로컬 런타임 경로를 명시하고 싶다면 다음처럼 설정할 수 있습니다.

```bash
export AME_HOME="$PWD/.ame"
```

## 빠른 시작

먼저 현재 컴퓨터 사양과 로컬 LLM 상태를 확인합니다.

```bash
memory doctor
```

추천 모델과 설치 상태를 확인합니다.

```bash
memory setup
```

추천 모델을 Ollama로 다운로드합니다.

```bash
memory setup --execute
```

문서 폴더를 읽어서 로컬 메모리를 구축합니다.

```bash
memory load my-docs ./path/to/markdown-docs
```

구축된 메모리에서 검색하거나 질문합니다.

```bash
memory retrieve my-docs "현재 유효한 결정은 무엇인가요?"
memory query my-docs "왜 LightRAG 구조를 선택했나요?"
```

매번 명령어를 치기 싫다면 대화형 모드로 들어갑니다.

```bash
memory chat my-docs
```

이후에는 프롬프트 안에서 질문만 입력하면 됩니다.

```text
ame> 현재 유효한 결정은 무엇인가요?
ame> 왜 LightRAG 구조를 선택했나요?
ame> /exit
```

Codex 또는 Claude Code 안에서 명령어 없이 쓰고 싶다면 MCP 설정을 출력합니다.

```bash
memory connect my-docs --client codex
memory connect my-docs --client claude
```

## Bronze/Silver/Gold 구조

AME의 기본 설계는 문서를 한 번에 요약하는 방식이 아니라, 문서 메모리를 단계별로 구축하는 방식입니다.

- Bronze: 원본 문서를 보존합니다. 이 단계는 LLM 없이도 동작합니다.
- Silver: 문서에서 엔티티, 관계, 결정, 근거, 제약을 구조화합니다. 기본값은 로컬 LLM 기반 추출입니다.
- Gold: Silver 결과를 바탕으로 그래프, 타임라인, 온톨로지, supersession, 검증 정보를 구성합니다.

`memory load`의 기본 모드는 로컬 LLM을 사용하는 Bronze/Silver/Gold 구축입니다.
가벼운 테스트나 fallback이 필요할 때만 deterministic 모드를 사용합니다.

```bash
memory load my-docs ./path/to/docs --mode deterministic
```

## MCP 연결

AME는 문서 메모리를 만든 뒤, MCP stdio 서버로 Codex나 Claude Code에 연결할 수 있습니다.
MCP로 연결하면 터미널에서 `memory query ...`를 매번 입력하지 않고, Codex나 Claude Code 안에서 평소처럼 질문하면 됩니다.

```bash
memory mcp stdio my-docs
```

`memory connect` 명령어는 클라이언트 설정에 넣을 JSON 형태를 출력합니다.

```json
{
  "command": "memory",
  "args": ["mcp", "stdio", "my-docs"],
  "env": {
    "AME_HOME": "/absolute/path/to/.ame"
  }
}
```

MCP는 연결 계층입니다. 문서를 직접 분석하는 역할은 `memory load` 단계에서 수행하고,
MCP는 이미 구축된 로컬 메모리를 Codex, Claude Code, 기타 MCP 클라이언트에 노출합니다.

사용 가능한 MCP 도구에는 `memory_search`, `memory_retrieve`, `memory_graph`,
`memory_decisions`, `memory_timeline`, `memory_why`, `memory_diff`,
`memory_write_decision`, `memory_write_note`가 포함됩니다.

## 로컬 LLM 추출

LLM 추출은 기본적으로 Ollama를 사용합니다.

```bash
AME_OLLAMA_MODEL=qwen3:8b memory ingest openclaw ./examples/notes --mode llm
```

LightRAG Core 연동을 실험하려면 optional dependency를 설치합니다.

```bash
pip install -e ".[lightrag]"
```

그 다음 `$AME_HOME/config.toml`에 설정을 추가할 수 있습니다.

```toml
[lightrag]
backend = "core"
query_mode = "hybrid"
llm_model = "qwen3:8b"
embedding_model = "nomic-embed-text"
embedding_dim = 768
max_token_size = 8192
```

## 자주 쓰는 명령어

```bash
memory init
memory doctor
memory setup
memory setup --execute
memory load my-docs ./path/to/docs
memory chat my-docs
memory stats my-docs
memory inspect my-docs
memory retrieve my-docs "질문"
memory graph my-docs
memory decisions my-docs
memory connect my-docs --client codex
```

## SDK

```python
from ame.sdk import Corpus
from memory import Corpus
```

## 테스트

전체 테스트를 실행합니다.

```bash
pytest
```

CLI 패키지의 핵심 흐름만 빠르게 확인하려면 다음 테스트를 사용할 수 있습니다.

```bash
pytest tests/test_pipeline.py tests/test_query_engine.py
```

## 참고 문서

- `docs/product_user_flow.md`: 의도한 CLI 제품 흐름
- `docs/release_distribution_plan.md`: 외부 배포 계획
- `docs/pypi_release_checklist.md`: PyPI/TestPyPI 배포 체크리스트
- `docs/standalone_distribution.md`: standalone 패키지 분리 전략
