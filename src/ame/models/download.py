from __future__ import annotations

import shutil
import subprocess
import urllib.request
from collections.abc import Callable
import json
from typing import Literal

from pydantic import BaseModel, Field

from ame.hardware.profiler import HardwareProfile
from ame.models.router import ModelPlan


class ModelDownloadError(RuntimeError):
    pass


class ModelInstallPlan(BaseModel):
    tier: str
    mode: str
    ollama_installed: bool
    required_models: list[str] = Field(default_factory=list)
    installed_models: list[str] = Field(default_factory=list)
    installed_models_source: str | None = None
    missing_models: list[str] = Field(default_factory=list)
    pull_commands: list[list[str]] = Field(default_factory=list)
    error: str | None = None


class ModelPullResult(BaseModel):
    model: str
    command: list[str]
    status: Literal["planned", "skipped", "success", "failed"]
    transport: Literal["planned", "ollama_http", "ollama_cli"] = "planned"
    output: str = ""
    error: str = ""


CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]
JsonGetter = Callable[[str], dict]
JsonPoster = Callable[[str, dict], dict]


class OllamaModelInstaller:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        host: str = "http://127.0.0.1:11434",
        get_json: JsonGetter | None = None,
        post_json: JsonPoster | None = None,
        allow_cli_list: bool = False,
    ):
        self.runner = runner or self._run
        self.host = host.rstrip("/")
        self.get_json = get_json or self._get_json
        self.post_json = post_json or self._post_json
        self.allow_cli_list = allow_cli_list

    def install_plan(self, plan: ModelPlan, profile: HardwareProfile) -> ModelInstallPlan:
        required = self.required_ollama_models(plan)
        error = None
        source = None
        try:
            installed, source = self.installed_models_with_source() if profile.ollama_installed else ([], None)
        except ModelDownloadError as exc:
            installed = []
            error = str(exc)
        missing = [model for model in required if not is_model_installed(model, installed)]
        return ModelInstallPlan(
            tier=plan.tier,
            mode=plan.mode,
            ollama_installed=profile.ollama_installed,
            required_models=required,
            installed_models=installed,
            installed_models_source=source,
            missing_models=missing,
            pull_commands=[["ollama", "pull", model] for model in missing],
            error=error,
        )

    def required_ollama_models(self, plan: ModelPlan) -> list[str]:
        models = plan.models
        seen: set[str] = set()
        required: list[str] = []
        for role in [models.extract, models.verify, models.synthesize, models.embed]:
            if role.runtime != "ollama":
                continue
            if role.model in seen:
                continue
            seen.add(role.model)
            required.append(role.model)
        return required

    def installed_models(self) -> list[str]:
        models, _source = self.installed_models_with_source()
        return models

    def installed_models_with_source(self) -> tuple[list[str], str]:
        http_error: ModelDownloadError | None = None
        try:
            return self._installed_models_from_http(), "ollama_http"
        except ModelDownloadError as exc:
            http_error = exc
        if not self.allow_cli_list:
            raise http_error
        if shutil.which("ollama") is None:
            raise ModelDownloadError("Ollama HTTP API is unavailable and ollama CLI was not found.")
        result = self.runner(["ollama", "list"])
        if result.returncode != 0:
            raise ModelDownloadError(_clip_one_line(result.stderr or result.stdout or "ollama list failed"))
        return _parse_ollama_list(result.stdout), "ollama_cli"

    def pull(self, models: list[str], *, execute: bool = False, installed: list[str] | None = None) -> list[ModelPullResult]:
        installed_set = set(installed or [])
        results: list[ModelPullResult] = []
        if execute and shutil.which("ollama") is None:
            raise ModelDownloadError("Ollama is not installed. Install Ollama first, then run this command again.")
        for model in models:
            command = ["ollama", "pull", model]
            if is_model_installed(model, list(installed_set)):
                results.append(
                    ModelPullResult(
                        model=model,
                        command=command,
                        status="skipped",
                        transport="planned",
                        output="already installed",
                    )
                )
                continue
            if not execute:
                results.append(ModelPullResult(model=model, command=command, status="planned"))
                continue
            results.append(self._pull(model, command))
        return results

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def _installed_models_from_http(self) -> list[str]:
        try:
            payload = self.get_json(f"{self.host}/api/tags")
        except Exception as exc:
            raise ModelDownloadError(f"Ollama HTTP API is unavailable: {_clip(str(exc))}") from exc
        rows = payload.get("models")
        if not isinstance(rows, list):
            raise ModelDownloadError("Ollama HTTP API response did not include models.")
        models: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            model = row.get("model") or row.get("name")
            if model:
                models.append(str(model))
        return models

    def _pull_http(self, model: str, command: list[str]) -> ModelPullResult:
        try:
            payload = self.post_json(f"{self.host}/api/pull", {"name": model, "stream": False})
        except Exception as exc:
            return ModelPullResult(
                model=model,
                command=command,
                status="failed",
                transport="ollama_http",
                error=_clip(str(exc)),
            )
        error = payload.get("error")
        if error:
            return ModelPullResult(model=model, command=command, status="failed", transport="ollama_http", error=str(error))
        return ModelPullResult(model=model, command=command, status="success", transport="ollama_http", output=json.dumps(payload))

    def _pull(self, model: str, command: list[str]) -> ModelPullResult:
        http_result = self._pull_http(model, command)
        if http_result.status == "success":
            return http_result
        return self._pull_cli(model, command, http_result.error)

    def _pull_cli(self, model: str, command: list[str], http_error: str = "") -> ModelPullResult:
        result = self.runner(command)
        if result.returncode == 0:
            return ModelPullResult(
                model=model,
                command=command,
                status="success",
                transport="ollama_cli",
                output=result.stdout.strip(),
            )
        error = result.stderr.strip() or result.stdout.strip() or "ollama pull failed"
        if http_error:
            error = f"HTTP failed: {http_error}; CLI failed: {_clip(error)}"
        return ModelPullResult(
            model=model,
            command=command,
            status="failed",
            transport="ollama_cli",
            error=_clip(error),
        )

    def _get_json(self, url: str) -> dict:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=None) as response:
            return json.loads(response.read().decode("utf-8"))


def _parse_ollama_list(output: str) -> list[str]:
    models: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.casefold().startswith("name"):
            continue
        models.append(stripped.split()[0])
    return models


def is_model_installed(required: str, installed: list[str]) -> bool:
    if required in installed:
        return True
    if ":" not in required and f"{required}:latest" in installed:
        return True
    return False


def _clip(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def _clip_one_line(value: str, limit: int = 180) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return _clip(stripped, limit)
    return "ollama command failed"
