"""Default-path and packaged-corpus contract tests.

Pin the 0.4.1 packaging contract:

- the corpus ships INSIDE the installed package (package data), so
  ``pip install ue-knowledge-base`` works with no repo checkout;
- the default ChromaDB dir is a user-writable data directory (never
  inside site-packages / Python's Lib);
- override priority is CLI flag > env var > default;
- the released corpus snapshot: 86 markdown files, 1,455 unique chunks.

Snapshot numbers must be updated only when the corpus is deliberately
re-published (scripts/publish_from_hermes.py) and the wheel gate re-run.
"""

from pathlib import Path

import pytest

import ue_knowledge
from ue_knowledge import config
from ue_knowledge.build import build_index
from ue_knowledge.chunking import collect_markdown

# Released-corpus snapshot — see module docstring.
CORPUS_FILES = 86
CORPUS_CHUNKS = 1455


def test_package_version():
    assert ue_knowledge.__version__ == "0.4.1"


def test_default_source_dir_is_package_data():
    pkg = Path(ue_knowledge.__file__).resolve().parent
    assert config.DEFAULT_SOURCE_DIR == pkg / "knowledge"
    assert config.DEFAULT_SOURCE_DIR.is_dir()


def test_default_corpus_86_files_readable():
    files = sorted(config.DEFAULT_SOURCE_DIR.rglob("*.md"))
    assert len(files) == CORPUS_FILES
    for fp in files:
        text = fp.read_text(encoding="utf-8")
        assert text.strip(), f"empty file: {fp}"


def test_default_corpus_chunks_unique_count():
    docs = collect_markdown(config.DEFAULT_SOURCE_DIR)
    ids = [d["id"] for d in docs]
    assert len(docs) == CORPUS_CHUNKS
    assert len(set(ids)) == CORPUS_CHUNKS


def test_source_dir_priority(monkeypatch):
    monkeypatch.setenv("UE_KB_SOURCE", "C:/env-corpus")
    assert config.source_dir() == Path("C:/env-corpus")
    assert config.source_dir("C:/flag-corpus") == Path("C:/flag-corpus")
    monkeypatch.delenv("UE_KB_SOURCE")
    assert config.source_dir() == config.DEFAULT_SOURCE_DIR


def test_chroma_dir_priority(monkeypatch):
    monkeypatch.setenv("UE_KB_CHROMA_DIR", "C:/env-db")
    assert config.chroma_dir() == Path("C:/env-db")
    assert config.chroma_dir("C:/flag-db") == Path("C:/flag-db")
    monkeypatch.delenv("UE_KB_CHROMA_DIR")
    assert config.chroma_dir() == config.DEFAULT_CHROMA_DIR


def test_default_chroma_dir_is_user_writable_data_dir():
    d = config.DEFAULT_CHROMA_DIR
    # never inside the package or site-packages (wheel installs cannot
    # write there)
    pkg = Path(ue_knowledge.__file__).resolve().parent
    assert not str(d).lower().startswith(str(pkg).lower())
    assert "site-packages" not in str(d).lower()
    assert d.name == "chroma_db"
    assert d.parent.name == "ue-knowledge-base"


def test_build_missing_corpus_raises(tmp_path):
    missing = tmp_path / "no-such-corpus"
    with pytest.raises(FileNotFoundError):
        build_index(
            source_dir=missing,
            chroma_dir=tmp_path / "db",
            model_name="fake",
            embedder=object(),  # never reached: fails before model load
        )
