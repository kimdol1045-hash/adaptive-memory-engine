from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Literal, Protocol


SENSITIVE_KEYS = {"access_token", "refresh_token", "client_secret", "authorization", "token"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})(?!\w)")
PiiRedactionMode = Literal["off", "metadata", "content"]


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod(path.parent, 0o700)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _chmod(path, 0o600)


def ensure_private_file(path: Path) -> None:
    if path.exists():
        _chmod(path, 0o600)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, 0o700)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[redacted]" if key.casefold() in SENSITIVE_KEYS else redact_secrets(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def redact_pii(value: Any) -> Any:
    if isinstance(value, str):
        return PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", value))
    if isinstance(value, dict):
        return {key: redact_pii(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    return value


class TokenVaultError(RuntimeError):
    pass


class TokenVault(Protocol):
    backend: str

    def load(self) -> dict[str, Any]:
        ...

    def save(self, payload: dict[str, Any]) -> None:
        ...

    def delete(self) -> None:
        ...


class PrivateFileTokenVault:
    backend = "file"

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        ensure_private_file(self.path)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, payload: dict[str, Any]) -> None:
        write_private_json(self.path, payload)

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()


class MacOSKeychainTokenVault:
    backend = "keychain"

    def __init__(
        self,
        service: str,
        account: str = "tokens",
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ):
        self.service = service
        self.account = account
        self.runner = runner or subprocess.run

    @staticmethod
    def available() -> bool:
        return sys.platform == "darwin" and shutil.which("security") is not None

    def load(self) -> dict[str, Any]:
        result = self._run(["security", "find-generic-password", "-a", self.account, "-s", self.service, "-w"], check=False)
        if result.returncode != 0:
            return {}
        secret = result.stdout.strip()
        return json.loads(secret) if secret else {}

    def save(self, payload: dict[str, Any]) -> None:
        secret = json.dumps(payload, ensure_ascii=False)
        result = self._run(
            ["security", "add-generic-password", "-a", self.account, "-s", self.service, "-w", secret, "-U"],
            check=False,
        )
        if result.returncode != 0:
            raise TokenVaultError(result.stderr.strip() or f"Keychain save failed for {self.service}")

    def delete(self) -> None:
        self._run(["security", "delete-generic-password", "-a", self.account, "-s", self.service], check=False)

    def _run(self, args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        return self.runner(args, text=True, capture_output=True, check=check)


def token_vault(provider: str, path: Path, backend: Literal["file", "keychain", "auto"] = "file") -> TokenVault:
    if backend == "keychain":
        if not MacOSKeychainTokenVault.available():
            raise TokenVaultError("macOS Keychain backend is not available on this system")
        return MacOSKeychainTokenVault(service=f"adaptive-memory-engine.{provider}")
    if backend == "auto" and MacOSKeychainTokenVault.available():
        return MacOSKeychainTokenVault(service=f"adaptive-memory-engine.{provider}")
    return PrivateFileTokenVault(path)


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass
