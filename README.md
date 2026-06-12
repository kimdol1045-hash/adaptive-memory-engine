# Adaptive Memory Engine Core

[English](README.en.md)

Adaptive Memory Engine Core는 내 로컬 문서를 읽어 Bronze/Silver/Gold 메모리로 만들고,
Codex나 Claude Code가 그 메모리를 보고 답할 수 있게 해주는 local-first 메모리 엔진입니다.

사용자가 매번 긴 명령어를 치는 방식보다, **Codex/Claude Code에 AME를 연결하고 자연어로 맡기는 방식**을 우선합니다.

현재는 alpha 단계이며 PyPI로 배포 중입니다. 현재 버전은 `0.1.9`입니다.

## 1. 설치

macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.ps1 | iex
```

설치 스크립트는 `~/.ame`에 AME를 설치하고 `ame` 명령을 PATH에 추가합니다. macOS/Linux에서는 설치 직후 스크립트가 출력하는 `source ...` 명령을 현재 터미널에 한 번 실행하면 됩니다.

```bash
source ~/.zshrc
```

직접 설치하고 싶다면 PyPI에서 설치할 수 있습니다.

```bash
python -m pip install adaptive-memory-engine
```

커스텀 MCP로만 쓸 때도 AME 실행 파일은 로컬에 있어야 합니다. PyPI/GitHub는 설치 파일을 배포하는 곳이고, MCP 클라이언트는 로컬에서 `ame mcp stdio` 프로세스를 실행합니다.

## 2. Codex 또는 Claude Code에 연결

Codex용 MCP 설정을 출력해서 Codex의 커스텀 MCP 설정에 붙입니다.

```bash
ame connect --client codex
```

Claude Code를 쓴다면 다음 명령을 사용합니다.

```bash
ame connect --client claude
```

출력된 JSON의 기본 `command`는 절대경로가 아니라 `ame`입니다.

```json
{
  "command": "ame",
  "args": ["mcp", "stdio"]
}
```

기본 설정에는 실행 파일 절대경로를 넣지 않습니다. MCP 클라이언트가 실행될 때마다 가상환경을 직접 활성화할 필요도 없습니다.

이때 아직 문서 메모리를 만들지 않았어도 괜찮습니다. `ame connect --client ...`는 bootstrap MCP 설정을 출력하므로, Codex/Claude Code가 사양 진단부터 메모리 구축까지 진행할 수 있습니다.

## 3. 자연어로 진행

한 번에 길게 요청하기보다, 아래 흐름대로 하나씩 진행하는 것을 권장합니다.

처음에는 아래 문장을 그대로 입력하는 것이 가장 안전합니다. 이 문장은 에이전트가 shell 명령이나 웹 검색보다 AME MCP 도구를 먼저 쓰도록 유도합니다.

```text
AME MCP를 사용해서 단계별로 진행해줘.
먼저 ame_flow를 확인하고, 사양 진단은 ame_doctor로 해줘.
모델 다운로드는 ame_setup execute=false로 계획만 먼저 보여주고,
내가 승인하기 전에는 execute=true를 실행하지 마.
```

그 다음 사양 진단을 요청합니다.

```text
내 컴퓨터 사양을 진단하고 AME에 맞는 로컬 모델을 추천해줘.
```

모델 다운로드가 필요하면 먼저 계획만 확인합니다.

```text
다운로드가 필요한 모델과 이유를 먼저 알려줘. 아직 설치는 하지 마.
```

계획을 보고 승인한 뒤 설치합니다.

```text
승인할게. 필요한 모델을 설치해줘.
```

문서 폴더와 corpus 이름을 지정해서 메모리를 구축합니다.

```text
/Users/me/Documents/planning 폴더를 my-docs라는 이름으로 메모리화해줘.
```

구축 후에는 메모리 기준으로 질문합니다.

```text
my-docs 메모리를 기준으로 현재 유효한 결정과 그 근거를 알려줘.
```

정상 플로우는 다음 순서입니다.

```text
ame_flow -> ame_doctor -> ame_setup execute=false -> 사용자 승인 -> ame_setup execute=true -> ame_load -> memory_query/memory_search
```

사양 진단과 모델 추천 단계에서는 corpus가 필요 없습니다. 문서 메모리 구축 단계에서만 corpus 이름을 정하면 됩니다.

## 4. 단계별 응답 템플릿

AME MCP의 `ame_flow`는 에이전트가 답변에 사용할 템플릿을 제공합니다. 사용자가 직접 템플릿을 보고 싶다면 이렇게 요청하면 됩니다.

```text
ame_flow에서 model_plan 단계의 output_template을 보여줘.
```

권장 응답 형태는 다음과 같습니다.

사양 진단:

```text
사양 진단 결과입니다.

