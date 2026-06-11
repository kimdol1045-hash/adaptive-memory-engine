import json
from pathlib import Path

from typer.testing import CliRunner

from ame.bronze.store import BronzeStore
from ame.cli.main import app
from ame.connectors.router import ConnectorRouter
from ame.connectors.sync_history import ConnectorSyncStore
from ame.core.corpus import create_corpus, require_corpus
from ame.core.paths import ensure_runtime_layout


def test_export_connector_runtime_contract_diff_and_sync(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("contract")
    notes = tmp_path / "notes"
    notes.mkdir()
    source = notes / "decision.md"
    source.write_text("# Decision\nHermes decided to use Adaptive Memory Engine.\n", encoding="utf-8")

    runtime = ConnectorRouter().runtime(notes, "markdown")
    connection = runtime.connect(notes)
    refs = runtime.fetch(notes)
    doc = runtime.normalize_to_bronze("contract", refs[0])
    initial_diff = runtime.diff("contract", notes)

    assert connection.profile.name == "markdown"
    assert len(refs) == 1
    assert doc.source_type == "markdown"
    assert initial_diff.counts["new"] == 1
    assert initial_diff.counts["unchanged"] == 0

    report = runtime.sync("contract", notes)
    after_sync = runtime.diff("contract", notes)

    assert report.fetched == 1
    assert report.new == 1
    assert report.sync_run_id
    assert after_sync.counts["new"] == 0
    assert after_sync.counts["unchanged"] == 1
    assert len(list(BronzeStore(require_corpus("contract")).list())) == 1
    assert ConnectorSyncStore(require_corpus("contract")).latest(connector="markdown") is not None

    source.write_text("# Decision\nHermes decided to use Adaptive Memory Engine and Slack OAuth.\n", encoding="utf-8")
    changed_diff = runtime.diff("contract", notes)

    assert changed_diff.counts["changed"] == 1


def test_connector_profiles_and_cli_diff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AME_HOME", str(tmp_path / ".ame"))
    ensure_runtime_layout()
    create_corpus("contract-cli")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "decision.md").write_text("# Decision\nHermes decided to keep connector profiles versioned.\n", encoding="utf-8")
    runner = CliRunner()

    profiles = runner.invoke(app, ["connectors", "profiles"])
    diff = runner.invoke(app, ["connectors", "diff", "contract-cli", str(notes), "--profile", "markdown"])

    assert profiles.exit_code == 0
    assert "slack-oauth" in profiles.output
    assert diff.exit_code == 0
    payload = json.loads(diff.output)
    assert payload["connector"] == "markdown"
    assert payload["counts"]["new"] == 1
