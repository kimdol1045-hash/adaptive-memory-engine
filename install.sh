#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${AME_INSTALL_DIR:-$HOME/.ame}"
PACKAGE="${AME_PACKAGE:-adaptive-memory-engine}"
VERSION="${AME_VERSION:-}"

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
  then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$INSTALL_DIR"
"$INSTALL_DIR/bin/python" -m pip install --upgrade pip

if [ -n "$VERSION" ]; then
  "$INSTALL_DIR/bin/python" -m pip install --upgrade "$PACKAGE==$VERSION"
else
  "$INSTALL_DIR/bin/python" -m pip install --upgrade "$PACKAGE"
fi

AME_BIN="$INSTALL_DIR/bin"
RC_FILE="${AME_SHELL_RC:-}"

if [ -z "$RC_FILE" ]; then
  SHELL_NAME="$(basename "${SHELL:-}")"
  if [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
  else
    RC_FILE="$HOME/.zshrc"
  fi
fi

mkdir -p "$(dirname "$RC_FILE")"
touch "$RC_FILE"

PATH_LINE='export PATH="$HOME/.ame/bin:$PATH"'
if [ "$INSTALL_DIR" != "$HOME/.ame" ]; then
  PATH_LINE="export PATH=\"$AME_BIN:\$PATH\""
fi

if ! grep -F "$PATH_LINE" "$RC_FILE" >/dev/null 2>&1; then
  printf '\n%s\n' "$PATH_LINE" >> "$RC_FILE"
fi

"$AME_BIN/ame" --help >/dev/null

cat <<EOF
Adaptive Memory Engine installed.

Run this once in your current terminal:
  source "$RC_FILE"

Then create your MCP config:
  ame connect --client codex

For Claude Code:
  ame connect --client claude
EOF
