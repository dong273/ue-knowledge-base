"""End-to-end integration test: build -> query, no network, no model download.

Uses a deterministic fake embedder so the full ChromaDB pipeline
(build index -> persist -> reload -> semantic query) is exercised in CI
without touching HuggingFace or downloading the ~100MB BGE model.
"""

import pytest

from ue_knowledge.build import build_index
from ue_knowledge.query import query

from fake_embedder import FakeEmbedder


@pytest.fixture
def corpus(tmp_path):
    d = tmp_path / "corpus"
    (d / "topic").mkdir(parents=True)
    (d / "topic" / "doc.md").write_text(
        "# GAS\n\n"
        + ("cooldown ability gameplay attribute " * 20)
        + "\n\n## Jump\n\n"
        + ("jump movement input momentum " * 20),
        encoding="utf-8",
    )
    (d / "topic" / "second.md").write_text(
        "# Niagara\n\n" + ("particle system emitter GPU " * 20),
        encoding="utf-8",
    )
    return d


def test_build_query_roundtrip(corpus, tmp_path):
    """build_index then query against a fresh persisted collection."""
    db = tmp_path / "chroma"
    summary = build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    assert summary["chunks"] >= 3
    assert summary["collection"] == "ue_knowledge"

    # semantic query for the GAS chunk
    results = query(
        "cooldown ability", top_k=2, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert len(results) >= 1
    assert "doc.md" in results[0]["source"]
    assert 0.0 < results[0]["score"] <= 1.0

    # query for the Niagara chunk
    results = query(
        "particle emitter", top_k=2, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert "second.md" in results[0]["source"]


def test_rebuild_force(corpus, tmp_path):
    """--force semantics: rebuild wipes and re-indexes."""
    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    summary = build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), force=True,
    )
    assert summary["chunks"] >= 3


def test_rebuild_without_force_raises(corpus, tmp_path):
    """Existing non-empty index refuses rebuild unless force/append."""
    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    with pytest.raises(RuntimeError):
        build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())


def test_append_only_adds_new_chunks(corpus, tmp_path):
    """--append is a snapshot sync; repeated syncs are idempotent."""
    import chromadb

    from ue_knowledge.config import chroma_settings
    from ue_knowledge.index_store import load_current

    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    client = chromadb.PersistentClient(
        path=str(load_current(db) / "chroma"), settings=chroma_settings()
    )
    col = client.get_collection("ue_knowledge")
    n1 = col.count()

    # add a new document to the corpus
    (corpus / "topic" / "new.md").write_text(
        "# New Topic\n\n" + ("brand new content words " * 20),
        encoding="utf-8",
    )
    summary = build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    client = chromadb.PersistentClient(
        path=str(load_current(db) / "chroma"), settings=chroma_settings()
    )
    n2 = client.get_collection("ue_knowledge").count()
    assert n2 > n1
    assert summary["added"] > 0

    # idempotent: appending again adds nothing
    summary = build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    current = chromadb.PersistentClient(
        path=str(load_current(db) / "chroma"), settings=chroma_settings()
    )
    assert current.get_collection("ue_knowledge").count() == n2
    assert summary["added"] == 0
    assert summary["removed"] == 0

    # the new doc is queryable
    results = query(
        "brand new content", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert "new.md" in results[0]["source"]


def test_append_syncs_edited_content(corpus, tmp_path):
    """A content edit replaces old chunk ids and is queryable after sync."""
    import chromadb

    from ue_knowledge.config import chroma_settings
    from ue_knowledge.index_store import load_current

    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    client = chromadb.PersistentClient(
        path=str(load_current(db) / "chroma"), settings=chroma_settings()
    )
    n1 = client.get_collection("ue_knowledge").count()

    # Replace existing body content so the old chunk ids become stale.
    doc = corpus / "topic" / "doc.md"
    doc.write_text(
        "# GAS\n\n" + ("cooldown ability gameplay attribute " * 20)
        + "\n\n## Jump\n\n"
        + ("stamina drain movement speed decay " * 20),
        encoding="utf-8",
    )
    summary = build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    current = chromadb.PersistentClient(
        path=str(load_current(db) / "chroma"), settings=chroma_settings()
    )
    n2 = current.get_collection("ue_knowledge").count()
    assert n2 >= n1
    assert summary["added"] > 0
    assert summary["removed"] > 0

    # the merged-in content is actually queryable
    results = query(
        "stamina drain movement speed", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert "doc.md" in results[0]["source"]


def test_demote_frontmatter_reorders_but_keeps_membership(corpus, tmp_path):
    """demote_frontmatter is presentation-only: same hits, same raw scores.

    Content chunks are listed before topic-summary (frontmatter) chunks;
    RRF fusion itself is untouched, so default queries stay byte-identical.
    """
    (corpus / "topic" / "meta.md").write_text(
        "---\n"
        "title: meta\n"
        "description: cooldown ability gameplay attribute summary\n"
        "---\n\n"
        "# Meta Doc\n\nSee also cooldown ability gameplay attribute.\n",
        encoding="utf-8",
    )
    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    kwargs = dict(top_k=8, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())

    plain = query("cooldown ability gameplay attribute", **kwargs)
    demoted = query("cooldown ability gameplay attribute", demote_frontmatter=True, **kwargs)

    keys = {(hit["source"], hit["heading"]) for hit in plain}
    assert keys == {(hit["source"], hit["heading"]) for hit in demoted}
    frontmatter = [hit for hit in demoted if hit["type"] == "frontmatter"]
    content = [hit for hit in demoted if hit["type"] == "content"]
    assert frontmatter and content
    assert max(demoted.index(hit) for hit in content) < min(demoted.index(hit) for hit in frontmatter)
    # ranks are recomputed after demotion and stay 1..n
    assert [hit["rank"] for hit in demoted] == list(range(1, len(demoted) + 1))
    # per-hit fusion scores are untouched by the reordering
    raw_plain = {(hit["source"], hit["heading"]): hit["raw_score"] for hit in plain}
    for hit in demoted:
        assert raw_plain[(hit["source"], hit["heading"])] == hit["raw_score"]
