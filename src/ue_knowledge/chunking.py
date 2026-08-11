"""Markdown chunking — split docs on heading boundaries into semantic chunks."""

import hashlib


def chunk_markdown(text: str, source: str, min_chars: int = 100, max_chars: int = 800) -> list[dict]:
    """Split markdown into chunks by heading boundaries.

    Returns a list of dicts: {id, text, source, heading}.
    """
    chunks = []
    lines = text.split("\n")
    buffer = []
    buffer_heading = "前言"

    def flush():
        nonlocal buffer, buffer_heading
        chunk_text = "\n".join(buffer).strip()
        if len(chunk_text) >= min_chars:
            chunks.append({
                "text": chunk_text,
                "source": source,
                "heading": buffer_heading,
                "id": hashlib.md5(
                    f"{source}:{buffer_heading}:{chunk_text[:50]}".encode()
                ).hexdigest() + f":{len(chunks)}",
            })

    for line in lines:
        if line.startswith(("## ", "### ", "# ")):
            flush()
            buffer_heading = line.lstrip("#").strip()
            buffer = [line]
        else:
            buffer.append(line)

    flush()

    # Merge tiny chunks into their predecessor so the index stays useful.
    merged = []
    for c in chunks:
        if merged and len(c["text"]) < 200:
            merged[-1]["text"] += "\n\n" + c["text"]
            merged[-1]["heading"] += " / " + c["heading"]
        else:
            merged.append(c)

    return merged


def collect_markdown(source_dir, min_chars: int = 100) -> list[dict]:
    """Recursively read all .md files under source_dir into chunks."""
    documents = []
    files = sorted(source_dir.rglob("*.md"))
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = fp.relative_to(source_dir)
        documents.extend(chunk_markdown(text, source=str(rel), min_chars=min_chars))
    return documents
