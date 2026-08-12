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
    """--append semantics: only new chunk ids are indexed; idempotent."""
    import chromadb

    from ue_knowledge.config import chroma_settings

    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    client = chromadb.PersistentClient(path=str(db), settings=chroma_settings())
    col = client.get_collection("ue_knowledge")
    n1 = col.count()

    # add a new document to the corpus
    (corpus / "topic" / "new.md").write_text(
        "# New Topic\n\n" + ("brand new content words " * 20),
        encoding="utf-8",
    )
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    n2 = client.get_collection("ue_knowledge").count()
    assert n2 > n1

    # idempotent: appending again adds nothing
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    assert client.get_collection("ue_knowledge").count() == n2

    # the new doc is queryable
    results = query(
        "brand new content", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert "new.md" in results[0]["source"]


def test_append_indexes_content_merged_into_existing_chunk(corpus, tmp_path):
    """Regression: a short new section (< 200 chars) gets merged into an
    existing chunk; the merged chunk must be re-id'd, otherwise --append
    silently drops the new content from the index."""
    import chromadb

    from ue_knowledge.config import chroma_settings

    db = tmp_path / "chroma"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    client = chromadb.PersistentClient(path=str(db), settings=chroma_settings())
    n1 = client.get_collection("ue_knowledge").count()

    # ~140 chars: passes min_chars but stays under the 200-char merge threshold
    doc = corpus / "topic" / "doc.md"
    doc.write_text(
        doc.read_text(encoding="utf-8")
        + "\n## NewShort\n\nshort but meaningful addition about stamina drain "
        + "and movement speed decay that gets absorbed into the previous chunk\n",
        encoding="utf-8",
    )
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), append=True,
    )
    n2 = client.get_collection("ue_knowledge").count()
    assert n2 > n1

    # the merged-in content is actually queryable
    results = query(
        "stamina drain movement speed", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    assert "doc.md" in results[0]["source"]