- OS/CPU: ...
- RAM: ...
- 사용 가능 디스크: ...
- AME tier: ...

추천 모델은 다음과 같습니다.

- 추출: ...
- 검증: ...
- 종합: ...
- 임베딩: ...

현재 설치 상태를 보면 ...입니다.
다음 단계는 ...입니다.
```

모델 다운로드 계획:

```text
모델 설치 계획입니다. 아직 다운로드는 실행하지 않았습니다.

필요한 모델:
...

이 모델들이 필요한 이유:
- 추출 모델: 문서에서 엔티티, 관계, 결정, 근거를 뽑기 위해 사용합니다.
- 검증 모델: 추출된 내용을 원문과 대조해 과한 추론을 줄이는 데 사용합니다.
- 종합 모델: Bronze/Silver 결과를 Gold 메모리로 정리하는 데 사용합니다.
- 임베딩 모델: 문서 검색과 RAG 검색에 사용합니다.

진행하면 로컬 디스크와 다운로드 시간이 사용됩니다.
이 계획대로 모델을 설치해도 될까요?
```

문서 메모리 구축:

```text
문서 메모리 구축 결과입니다.

- corpus: ...
- 대상 폴더: ...
- 구축 방식: Bronze -> Silver -> Gold
- 처리 문서: ...
- Gold nodes: ...
- Gold edges: ...
- 제외/실패 항목: ...

이제 이 메모리를 기준으로 질문할 수 있습니다.
```

## AME가 제공하는 MCP 도구

Codex/Claude Code는 AME MCP를 통해 다음 도구를 사용할 수 있습니다.

- `ame_doctor`: 컴퓨터 사양과 로컬 모델 상태 진단
- `ame_flow`: 단계별 진행 방식과 응답 템플릿 확인
- `ame_setup`: 추천 모델 다운로드 계획 또는 실행
- `ame_load`: 문서 폴더를 Bronze/Silver/Gold 메모리로 구축
- `ame_corpora`: 만들어진 corpus 목록 확인
- `memory_search`, `memory_query`: 구축된 메모리 기반 질문
- `memory_graph`, `memory_decisions`, `memory_timeline`, `memory_why`: 구조화된 메모리 조회

모델 다운로드는 시간과 디스크를 사용합니다. Codex/Claude Code가 먼저 다운로드 계획을 보여준 뒤, 사용자가 승인하면 실행하는 흐름을 권장합니다.

사양 진단이나 모델 추천은 corpus가 필요 없는 bootstrap MCP에서 처리합니다. 문서 메모리 구축 단계에서만 corpus 이름과 문서 폴더가 필요합니다.

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
MCP 설정을 한 번 추가한 뒤에는 Codex/Claude Code가 `ame` 명령을 직접 실행합니다.

이미 설치한 적이 있다면 업그레이드를 명시합니다.

```bash
python -m pip install --upgrade adaptive-memory-engine
python -m pip show adaptive-memory-engine
```

출력의 `Version`이 현재 README의 버전과 같아야 합니다.

터미널에서 `ame` 명령이 안 보이면 PATH를 다시 적용합니다.

```bash
source ~/.zshrc
ame --help
ame connect --client codex
```

MCP 클라이언트가 `ame`를 찾지 못한다면 PATH를 JSON에 같이 넣을 수 있습니다.

```bash
ame connect --client codex --include-path-env
```

그래도 안 되면 예전 방식처럼 실행 파일 절대경로를 넣을 수 있습니다.

```bash
ame connect --client codex --absolute-command
```

예전 문서의 `memory` 명령과 충돌할 수 있어서, 새 버전에서는 `ame` 명령을 기본으로 사용합니다.
`memory`는 호환용 alias로 남아 있지만 가능하면 `ame`를 사용하세요.

`ame`가 여전히 보이지 않으면 설치 스크립트로 `~/.ame`에 격리 설치하는 방법이 가장 단순합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/kimdol1045-hash/adaptive-memory-engine/main/install.sh | bash
source ~/.zshrc
ame --help
```

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
