# Adaptive Memory Engine Core

[English](README.en.md)

Adaptive Memory Engine Core는 내 로컬 문서를 읽어 Bronze/Silver/Gold 메모리로 만들고,
Codex나 Claude Code가 그 메모리를 보고 답할 수 있게 해주는 local-first 메모리 엔진입니다.

사용자가 매번 긴 명령어를 치는 방식보다, **Codex/Claude Code에 AME를 연결하고 자연어로 맡기는 방식**을 우선합니다.

현재는 alpha 단계이며 TestPyPI로 베타 배포 중입니다. 현재 베타 버전은 `0.1.4`입니다.

## 1. 설치

`pipx`가 없어도 됩니다. 아래를 그대로 실행합니다.

```bash
python3 -m venv ~/.ame
source ~/.ame/bin/activate

python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  adaptive-memory-engine==0.1.4
```

설치 확인:

```bash
hash -r
which ame
ame --help
```

`which ame` 결과가 `~/.ame/bin/ame`처럼 나오면 정상입니다.

## 2. Codex 또는 Claude Code에 연결

Codex용 MCP 설정을 출력합니다.

```bash
ame connect --client codex
```

Claude Code용 MCP 설정은 다음과 같습니다.

```bash
ame connect --client claude
```

출력된 JSON을 Codex 또는 Claude Code의 MCP 설정에 추가합니다.
JSON 안의 `command`에는 `~/.ame/bin/ame` 같은 절대경로가 들어갑니다.
그래서 MCP 클라이언트가 실행될 때마다 가상환경을 직접 활성화할 필요는 없습니다.

이때 아직 문서 메모리를 만들지 않았어도 괜찮습니다. `ame connect --client ...`는 bootstrap MCP 설정을 출력하므로, Codex/Claude Code가 사양 진단부터 메모리 구축까지 진행할 수 있습니다.

## 3. 자연어로 요청

이제 Codex나 Claude Code에 이렇게 말하면 됩니다.

```text
내 컴퓨터 사양을 진단하고 AME에 맞는 로컬 모델을 추천해줘.
다운로드가 필요하면 어떤 모델을 받을지 먼저 알려줘.
내가 승인하면 모델을 설치해줘.
그 다음 /Users/me/Documents/planning 폴더를 my-docs라는 이름으로 메모리화해줘.
구축이 끝나면 그 메모리를 기준으로 질문에 답해줘.
```

이후에는 평소처럼 질문하면 됩니다.

```text
이 문서들에서 현재 유효한 결정은 뭐야?
왜 이런 구조를 선택했는지 근거를 찾아줘.
지난 결정 중 지금은 superseded 된 게 있어?
```

## AME가 제공하는 MCP 도구

Codex/Claude Code는 AME MCP를 통해 다음 도구를 사용할 수 있습니다.

- `ame_doctor`: 컴퓨터 사양과 로컬 모델 상태 진단
- `ame_setup`: 추천 모델 다운로드 계획 또는 실행
- `ame_load`: 문서 폴더를 Bronze/Silver/Gold 메모리로 구축
- `ame_corpora`: 만들어진 corpus 목록 확인
- `memory_search`, `memory_query`: 구축된 메모리 기반 질문
- `memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`: 구조화된 메모리 조회

모델 다운로드는 시간과 디스크를 사용합니다. Codex/Claude Code가 먼저 다운로드 계획을 보여준 뒤, 사용자가 승인하면 실행하는 흐름을 권장합니다.

## CLI로 직접 쓰고 싶을 때

에이전트 없이 직접 사용할 수도 있습니다.

```bash
ame doctor
ame setup
ame setup --execute
ame load my-docs ./path/to/markdown-docs
ame chat my-docs
```

`ame chat`에 들어가면 매번 명령어를 치지 않고 질문만 입력할 수 있습니다.

```text
ame> 현재 유효한 결정은 뭐야?
ame> 왜 LightRAG를 선택했어?
ame> /exit
```

## 설치 문제 해결

가상환경은 패키지를 격리해서 설치하기 위한 용도입니다.
MCP 설정을 한 번 추가한 뒤에는 Codex/Claude Code가 설정에 들어간 절대경로로 `ame`를 직접 실행합니다.

`ame` 명령이 안 보이면 가상환경을 다시 활성화합니다.

```bash
source ~/.ame/bin/activate
hash -r
which ame
ame --help
```

예전 문서의 `memory` 명령과 충돌할 수 있어서, 새 버전에서는 `ame` 명령을 기본으로 사용합니다.
`memory`는 호환용 alias로 남아 있지만 가능하면 `ame`를 사용하세요.

## MCP 모드

AME는 두 가지 MCP 모드를 제공합니다.

아직 corpus가 없고 Codex/Claude Code가 설정부터 진행해야 한다면 bootstrap MCP를 사용합니다.

```bash
ame mcp stdio
```

이미 만들어진 특정 corpus만 보게 하려면 corpus-bound MCP를 사용합니다.

```bash
ame mcp stdio my-docs
```

대부분의 사용자는 직접 `ame mcp stdio`를 실행하지 않고, `ame connect --client codex` 또는 `ame connect --client claude`로 출력된 설정을 클라이언트에 넣으면 됩니다.

## Bronze/Silver/Gold 구조

- Bronze: 원본 문서를 보존합니다.
- Silver: 엔티티, 관계, 결정, 근거, 제약을 구조화합니다.
- Gold: 그래프, 타임라인, supersession, 검증 정보를 구성합니다.

`ame load`의 기본 모드는 로컬 LLM을 사용하는 Bronze/Silver/Gold 구축입니다.
테스트나 fallback이 필요할 때만 deterministic 모드를 사용합니다.

```bash
ame load my-docs ./path/to/docs --mode deterministic
```

## SDK

```python
from ame.sdk import Corpus
from memory import Corpus
```

## 테스트

```bash
pytest
```

## 참고 문서

- `docs/product_user_flow.md`: 의도한 CLI 제품 흐름
- `docs/release_distribution_plan.md`: 외부 배포 계획
- `docs/pypi_release_checklist.md`: PyPI/TestPyPI 배포 체크리스트
- `docs/standalone_distribution.md`: standalone 패키지 분리 전략
