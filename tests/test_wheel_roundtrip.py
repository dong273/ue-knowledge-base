"""Installed-package round trip: build -> persist -> NEW PROCESS -> query.

Runs the full user loop against the packaged default corpus with the
deterministic FakeEmbedder — no model download needed, so it is CI-stable
for both source installs and fresh wheel installs.

The query step runs in a NEW Python process (subprocess), re-importing the
installed ``ue_knowledge`` package from site-packages — this proves the
wheel (not just the source tree) serves the corpus correctly, and that a
persisted index survives a process restart (the real user experience).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ue_knowledge import config
from ue_knowledge.build import build_index
from fake_embedder import FakeEmbedder

QUERY_SCRIPT = r"""
import json
import sys

from fake_embedder import FakeEmbedder
from ue_knowledge.query import query

db, q = sys.argv[1], sys.argv[2]
hits = query(q, top_k=3, chroma_dir=db, model_name="fake",
             embedder=FakeEmbedder())
print(json.dumps(hits, ensure_ascii=False))
"""


@pytest.fixture(scope="module")
def built_index(tmp_path_factory):
    """Persisted index built from the REAL bundled corpus (no model)."""
    db = tmp_path_factory.mktemp("chroma")
    summary = build_index(
        source_dir=config.DEFAULT_SOURCE_DIR,
        chroma_dir=db,
        model_name="fake",
        embedder=FakeEmbedder(),
    )
    assert summary["files"] == 86
    assert summary["chunks"] > summary["files"]
    return db


def _query_in_new_process(db: Path, text: str) -> list[dict]:
    env = {
        **os.environ,
        # expose tests/fake_embedder.py to the child process
        "PYTHONPATH": str(Path(__file__).parent),
        # the child prints Chinese hit text; force UTF-8 so the round trip
        # works identically on every locale (cp1252/gbk/utf-8)
        "PYTHONIOENCODING": "utf-8",
    }
    r = subprocess.run(
        [sys.executable, "-c", QUERY_SCRIPT, str(db), text],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=180,
    )
    assert r.returncode == 0, f"child failed:\n{r.stderr}"
    return json.loads(r.stdout)


def test_new_process_english_query_hits(built_index):
    hits = _query_in_new_process(built_index, "GAS ability cooldown")
    assert hits, "no results for English query"
    assert hits[0]["source"] and hits[0]["heading"]
    assert 0.0 < hits[0]["score"] <= 1.0


def test_new_process_chinese_query_hits(built_index):
    hits = _query_in_new_process(built_index, "技能 冷却")
    assert hits, "no results for Chinese query"
    assert hits[0]["source"] and hits[0]["heading"]
    assert 0.0 < hits[0]["score"] <= 1.0
