"""Markdown-aware, token-bounded corpus chunking."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

CHUNKER_VERSION = "2"
DEFAULT_MAX_TOKENS = 384
DEFAULT_OVERLAP_TOKENS = 48

_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u9fff]|[^\s]", re.UNICODE)


def _token_spans(text: str, tokenizer=None) -> list[tuple[int, int]]:
    """Return embedding-token character offsets when a fast tokenizer exists.

    The deterministic regex fallback keeps unit tests and corpus inspection
    dependency-free. Production builds pass the embedding model tokenizer, so
    the 384-token limit is measured in the model's own token space.
    """
    if tokenizer is not None:
        try:
            encoded = tokenizer(
                text,
                add_special_tokens=False,
                return_offsets_mapping=True,
                truncation=False,
                verbose=False,
            )
            offsets = encoded["offset_mapping"]
            if offsets and isinstance(offsets[0], list):
                offsets = offsets[0]
            spans = [(int(start), int(end)) for start, end in offsets if end > start]
            if spans:
                return spans
        except (KeyError, TypeError, ValueError, NotImplementedError):
            pass
    return [match.span() for match in _TOKEN_RE.finditer(text)]


def token_count(text: str, tokenizer=None) -> int:
    """Count tokens with the embedding tokenizer or the local fallback."""
    return len(_token_spans(text, tokenizer))


def _normalized_source(source: str) -> str:
    return PurePosixPath(source.replace("\\", "/")).as_posix()


def _sections(text: str) -> list[tuple[str, str]]:
    """Split on real Markdown headings while ignoring headings in fences."""
    sections: list[tuple[str, str]] = []
    heading_stack: list[str] = []
    current_heading = "前言"
    buffer: list[str] = []
    fence_marker: str | None = None

    def flush() -> None:
        nonlocal buffer
        raw = "".join(buffer).strip()
        if raw:
            sections.append((current_heading, raw))
        buffer = []

    for line in text.splitlines(keepends=True):
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            marker_char = marker[0]
            if fence_marker is None:
                fence_marker = marker
            elif marker_char == fence_marker[0] and len(marker) >= len(fence_marker):
                fence_marker = None
            buffer.append(line)
            continue

        heading = _HEADING_RE.match(line.rstrip("\r\n")) if fence_marker is None else None
        if not heading:
            buffer.append(line)
            continue

        flush()
        level = len(heading.group(1))
        title = heading.group(2).strip()
        heading_stack[level - 1 :] = []
        while len(heading_stack) < level - 1:
            heading_stack.append("")
        heading_stack.append(title)
        current_heading = " / ".join(part for part in heading_stack if part)
        buffer = [line]

    flush()
    return sections


def _has_body(section: str) -> bool:
    """Do not emit chunks for a heading with no body of its own."""
    lines = section.splitlines()
    if lines and _HEADING_RE.match(lines[0]):
        lines = lines[1:]
    return bool("\n".join(lines).strip())


def _fenced_token_ranges(text: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return half-open token ranges occupied by complete fenced blocks."""
    char_ranges: list[tuple[int, int]] = []
    marker: str | None = None
    start = 0
    cursor = 0
    for line in text.splitlines(keepends=True):
        match = _FENCE_RE.match(line)
        if match:
            found = match.group(1)
            if marker is None:
                marker = found
                start = cursor
            elif found[0] == marker[0] and len(found) >= len(marker):
                char_ranges.append((start, cursor + len(line)))
                marker = None
        cursor += len(line)

    ranges: list[tuple[int, int]] = []
    for char_start, char_end in char_ranges:
        indexes = [
            index for index, (token_start, token_end) in enumerate(spans)
            if token_end > char_start and token_start < char_end
        ]
        if indexes:
            ranges.append((indexes[0], indexes[-1] + 1))
    return ranges


def _fence_state_at(text: str, position: int) -> tuple[str, str] | None:
    """Return (opening line, marker) when ``position`` is inside a fence."""
    active: tuple[str, str] | None = None
    cursor = 0
    for line in text.splitlines(keepends=True):
        if cursor >= position:
            break
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if active is None:
                active = (line.rstrip("\r\n"), marker)
            elif marker[0] == active[1][0] and len(marker) >= len(active[1]):
                active = None
        cursor += len(line)
    return active


