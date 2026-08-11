"""Unit tests for the markdown chunker (no external deps, runs anywhere)."""

from ue_knowledge.chunking import chunk_markdown

LONG = "word " * 60  # 300 chars — well above the 200-char merge threshold


def test_chunks_by_heading():
    doc = f"# Title\n\n{LONG}\n\n## Section A\n\n{LONG}\n\n### Sub\n\n{LONG}"
    chunks = chunk_markdown(doc, source="test.md", min_chars=10)
    assert len(chunks) == 3
    headings = [c["heading"] for c in chunks]
    assert headings[0] == "Title"
    assert headings[1] == "Section A"
    assert headings[2] == "Sub"
    assert chunks[0]["source"] == "test.md"


def test_tiny_chunks_merged():
    doc = f"# Big\n\n{LONG}\n\n## Tiny\n\nshort\n\n## Big2\n\n{LONG}"
    chunks = chunk_markdown(doc, source="t.md", min_chars=100)
    # "short" is below min_chars → dropped; only Big and Big2 become chunks
    assert len(chunks) == 2
    assert "Tiny" not in [c["heading"] for c in chunks]


def test_ids_unique():
    doc = f"# A\n\n{LONG}\n\n## B\n\n{LONG}"
    chunks = chunk_markdown(doc, source="u.md", min_chars=50)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
