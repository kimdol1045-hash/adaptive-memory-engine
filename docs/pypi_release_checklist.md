# PyPI Release Checklist

이 문서는 `adaptive-memory-engine`을 PyPI에 올리기 직전 확인할 항목입니다.

## 1. Package Metadata

- `pyproject.toml`의 `name` 확인
- `version` 확인
- `description` 확인
- `license` 확인
- classifiers 확인
- README가 end-user install 중심인지 확인

## 2. Local Verification

```bash
python -m pytest
python -m build
python -m twine check dist/*
```

## 3. Install Smoke Test

새 가상환경에서 wheel을 설치합니다.

```bash
python -m venv /tmp/ame-release-smoke
/tmp/ame-release-smoke/bin/python -m pip install dist/adaptive_memory_engine-0.1.0-py3-none-any.whl
/tmp/ame-release-smoke/bin/memory --help
```

Windows PowerShell:

```powershell
py -m venv $env:TEMP\ame-release-smoke
& "$env:TEMP\ame-release-smoke\Scripts\python.exe" -m pip install dist\adaptive_memory_engine-0.1.0-py3-none-any.whl
& "$env:TEMP\ame-release-smoke\Scripts\memory.exe" --help
```

## 4. Product Flow Smoke Test

```bash
export AME_HOME="/tmp/ame-release-runtime"
memory doctor
memory setup
memory load smoke-docs ./examples/notes --mode deterministic
memory connect smoke-docs --client codex
```

Full local LLM smoke test:

```bash
export AME_HOME="/tmp/ame-release-runtime-llm"
memory setup --execute
memory load smoke-docs ./examples/notes
memory retrieve smoke-docs "LightRAG"
```

## 5. PyPI Upload

TestPyPI API token을 먼저 발급합니다.

토큰은 채팅이나 문서에 저장하지 않습니다.  
로컬 터미널 환경변수로만 사용합니다.

macOS/Linux:

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-..."
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
unset TWINE_PASSWORD
```

Windows PowerShell:

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
Remove-Item Env:\TWINE_PASSWORD
```

TestPyPI는 dependency index가 실제 PyPI와 다릅니다.  
설치 검증 시에는 실제 PyPI를 extra index로 같이 지정합니다.

macOS/Linux:

```bash
python -m venv /tmp/ame-testpypi-smoke
/tmp/ame-testpypi-smoke/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  adaptive-memory-engine
/tmp/ame-testpypi-smoke/bin/memory --help
```

Windows PowerShell:

```powershell
py -m venv $env:TEMP\ame-testpypi-smoke
& "$env:TEMP\ame-testpypi-smoke\Scripts\python.exe" -m pip install `
  --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple/ `
  adaptive-memory-engine
& "$env:TEMP\ame-testpypi-smoke\Scripts\memory.exe" --help
```

주의:

- TestPyPI와 PyPI 모두 같은 version/file name을 다시 업로드할 수 없습니다.
- 같은 버전을 다시 테스트해야 하면 `pyproject.toml`의 version을 올려야 합니다.

Production PyPI:

```bash
python -m twine upload dist/*
```

## 6. Post-release Verification

```bash
pipx install adaptive-memory-engine
memory --help
memory doctor
```

Windows verification must be done on a real Windows machine before announcing Windows support broadly.
