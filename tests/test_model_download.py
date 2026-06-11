from ame.hardware.profiler import HardwareProfile
from ame.hardware.tier import Tier
from ame.models.download import OllamaModelInstaller
from ame.models.registry import ModelRegistry
from ame.models.router import ModelRouter


def _profile(*, ollama_installed: bool = True) -> HardwareProfile:
    return HardwareProfile(
        os="Darwin",
        machine="arm64",
        processor="Apple",
        total_ram_gb=16,
        disk_free_gb=100,
        ollama_installed=ollama_installed,
        mlx_available=False,
        tier=Tier.T1,
    )


def test_ollama_install_plan_uses_16gb_qwen3_defaults(monkeypatch) -> None:
    def get_json(url: str) -> dict:
        return {"models": [{"model": "qwen3:8b"}, {"model": "nomic-embed-text:latest"}]}

    monkeypatch.setattr("ame.models.download.shutil.which", lambda name: f"/bin/{name}")
    plan = ModelRouter(ModelRegistry()).plan(_profile())
    install = OllamaModelInstaller(get_json=get_json).install_plan(plan, _profile())

    assert install.tier == "T1"
    assert install.required_models == ["qwen3:8b", "nomic-embed-text"]
    assert install.installed_models == ["qwen3:8b", "nomic-embed-text:latest"]
    assert install.installed_models_source == "ollama_http"
    assert install.missing_models == []
    assert install.pull_commands == []


def test_ollama_pull_dry_run_and_execute(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    def post_json(url: str, payload: dict) -> dict:
        calls.append((url, payload))
        return {"status": "success"}

    monkeypatch.setattr("ame.models.download.shutil.which", lambda name: f"/bin/{name}")
    installer = OllamaModelInstaller(post_json=post_json)

    dry_run = installer.pull(["qwen3:8b"], execute=False)
    executed = installer.pull(["qwen3:8b"], execute=True)

    assert dry_run[0].status == "planned"
    assert calls == [("http://127.0.0.1:11434/api/pull", {"name": "qwen3:8b", "stream": False})]
    assert executed[0].status == "success"
    assert executed[0].transport == "ollama_http"


def test_ollama_pull_falls_back_to_cli_when_http_unavailable(monkeypatch) -> None:
    def post_json(url: str, payload: dict) -> dict:
        raise RuntimeError("ollama http is down")

    def runner(command: list[str]):
        class Result:
            returncode = 0
            stdout = "pulled"
            stderr = ""

        return Result()

    monkeypatch.setattr("ame.models.download.shutil.which", lambda name: f"/bin/{name}")
    installer = OllamaModelInstaller(runner=runner, post_json=post_json)

    executed = installer.pull(["qwen3:8b"], execute=True)

    assert executed[0].status == "success"
    assert executed[0].transport == "ollama_cli"
    assert executed[0].output == "pulled"


def test_ollama_install_plan_reports_http_error_without_cli_crash(monkeypatch) -> None:
    def get_json(url: str) -> dict:
        raise RuntimeError("native cli is not used")

    def runner(command: list[str]):
        raise AssertionError("ollama list should not be called by default")

    monkeypatch.setattr("ame.models.download.shutil.which", lambda name: f"/bin/{name}")
    plan = ModelRouter(ModelRegistry()).plan(_profile())
    install = OllamaModelInstaller(runner=runner, get_json=get_json).install_plan(plan, _profile())

    assert install.installed_models == []
    assert install.missing_models == ["qwen3:8b", "nomic-embed-text"]
    assert install.error
    assert "HTTP API" in install.error


def test_ollama_cli_list_error_is_summarized(monkeypatch) -> None:
    def get_json(url: str) -> dict:
        raise RuntimeError("http down")

    def runner(command: list[str]):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "WARNING: noisy native backtrace\n0   ollama stack frame\n1   more stack"

        return Result()

    monkeypatch.setattr("ame.models.download.shutil.which", lambda name: f"/bin/{name}")
    plan = ModelRouter(ModelRegistry()).plan(_profile())
    install = OllamaModelInstaller(runner=runner, get_json=get_json, allow_cli_list=True).install_plan(plan, _profile())

    assert install.error == "WARNING: noisy native backtrace"
