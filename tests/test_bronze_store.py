from ame.bronze.store import BronzeStore
from ame.connectors.obsidian import ObsidianConnector


def test_bronze_store_deduplicates_by_hash(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.md").write_text("# A\nOpenClaw uses LightRAG\n", encoding="utf-8")
    root = tmp_path / "corpus"
    connector = ObsidianConnector()
    doc = connector.load("openclaw", connector.scan(source)[0])
    store = BronzeStore(root)

    first = store.put(doc)
    second = store.put(doc)

    assert first.id == second.id
    assert len(list(store.list())) == 1