def _render_window(
    text: str,
    spans: list[tuple[int, int]],
    start: int,
    end: int,
) -> str:
    """Render a token window with balanced fences for split code blocks."""
    char_start = spans[start][0]
    char_end = spans[end - 1][1]
    rendered = text[char_start:char_end].strip()
    start_fence = _fence_state_at(text, char_start)
    end_fence = _fence_state_at(text, char_end)
    if start_fence is not None:
        rendered = f"{start_fence[0]}\n{rendered}"
    if end_fence is not None:
        rendered = f"{rendered}\n{end_fence[1]}"
    return rendered


def _windows(
    total: int,
    max_tokens: int,
    overlap_tokens: int,
    protected: list[tuple[int, int]],
    text: str | None = None,
    spans: list[tuple[int, int]] | None = None,
    tokenizer=None,
) -> list[tuple[int, int]]:
    """Build covering token windows, keeping normal-size code blocks whole."""
    if total <= max_tokens:
        return [(0, total)]

    windows: list[tuple[int, int]] = []
    start = 0
    while start < total:
        end = min(start + max_tokens, total)
        if end < total:
            for block_start, block_end in protected:
                if block_start < end < block_end and block_end - block_start <= max_tokens:
                    end = block_start if block_start > start else block_end
                    break
        if end <= start:
            end = min(start + max_tokens, total)
        # WordPiece boundaries can change when an offset window becomes a
        # standalone string (rarely adding one token). Re-tokenize the exact
        # persisted text and shrink before committing the window.
        if text is not None and spans is not None:
            while end > start:
                candidate = _render_window(text, spans, start, end)
                if token_count(candidate, tokenizer) <= max_tokens:
                    break
                end -= 1
            if end <= start:
                raise RuntimeError("cannot create a non-empty token-bounded chunk")
        windows.append((start, end))
        if end == total:
            break
        next_start = max(0, end - overlap_tokens)
        for block_start, block_end in protected:
            if block_start < next_start < block_end and block_end <= end:
                next_start = block_end
                break
        start = next_start if next_start > start else end

    # A gap here means content would be silently lost; fail the build loudly.
    covered_until = 0
    for window_start, window_end in windows:
        if window_start > covered_until:
            raise RuntimeError(
                f"chunk coverage gap: tokens {covered_until}:{window_start}"
            )
        covered_until = max(covered_until, window_end)
    if covered_until != total:
        raise RuntimeError(f"chunk coverage ended at {covered_until}, expected {total}")
    return windows


def chunk_markdown(
    text: str,
    source: str,
    min_chars: int = 1,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    tokenizer=None,
    **legacy,
) -> list[dict]:
    """Split Markdown into stable, heading-aware, token-bounded chunks.

    ``max_chars`` from 0.4 is accepted but ignored so callers get the v2 token
    contract without a flag-day API break.
    """
    legacy.pop("max_chars", None)
    if legacy:
        raise TypeError(f"unexpected chunking options: {', '.join(legacy)}")
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be >= 0 and < max_tokens")

    normalized_source = _normalized_source(source)
    chunks: list[dict] = []
    for heading, section in _sections(text):
        if not _has_body(section):
            continue
        body = section.split("\n", 1)[1] if _HEADING_RE.match(section.splitlines()[0]) and "\n" in section else section
        if len(body.strip()) < min_chars:
            continue

        spans = _token_spans(section, tokenizer)
        if not spans:
            continue
        protected = _fenced_token_ranges(section, spans)
        for start, end in _windows(
            len(spans), max_tokens, overlap_tokens, protected,
            text=section, spans=spans, tokenizer=tokenizer,
        ):
            chunk_text = _render_window(section, spans, start, end)
            digest = hashlib.sha256(
                f"{normalized_source}\0{heading}\0{chunk_text}".encode("utf-8")
            ).hexdigest()
            chunks.append(
                {
                    "id": digest,
                    "text": chunk_text,
                    "source": normalized_source,
                    "heading": heading,
                }
            )
    return chunks


def collect_markdown(
    source_dir: Path,
    min_chars: int = 1,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    tokenizer=None,
) -> list[dict]:
    """Recursively read every Markdown file under ``source_dir``."""
    documents: list[dict] = []
    for path in sorted(source_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        relative = path.relative_to(source_dir).as_posix()
        documents.extend(
            chunk_markdown(
                text,
                source=relative,
                min_chars=min_chars,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                tokenizer=tokenizer,
            )
        )
    return documents
