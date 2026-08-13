"""Stability guards: orphan-generation sweep and build locking."""

import os
import time
from pathlib import Path

import pytest

from ue_knowledge.build import build_index
from ue_knowledge.index_store import (
    load_current,
    new_generation,
    sweep_incomplete,
)

from fake_embedder import FakeEmbedder


def _corpus(tmp_path):
    directory = tmp_path / "corpus"
    directory.mkdir()
    (directory / "doc.md").write_text(
        "# Topic\n\n" + ("movement speed braking " * 30), encoding="utf-8"
    )
    return directory


def _age(path: Path, seconds: float) -> None:
    stamp = time.time() - seconds
    os.utime(path, (stamp, stamp))


def test_sweep_removes_only_old_building_generations(tmp_path):
    root = tmp_path / "db"
    root.mkdir()
    fresh = new_generation(root)
    stale = new_generation(root)
    _age(stale / "BUILDING", 25 * 3600)

    removed = sweep_incomplete(root, max_age_seconds=24 * 3600)

    assert removed == [stale.name]
    assert fresh.is_dir()          # young BUILDING must survive
    assert not stale.exists()      # abandoned BUILDING must be reclaimed


def test_sweep_ignores_complete_generations(tmp_path):
    root = tmp_path / "db"
    root.mkdir()
    generation = new_generation(root)
    (generation / "BUILDING").unlink()  # completed build

    assert sweep_incomplete(root, max_age_seconds=0) == []


def test_sweep_reclaims_failed_marker_generations(tmp_path):
    root = tmp_path / "db"
    root.mkdir()
    failed = new_generation(root)
    (failed / "BUILDING").unlink()  # partial rmtree ate BUILDING...
    (failed / "FAILED").write_text("failed\n", encoding="ascii")
    _age(failed / "FAILED", 25 * 3600)

    assert sweep_incomplete(root, max_age_seconds=24 * 3600) == [failed.name]


def test_build_lock_blocks_concurrent_build(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    foreign = db / ".build.lock"
    foreign.write_text("pid=1\n", encoding="ascii")

    with pytest.raises(RuntimeError, match="另一个 ue-kb build"):
        build_index(
            source_dir=corpus, chroma_dir=db, model_name="fake",
            embedder=FakeEmbedder(), force=True,
        )
    # A foreign (possibly still-running) lock must NOT be deleted by us.
    assert foreign.exists()


def test_stale_lock_is_replaced_and_released(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    stale = db / ".build.lock"
    stale.write_text("pid=1\n", encoding="ascii")
    _age(stale, 2 * 3600)

    build_index(
        source_dir=corpus, chroma_dir=db, model_name="fake",
        embedder=FakeEmbedder(), force=True,
    )
    assert not (db / ".build.lock").exists()  # released after the build


def test_build_lock_removed_on_failure(tmp_path):
    corpus = _corpus(tmp_path)
    db = tmp_path / "db"

    class Broken(FakeEmbedder):
        def encode(self, texts, **kwargs):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        build_index(
            source_dir=corpus, chroma_dir=db, model_name="fake",
            embedder=Broken(), force=True,
        )
    # The lock MUST be released so the next build can proceed. Any leftover
    # generation must still carry BUILDING or FAILED (never mistaken for a
    # complete generation); the age-bounded sweep reclaims it later.
    assert not (db / ".build.lock").exists()
    generations = db / "generations"
    if generations.exists():
        for leftover in generations.iterdir():
            assert (leftover / "BUILDING").exists() or (leftover / "FAILED").exists()


def test_legacy_content_ignores_build_lock(tmp_path):
    root = tmp_path / "db"
    root.mkdir()
    (root / ".build.lock").write_text("pid=1\n", encoding="ascii")
    with pytest.raises(FileNotFoundError):
        # Must be "index not found" (build first), not a schema-mismatch error.
        load_current(root)
