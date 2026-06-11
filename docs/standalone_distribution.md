# Standalone Distribution

이 문서는 Adaptive Memory Engine Core만 따로 배포해서 터미널에서 사용하는 방법을 정리합니다.

Chronicle 앱, 웹 UI, 서비스 레이어는 포함하지 않습니다.  
배포 단위는 Python 패키지와 `memory` CLI입니다.

## 현재 배포 단위

현재 core 폴더는 독립 패키지로 설치할 수 있습니다.

- 패키지명: `adaptive-memory-engine`
- CLI 명령어: `memory`
- Python 모듈: `ame`, `memory`
- 런타임 데이터 위치: `$AME_HOME`
- 기본 저장 방식: local filesystem

지원 대상:

- macOS
- Windows
- Linux local filesystem runtime

Windows에서는 PowerShell 기준으로 `$env:AME_HOME = "$PWD\.ame"`처럼 환경변수를 지정합니다.

## 목표 사용자 흐름

```text
Claude Code 또는 Codex 터미널 시작
  -> Adaptive Memory Engine 설치
  -> 컴퓨터 사양 진단
  -> 로컬 LLM 추천
  -> 로컬 LLM 다운로드
  -> 문서 폴더 입력
  -> Bronze/Silver/Gold 3계층 RAG 구축
  -> MCP로 Claude Code 또는 Codex 연결
  -> 구축된 RAG memory pool에서 답변
```

자세한 흐름은 `docs/product_user_flow.md`에 정리했습니다.

## 로컬 설치

개발 중에는 editable install이 가장 편합니다.

```bash
cd adaptive_memory_engine_core
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
export AME_HOME="$PWD/.ame"
memory init
memory doctor
memory setup
memory setup --execute
```

문서 폴더를 corpus로 넣는 기본 흐름입니다.

```bash
memory create my-docs
memory ingest my-docs ./content/source_docs --mode llm
memory stats my-docs
memory retrieve my-docs "memory object와 raw document의 차이"
memory export obsidian my-docs ./exports/my-docs-vault
```

가장 짧은 흐름은 `load`입니다.

```bash
memory setup --execute
memory load my-docs ./content/source_docs
memory retrieve my-docs "memory object와 raw document의 차이"
memory connect my-docs --client codex
```

## Claude Code / Codex 연결

CLI는 설치, 초기화, 문서 적재를 담당합니다.

Claude Code, Codex 같은 agent client 연결은 MCP stdio server가 담당합니다.

```bash
export AME_HOME="/absolute/path/to/.ame"
memory load my-docs ./content/source_docs
memory mcp stdio my-docs
```

MCP client에는 다음 형태로 등록하면 됩니다.

```bash
memory connect my-docs --client codex
memory connect my-docs --client claude
```

위 명령은 다음 형태의 MCP server 설정을 출력합니다.

```json
{
  "command": "memory",
  "args": ["mcp", "stdio", "my-docs"],
  "env": {
    "AME_HOME": "/absolute/path/to/.ame"
  }
}
```

제공되는 MCP tools:

- `memory_search`
- `memory_retrieve`
- `memory_graph`
- `memory_decisions`
- `memory_timeline`
- `memory_why`
- `memory_diff`
- `memory_write_decision`
- `memory_write_note`

`memory serve my-docs --mcp`도 같은 stdio server를 실행합니다.

MCP transport 자체는 연결 계층입니다.

이 제품의 기본 사용 흐름은 로컬 LLM 기반 Bronze/Silver/Gold build입니다.  
사용자는 먼저 `memory setup --execute`로 컴퓨터 사양에 맞는 로컬 모델을 설치하고, `memory load`로 문서를 3계층 memory로 구축합니다.

그 다음 Codex나 Claude Code는 MCP tool 결과를 받아 사용합니다.

```bash
pip install adaptive-memory-engine
export AME_HOME="$PWD/.ame"
memory setup --execute
memory load my-docs ./docs
memory connect my-docs --client codex
```

하드웨어 프로파일러와 모델 레지스트리는 사용자 컴퓨터 사양에 맞춰 다음 모델 역할을 고르기 위한 구조입니다.

- extract model
- verify model
- synthesize model
- embedding model
- fallback policy

Bronze/Silver/Gold 기준으로 보면 다음처럼 나뉩니다.

- Bronze: 원본 문서 보존 계층입니다.
- Silver: entity, relation, decision, rationale 추출 계층이며 로컬 LLM이 가장 크게 개입하는 계층입니다.
- Gold: Silver 결과를 graph, timeline, ontology, supersession 구조로 승격하는 계층이며 deterministic builder와 validation gate가 중심입니다.

`memory load --mode deterministic`은 데모, 테스트, 저사양 fallback 용도입니다.  
사용자가 기대하는 “컴퓨터 사양에 맞는 local-first memory engine”의 기본 경로는 로컬 LLM 설치와 `memory load`입니다.

## Wheel 배포

다른 환경에 복사해서 설치하려면 wheel을 만들면 됩니다.

```bash
cd adaptive_memory_engine_core
python3 -m pip install build
python3 -m build
```

생성물은 `dist/` 아래에 만들어집니다.

설치 예시는 다음과 같습니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install ./dist/adaptive_memory_engine-0.1.0-py3-none-any.whl
export AME_HOME="$PWD/.ame"
memory init
memory doctor
```

## Git 기반 설치

별도 저장소로 분리한 뒤에는 Git URL로 설치할 수 있습니다.

```bash
python3 -m pip install "git+https://github.com/<owner>/adaptive-memory-engine-core.git"
```

private repo라면 SSH URL을 쓰는 편이 관리하기 쉽습니다.

```bash
python3 -m pip install "git+ssh://git@github.com/<owner>/adaptive-memory-engine-core.git"
```

## 런타임 데이터 분리

엔진 코드와 사용자 데이터는 분리해서 운영합니다.

권장 구조:

```text
adaptive-memory-engine-core/
  src/
  pyproject.toml

my-memory-runtime/
  .ame/
    config.toml
    registry.cache.yaml
    corpora/
```

실행할 때는 `AME_HOME`만 지정하면 됩니다.

```bash
export AME_HOME="/path/to/my-memory-runtime/.ame"
memory init
```

## 배포 범위

포함되는 것:

- memory CLI
- local filesystem runtime
- Markdown/Obsidian ingest
- bronze/silver/gold memory pipeline
- hardware-adaptive local model recommendation
- local LLM extraction through Ollama
- deterministic fallback extraction
- local MCP manifest/call simulation
- Obsidian export
- benchmark runner

포함하지 않는 것:

- Chronicle product UI
- hosted web API
- hosted MCP server
- team workspace service layer
- hosted OAuth callback server
- production billing/auth/user management

## 운영 전 체크리스트

- `memory init`이 성공하는가
- `memory doctor`가 현재 장비와 모델 상태를 출력하는가
- `memory create <corpus>`가 corpus 폴더를 만드는가
- `memory ingest <corpus> <docs>`가 문서를 읽는가
- `memory retrieve <corpus> <query>`가 local memory 결과를 반환하는가
- `memory export obsidian <corpus> <out>`이 export 파일을 만드는가

## 아직 배포 전에 정리하면 좋은 것

현재 터미널 패키지로 쓰는 것은 가능합니다.

다만 외부 사용자에게 배포하려면 다음을 추가로 정리하는 편이 좋습니다.

- release tag와 changelog
- PyPI 배포 여부 결정
- Docker image가 필요한지 결정
- `memory serve`를 실제 long-running MCP server로 확장할지 결정
- examples와 benchmark 데이터를 wheel에 포함할지 별도 repo asset으로 둘지 결정
