"""Schema-v2 generation and hybrid retrieval regression tests."""

import json

import pytest

from fake_embedder import FakeEmbedder
from ue_knowledge.build import build_index
from ue_knowledge.index_store import INDEX_SCHEMA_VERSION, IndexSchemaMismatch, load_current
from ue_knowledge.query import query


@pytest.fixture
def movement_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    topic = corpus / "ue-character-movement"
    topic.mkdir(parents=True)
    (topic / "movement.md").write_text(
        "# Character Movement\n\n"
        + ("CharacterMovementComponent movement speed braking deceleration " * 30),
        encoding="utf-8",
    )
    other = corpus / "ue-niagara-effects"
    other.mkdir()
    (other / "particles.md").write_text(
        "# Niagara\n\n" + ("particle emitter GPU simulation " * 30),
        encoding="utf-8",
    )
    return corpus


def test_build_activates_valid_generation_manifest(movement_corpus, tmp_path):
    db = tmp_path / "index"
    summary = build_index(
        source_dir=movement_corpus,
        chroma_dir=db,
        model_name="fake",
        embedder=FakeEmbedder(),
    )

    generation = load_current(db)
    manifest = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
    assert (db / "CURRENT").read_text(encoding="utf-8").strip() == generation.name
    assert manifest["schema_version"] == INDEX_SCHEMA_VERSION == 2
    assert manifest["embedding"]["model"] == "fake"
    assert manifest["embedding"]["dimension"] == 64
    assert manifest["chunker"]["max_tokens"] == 384
    assert manifest["chunker"]["overlap_tokens"] == 48
    assert manifest["corpus"]["sha256"]
    assert manifest["corpus"]["documents"] == 2
    assert manifest["corpus"]["chunks"] == summary["chunks"]
    assert (generation / "bm25.json").is_file()


def test_append_is_sync_and_removes_stale_chunks(movement_corpus, tmp_path):
    db = tmp_path / "index"
    build_index(
        source_dir=movement_corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )

    (movement_corpus / "ue-niagara-effects" / "particles.md").unlink()
    movement = movement_corpus / "ue-character-movement" / "movement.md"
    movement.write_text(
        "# Character Movement\n\n" + ("stamina speed decay braking " * 30),
        encoding="utf-8",
    )
    summary = build_index(
        source_dir=movement_corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(), append=True,
    )

    assert summary["removed"] > 0
    assert query(
        "stamina speed decay", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(), profile="hybrid",
    )[0]["source"].endswith("movement.md")
    assert all(
        "particles.md" not in hit["source"]
        for hit in query(
            "particle emitter", top_k=5, chroma_dir=db,
            model_name="fake", embedder=FakeEmbedder(), profile="hybrid",
        )
    )


class FailOnSecondBatch(FakeEmbedder):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def encode(self, texts, **kwargs):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("injected second batch failure")
        return super().encode(texts, **kwargs)


def test_failed_rebuild_keeps_old_generation_queryable(movement_corpus, tmp_path):
    db = tmp_path / "index"
    build_index(
        source_dir=movement_corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    old_generation = (db / "CURRENT").read_text(encoding="utf-8")

    large = movement_corpus / "ue-character-movement" / "large.md"
    large.write_text(
        "\n".join(
            f"## Section {i}\n\n" + (f"unique{i} movement " * 20)
            for i in range(80)
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="second batch"):
        build_index(
            source_dir=movement_corpus, chroma_dir=db,
            model_name="fake", embedder=FailOnSecondBatch(), force=True,
        )

    assert (db / "CURRENT").read_text(encoding="utf-8") == old_generation
    assert query(
        "movement speed", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )


def test_manifest_rejects_same_dimension_different_model(movement_corpus, tmp_path):
    db = tmp_path / "index"
    build_index(
        source_dir=movement_corpus, chroma_dir=db,
        model_name="fake-a", embedder=FakeEmbedder(),
    )

    with pytest.raises(IndexSchemaMismatch) as caught:
        query(
            "movement", chroma_dir=db,
            model_name="fake-b", embedder=FakeEmbedder(),
        )
    assert caught.value.code == "INDEX_SCHEMA_MISMATCH"
    assert "--force" in caught.value.action


def test_legacy_index_returns_rebuild_instruction(tmp_path):
    db = tmp_path / "legacy"
    db.mkdir()
    (db / "chroma.sqlite3").write_bytes(b"legacy")

    with pytest.raises(IndexSchemaMismatch) as caught:
        query(
            "movement", chroma_dir=db,
            model_name="fake", embedder=FakeEmbedder(),
        )
    assert caught.value.code == "INDEX_SCHEMA_MISMATCH"
    assert caught.value.action == "ue-kb build --force"


def test_hybrid_expands_chinese_ue_terms(movement_corpus, tmp_path):
    db = tmp_path / "index"
    build_index(
        source_dir=movement_corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )

    results = query(
        "角色移动 速度衰减", top_k=3, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(), profile="hybrid",
    )
    assert results[0]["source"].startswith("ue-character-movement/")
    vector = query(
        "movement speed", top_k=1, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(), profile="vector",
    )
    assert vector[0]["source"].startswith("ue-character-movement/")


def test_hybrid_deduplicates_by_source_and_heading(tmp_path):
    corpus = tmp_path / "corpus"
    topic = corpus / "ue-character-movement"
    topic.mkdir(parents=True)
    (topic / "many.md").write_text(
        "\n".join(
            f"## Movement {index}\n\n" + ("movement speed braking " * 20)
            for index in range(5)
        ),
        encoding="utf-8",
    )
    (topic / "other.md").write_text(
        "# Other\n\n" + ("movement prediction network " * 20),
        encoding="utf-8",
    )
    db = tmp_path / "index"
    build_index(
        source_dir=corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )

    results = query(
        "角色移动", top_k=5, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(), profile="hybrid",
    )
    # Dedup is at (source, heading) granularity: distinct sections of the
    # same file may all surface, but an exact (source, heading) pair never
    # repeats.
    keys = [(result["source"], result["heading"]) for result in results]
    assert len(keys) == len(set(keys))
    # Each hit carries cross-query-comparable raw_score and a 1-based rank.
    assert all(result["raw_score"] > 0 for result in results)
    assert [result["rank"] for result in results] == list(range(1, len(results) + 1))
    # The strongest section of many.md is present, not collapsed away.
    assert any(source.endswith("many.md") for source, _ in keys)
