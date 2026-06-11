# Adaptive Memory Engine Core

[English](README.en.md)

Adaptive Memory Engine Core는 로컬 문서를 Bronze/Silver/Gold 구조로 정리하고,
그 결과를 Codex, Claude Code 같은 MCP 클라이언트가 조회할 수 있게 해주는
local-first 메모리 엔진입니다.

사용자가 매번 긴 CLI 명령어를 직접 입력하는 것보다, AME를 MCP로 연결한 뒤
Codex나 Claude Code에게 자연어로 맡기는 사용 방식을 우선합니다.

현재는 alpha 단계이며, 패키지는 TestPyPI를 통해 베타 배포하고 있습니다.

## 핵심 흐름

목표 사용 흐름은 다음과 같습니다.

```text
AME 설치
  -> Codex 또는 Claude Code에 AME MCP 연결
  -> "내 컴퓨터 사양 진단해줘"라고 말하기
  -> "추천 모델 알려줘"라고 말하기
  -> "승인할게. 모델 설치해줘"라고 말하기
  -> "이 문서 폴더로 메모리 구축해줘"라고 말하기
  -> 이후에는 구축된 로컬 메모리를 기준으로 자연어 질문
```

## 지원 환경

AME는 같은 `memory` CLI로 macOS, Windows, Linux에서 동작하도록 설계되어 있습니다.

- macOS: 기본 런타임 경로는 `~/Library/Application Support/ame`입니다.
- Windows: 기본 런타임 경로는 `%LOCALAPPDATA%\AdaptiveMemoryEngine`입니다.
- Linux: `$XDG_DATA_HOME/ame` 또는 `~/.local/share/ame`을 사용합니다.

로컬 LLM 모델 다운로드와 실행을 위해서는 Ollama가 설치되어 있고 `PATH`에서 실행 가능해야 합니다.

## 설치

현재 베타 버전은 `0.1.2`입니다.

가장 쉬운 방법은 Python 가상환경에 설치하는 것입니다. `pipx`가 없어도 됩니다.

```bash
python3 -m venv ~/.ame
source ~/.ame/bin/activate

python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  adaptive-memory-engine==0.1.2
```

설치가 끝나면 다음 명령어로 확인합니다.

```bash
hash -r
which memory
memory --help
```

`which memory`가 `~/.ame/bin/memory` 또는 현재 활성화한 가상환경의 `bin/memory`를 가리키면 정상입니다.
예전 전역 설치 경로가 나온다면 가상환경을 다시 활성화하고 zsh 명령어 캐시를 갱신합니다.

```bash
source ~/.ame/bin/activate
hash -r
which memory
```

`memory setup`에서 `No such command 'setup'`이 나오면 최신 core 패키지가 아니라 예전 CLI가 실행되고 있는 상태입니다.
이때는 다음처럼 가상환경 안의 실행 파일을 직접 호출해 확인할 수 있습니다.

```bash
~/.ame/bin/memory --help
~/.ame/bin/memory setup
```

`pipx`를 이미 쓰고 있다면 다음 방식도 가능합니다.

```bash
pipx install adaptive-memory-engine==0.1.2 \
  --pip-args="--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/"
```

`pipx: command not found`가 나오면 먼저 `pipx`를 설치해야 합니다.

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

그 다음 터미널을 새로 열고 `pipx install ...` 명령어를 다시 실행합니다.

개발자가 소스에서 직접 설치하려면 다음 명령어를 사용합니다.

```bash
git clone https://github.com/kimdol1045-hash/adaptive-memory-engine.git
cd adaptive-memory-engine
python3 -m pip install -e ".[dev]"
```

개발 환경에서 로컬 런타임 경로를 명시하고 싶다면 다음처럼 설정할 수 있습니다.

```bash
export AME_HOME="$PWD/.ame"
```

## 빠른 시작: Codex/Claude Code에서 자연어로 쓰기

권장 흐름은 사용자가 모든 명령어를 직접 치는 방식이 아니라, Codex나 Claude Code에 AME MCP를 연결한 뒤 자연어로 맡기는 방식입니다.
사용자가 직접 실행해야 하는 명령어는 설치 후 MCP 설정을 출력하는 정도입니다.

Codex용 bootstrap MCP 설정을 출력합니다.

```bash
memory connect --client codex
```

Claude Code를 쓰면 Claude용 설정을 출력합니다.

```bash
memory connect --client claude
```

출력된 MCP 설정을 클라이언트에 추가하면, 아직 corpus가 없어도 Codex/Claude Code가 AME 초기 설정을 도구로 수행할 수 있습니다.

- `ame_doctor`: 컴퓨터 사양, AME 런타임, 추천 로컬 모델 진단
- `ame_setup`: 추천 모델 다운로드 계획 또는 실행
- `ame_load`: 문서 폴더를 Bronze/Silver/Gold 메모리로 구축
- `ame_corpora`: 로컬에 구축된 corpus 목록 확인
- `memory_search`, `memory_query`: 구축된 메모리 기반 질문

그 다음 Codex나 Claude Code에 이렇게 말하면 됩니다.

```text
내 컴퓨터 사양을 진단하고 AME에 맞는 로컬 모델을 추천해줘.
모델 다운로드가 필요하면 먼저 어떤 모델을 받을지 알려줘.
내가 승인하면 모델을 설치하고, 내가 지정한 문서 폴더로 메모리를 구축해줘.
구축이 끝나면 그 메모리를 기준으로 질문에 답해줘.
```

문서 폴더를 넘길 때는 로컬 경로를 함께 말하면 됩니다.

```text
이 폴더를 my-docs라는 이름으로 메모리화해줘: /Users/me/Documents/planning
```

모델 다운로드는 디스크와 시간이 필요하므로, 에이전트가 `ame_setup`을 실행할 때는 먼저 계획을 보여주고 사용자 승인을 받은 뒤 `execute=true`로 진행하는 것이 좋습니다.

## CLI로 직접 쓰기

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

AME는 두 가지 MCP 연결 방식을 제공합니다.

아직 corpus가 없고, Codex/Claude Code가 사양 진단부터 메모리 구축까지 진행하게 하려면 bootstrap MCP를 사용합니다.

```bash
memory mcp stdio
```

이미 만들어진 특정 corpus만 조회하게 하려면 corpus-bound MCP를 사용합니다.

```bash
memory mcp stdio my-docs
```

`memory connect` 명령어는 클라이언트 설정에 넣을 JSON 형태를 출력합니다. corpus 없이 실행하면 bootstrap MCP 설정을 출력합니다.

```bash
memory connect --client codex
```

특정 corpus에 고정하려면 corpus id를 함께 넘깁니다.

```bash
memory connect my-docs --client codex
```

```json
{
  "command": "memory",
  "args": ["mcp", "stdio"],
  "env": {
    "AME_HOME": "/absolute/path/to/.ame"
  }
}
```

MCP는 연결 계층입니다. bootstrap MCP에서는 Codex/Claude Code가 `ame_load` 도구를 호출해 문서 메모리를 구축할 수 있고,
corpus-bound MCP에서는 이미 구축된 로컬 메모리만 조회하도록 제한할 수 있습니다.

bootstrap MCP에서 사용할 수 있는 도구에는 `ame_doctor`, `ame_setup`, `ame_load`, `ame_connect`, `ame_corpora`,
`memory_search`, `memory_retrieve`, `memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`,
`memory_diff`, `memory_write_decision`, `memory_write_note`가 포함됩니다.

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
