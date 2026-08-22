"""0.5 contracts for Markdown-aware, token-bounded chunking."""

from ue_knowledge.chunking import CHUNKER_VERSION, chunk_markdown, token_count


def test_chunks_are_token_bounded_with_overlap_and_heading_path():
    body = " ".join(f"token{i}" for i in range(900))
    doc = f"# Root\n\n## Long Section\n\n{body}\n"

    chunks = chunk_markdown(
        doc,
        source="topic\\doc.md",
        min_chars=1,
        max_tokens=384,
        overlap_tokens=48,
    )

    assert CHUNKER_VERSION == "2"
    assert len(chunks) >= 3
    assert all(token_count(chunk["text"]) <= 384 for chunk in chunks)
    assert all(chunk["source"] == "topic/doc.md" for chunk in chunks)
    assert all(chunk["heading"] == "Root / Long Section" for chunk in chunks)
    assert "token0" in chunks[0]["text"]
    assert "token899" in chunks[-1]["text"]
    assert set(chunks[0]["text"].split()) & set(chunks[1]["text"].split())


def test_heading_inside_fence_does_not_split_section():
    doc = """# Root

Before the example.

```cpp
# Not a heading
## Still code
void Tick() {}
```

After the example.

## Real Section

Real body.
"""

    chunks = chunk_markdown(doc, source="code.md", min_chars=1)

    assert [chunk["heading"] for chunk in chunks] == ["Root", "Root / Real Section"]
    assert "# Not a heading" in chunks[0]["text"]
    assert "## Still code" in chunks[0]["text"]
    assert chunks[0]["text"].count("```") == 2


def test_chunk_ids_use_normalized_path_heading_and_full_content():
    text = "# Root\n\n" + ("stable content " * 20)
    first = chunk_markdown(text, source="topic\\doc.md", min_chars=1)
    second = chunk_markdown(text, source="topic/doc.md", min_chars=1)
    edited = chunk_markdown(text + "changed", source="topic/doc.md", min_chars=1)

    assert first[0]["id"] == second[0]["id"]
    assert first[0]["id"] != edited[0]["id"]


def test_chunk_content_has_complete_non_overlap_coverage():
    body = " ".join(f"unique{i}" for i in range(800))
    chunks = chunk_markdown(
        f"# Coverage\n\n{body}",
        source="coverage.md",
        min_chars=1,
        max_tokens=128,
        overlap_tokens=16,
    )

    combined = " ".join(chunk["text"] for chunk in chunks)
    assert all(f"unique{i}" in combined for i in range(800))


def test_persisted_window_is_rechecked_after_contextual_tokenization():
    class ContextualTokenizer:
        def __call__(self, text, **_kwargs):
            words = list(__import__("re").finditer(r"\S+", text))
            offsets = [match.span() for match in words]
            # Simulate WordPiece creating one extra token only after a window
            # is detached from its original context.
            if text.startswith("token") and len(words) >= 8:
                offsets.append(offsets[-1])
            return {"offset_mapping": offsets}

    tokenizer = ContextualTokenizer()
    chunks = chunk_markdown(
        "# Root\n\n" + " ".join(f"token{i}" for i in range(30)),
        source="context.md",
        min_chars=1,
        max_tokens=8,
        overlap_tokens=2,
        tokenizer=tokenizer,
    )
    assert all(token_count(chunk["text"], tokenizer) <= 8 for chunk in chunks)
    assert "token29" in chunks[-1]["text"]


def test_oversized_code_fence_is_balanced_in_every_chunk():
    code = "\n".join(f"int value_{index} = {index};" for index in range(300))
    chunks = chunk_markdown(
        f"# Code\n\n```cpp\n{code}\n```\n",
        source="code.md",
        min_chars=1,
        max_tokens=64,
        overlap_tokens=8,
    )
    assert len(chunks) > 2
    assert all(token_count(chunk["text"]) <= 64 for chunk in chunks)
    assert all(chunk["text"].count("```") % 2 == 0 for chunk in chunks)
    assert "value_0" in chunks[0]["text"]
    assert "value_299" in chunks[-1]["text"]


def test_frontmatter_chunks_are_typed_with_stable_ids():
    """YAML frontmatter is flagged as type=frontmatter without changing ids.

    Chunk ids are sha256(source + heading + text) and must not absorb the
    new type field, so 0.6.2 indexes stay valid and rebuilds reuse ids.
    """
    import hashlib

    doc = (
        "---\n"
        "title: ue-test\n"
        "description: alpha beta gamma\n"
        "---\n\n"
        "# Head\n\n"
        "body text here\n"
    )
    chunks = chunk_markdown(doc, source="topic/doc.md")
    assert [chunk["type"] for chunk in chunks] == ["frontmatter", "content"]
    frontmatter = chunks[0]
    digest = hashlib.sha256(
        f"topic/doc.md\0前言\0{frontmatter['text']}".encode("utf-8")
    ).hexdigest()
    assert frontmatter["id"] == digest
    assert frontmatter["heading"] == "前言"


def test_preface_without_frontmatter_is_content():
    doc = "intro paragraph\n\n# Head\n\nbody\n"
    chunks = chunk_markdown(doc, source="doc.md")
    assert chunks and all(chunk["type"] == "content" for chunk in chunks)
