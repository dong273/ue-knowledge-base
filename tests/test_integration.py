"""End-to-end integration test: build -> query, no network, no model download.

Uses a deterministic fake embedder so the full ChromaDB pipeline
(build index -> persist -> reload -> semantic query) is exercised in CI
without touching HuggingFace or downloading the ~100MB BGE model.
"""

import hashlib
import math

import numpy as np
import pytest

from ue_knowledge.build import build_index
from ue_knowledge.query import query

DIM = 8


class FakeEmbedder:
    """Deterministic bag-of-words embedder: words map to fixed dimensions.

    Texts sharing words get similar vectors (like a real semantic embedder),
    so query -> hit assertions are meaningful, not random.
    """

    def __init__(self):
        self.max_seq_length = 512

    def get_sentence_embedding_dimension(self) -> int:
        return DIM

    def encode(self, texts, **kwargs):
        out = []
        for t in texts:
            v = [0.0] * DIM
            for word in t.lower().split():
                idx = hashlib.md5(word.encode("utf-8")).digest()[0] % DIM
                v[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in v))
            out.append([x / norm for x in v] if norm > 0 else v)
        return np.asarray(out, dtype=np.float32)


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
