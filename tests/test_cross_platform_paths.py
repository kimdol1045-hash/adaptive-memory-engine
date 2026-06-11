from pathlib import Path

from ame.core.paths import default_ame_home


def test_default_ame_home_uses_macos_application_support(monkeypatch) -> None:
    monkeypatch.setattr("ame.core.paths.platform.system", lambda: "Darwin")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)

    assert str(default_ame_home()).endswith("Library/Application Support/ame")


def test_default_ame_home_uses_windows_local_appdata(monkeypatch) -> None:
    monkeypatch.setattr("ame.core.paths.platform.system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\andan\AppData\Local")

    assert default_ame_home() == Path(r"C:\Users\andan\AppData\Local") / "AdaptiveMemoryEngine"


def test_default_ame_home_uses_xdg_on_linux(monkeypatch) -> None:
    monkeypatch.setattr("ame.core.paths.platform.system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/home/andan/.local/share")

    assert default_ame_home() == Path("/home/andan/.local/share") / "ame"
