"""Unit tests for the markdown chunker (no external deps, runs anywhere)."""

from ue_knowledge.chunking import chunk_markdown


def test_chunks_by_heading():
    doc = "# Title\n\nintro text that is long enough to count as a chunk\n\n## Section A\n\nbody text for section a that is long enough\n\n### Sub\n\nmore body text that is long enough"
    chunks = chunk_markdown(doc, source="test.md", min_chars=10)
    assert len(chunks) >= 3
    headings = [c["heading"] for c in chunks]
    assert "Title" in headings[0]
    assert "Section A" in headings
    assert chunks[0]["source"] == "test.md"


def test_tiny_chunks_merged():
    doc = "# Big\n\n" + "word " * 100 + "\n\n## Tiny\n\nshort\n\n## Big2\n\n" + "word " * 100
    chunks = chunk_markdown(doc, source="t.md", min_chars=100)
    assert len(chunks) == 1  # tiny middle chunk merged away


def test_ids_unique():
    doc = "# A\n\n" + "content " * 50 + "\n\n## B\n\n" + "content " * 50
    chunks = chunk_markdown(doc, source="u.md", min_chars=50)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
