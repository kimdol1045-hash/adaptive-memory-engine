# Release Distribution Plan

이 문서는 Adaptive Memory Engine을 외부 사용자가 설치해서 쓰게 만들기 위한 배포 계획입니다.

목표 제품 형태는 Python CLI 패키지입니다.

```text
사용자 터미널
  -> AME 설치
  -> memory doctor
  -> memory setup
  -> memory setup --execute
  -> memory load my-docs ./docs
  -> memory connect my-docs --client codex
  -> Codex / Claude Code에서 MCP tool로 local RAG memory 사용
```

## 1차 배포 채널

1차는 PyPI + pipx 배포가 가장 현실적입니다.

사용자 설치 명령:

```bash
pipx install adaptive-memory-engine
```

또는 Python 환경을 직접 관리하는 사용자는:

```bash
python -m pip install adaptive-memory-engine
```

이 방식의 장점:

- macOS, Windows, Linux에서 같은 CLI를 제공할 수 있습니다.
- `memory` console script를 그대로 배포할 수 있습니다.
- Homebrew, Scoop, Winget보다 초기 유지보수 부담이 낮습니다.
- Codex/Claude Code 사용자는 터미널에서 바로 설치할 수 있습니다.

## Beta 배포

PyPI 공개 전에는 GitHub URL 설치를 beta 채널로 사용할 수 있습니다.

```bash
pipx install "git+https://github.com/<owner>/adaptive-memory-engine-core.git"
```

private beta라면 SSH URL을 사용합니다.

```bash
pipx install "git+ssh://git@github.com/<owner>/adaptive-memory-engine-core.git"
```

## 릴리즈 전 필수 체크

배포 전 최소 체크리스트입니다.

- package name 확정
- version 확정
- README의 설치 흐름 정리
- LICENSE 확인
- Python 3.11 이상 지원 확인
- macOS smoke test
- Windows smoke test
- `memory doctor` 동작 확인
- `memory setup` 모델 추천 확인
- `memory setup --execute` Ollama pull 확인
- `memory load my-docs ./docs` LLM mode 확인
- `$AME_HOME/corpora/<corpus>` 폴더 생성 확인
- `memory connect my-docs --client codex` 출력 확인
- MCP `tools/list`, `tools/call` 확인

## Build

로컬에서 wheel과 sdist를 빌드합니다.

```bash
cd adaptive_memory_engine_core
python -m pip install build twine
python -m build
python -m twine check dist/*
```

생성물:

```text
dist/
  adaptive_memory_engine-<version>-py3-none-any.whl
  adaptive_memory_engine-<version>.tar.gz
```

## PyPI Upload

먼저 TestPyPI에 업로드합니다.

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-..."
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
unset TWINE_PASSWORD
```

TestPyPI 설치 검증:

```bash
python -m venv /tmp/ame-testpypi-smoke
/tmp/ame-testpypi-smoke/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  adaptive-memory-engine
/tmp/ame-testpypi-smoke/bin/memory --help
```

검증 후 PyPI 프로젝트에 업로드합니다.

```bash
python -m twine upload dist/*
```

운영 배포에서는 GitHub Actions + PyPI Trusted Publishing으로 바꾸는 것이 좋습니다.

권장 릴리즈 흐름:

```text
main branch
  -> version bump
  -> test
  -> build
  -> Git tag
  -> GitHub Release
  -> PyPI publish
```

## 사용자 설치 문서

최종 사용자 문서의 첫 화면은 다음 정도로 짧아야 합니다.

```bash
pipx install adaptive-memory-engine

export AME_HOME="$PWD/.ame"
memory doctor
memory setup
memory setup --execute
memory load my-docs ./docs
memory connect my-docs --client codex
```

Windows PowerShell:

```powershell
pipx install adaptive-memory-engine

$env:AME_HOME = "$PWD\.ame"
memory doctor
memory setup
memory setup --execute
memory load my-docs .\docs
memory connect my-docs --client codex
```

## 외부 의존성

사용자가 별도로 설치해야 하는 것:

- Python 3.11+
- pipx 또는 pip
- Ollama
- Codex 또는 Claude Code

AME가 처리하는 것:

- 컴퓨터 사양 진단
- tier 결정
- 로컬 LLM / embedding model 추천
- `ollama pull` 명령 계획
- `memory setup --execute`를 통한 모델 다운로드
- 문서 ingest
- Bronze/Silver/Gold memory build
- local MCP server 실행

## 이후 배포 채널

PyPI 배포가 안정화되면 다음 채널을 추가할 수 있습니다.

- Homebrew tap: macOS 사용자를 위한 `brew install`
- Scoop 또는 Winget: Windows 사용자를 위한 설치 경로
- Docker image: 서버나 격리 환경용
- GitHub Release binary: Python 설치를 어려워하는 사용자용

초기에는 PyPI/pipx만으로 충분합니다.

## 배포 전 남은 결정

- PyPI package name을 그대로 `adaptive-memory-engine`으로 쓸지 확인해야 합니다.
- GitHub repository 이름을 정해야 합니다.
- README 첫 화면을 end-user install 중심으로 줄여야 합니다.
- Windows 실제 장비에서 end-to-end smoke test가 필요합니다.
- 로컬 LLM 다운로드 실패 시 UX를 더 친절하게 다듬어야 합니다.
