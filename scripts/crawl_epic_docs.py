#!/usr/bin/env python3
"""
Crawl UE 5.7 Epic Games documentation pages into a LOCAL markdown corpus,
then build the knowledge-base index from it with the standard pipeline:

    python scripts/crawl_epic_docs.py --out epic-docs/
    ue-kb build --source epic-docs/ --append

Design notes (v0.6):
  - The old version wrote straight into a ChromaDB collection that predates
    the schema-v2 generation layout and silently ignored the atomic-index
    machinery. The crawler now only ever produces markdown corpus files;
    indexing goes through `ue-kb build` like any other source.
  - Resume-friendly: fetched HTML is cached under --cache-dir, so a rerun
    after a partial crawl skips already-downloaded pages (offline reruns
    still regenerate the markdown from cache).
  - Polite: 0.5s delay between requests, 3 retries with backoff.
  - Copyright: extracted text is generated locally and NOT redistributed —
    the same boundary the README declares for engine-source extraction.

Usage:
    python scripts/crawl_epic_docs.py [--out epic-docs] [--cache-dir .cache/epic-docs]
"""

from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://dev.epicgames.com/documentation/unreal-engine"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
POLITE_DELAY_SECONDS = 0.5
RETRIES = 3

# Pages to crawl (slug → display name). Extend by adding more slugs.
PAGES = {
    "unreal-engine-5-7-release-notes": "Unreal Engine 5.7 Release Notes",
    "unreal-engine-modules": "Unreal Engine Modules",
    "data-assets-in-unreal-engine": "Data Assets in Unreal Engine",
    "project-settings-in-unreal-engine": "Project Settings",
}


def fetch(url: str, timeout: int = 30) -> str | None:
    """GET with retries/backoff; returns HTML or None on final failure."""
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            response = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if response.status_code == 200:
                return response.text
            last_error = RuntimeError(f"HTTP {response.status_code}")
        except Exception as exc:  # network-level failure
            last_error = exc
        if attempt + 1 < RETRIES:
            time.sleep(1.5 * (attempt + 1))
    print(f"  FAILED after {RETRIES} tries: {last_error}")
    return None


def extract_texts(html: str) -> list[str]:
    """Extract headings, paragraphs, meta descriptions and callouts."""
    texts: list[str] = []
    idx = html.find("<article")
    if idx >= 0:
        end = html.find("</article>", idx)
        article = html[idx:end] if end > 0 else html[idx:]
        for m in re.finditer(r"<p[^>]*>(.*?)</p>", article, re.DOTALL):
            t = re.sub(r"<[^>]+>", "", m.group(1))
            t = _clean(t)
            if len(t) > 40:
                texts.append(t)
    for m in re.finditer(r'description="([^"]+)"', html):
        t = _clean(m.group(1))
        if len(t) > 30:
            texts.append(t)
    for m in re.finditer(r"block-callout-content[^>]*>(.*?)</div></div></block-callout>", html, re.DOTALL):
        t = _clean(re.sub(r"<[^>]+>", "", m.group(1)))
        if len(t) > 30:
            texts.append(f"[Note] {t}")
    for m in re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", html, re.DOTALL):
        t = _clean(re.sub(r"<[^>]+>", "", m.group(2)))
        if t and len(t) > 5:
            texts.append(f"\n## {t}\n")
    return texts


def _clean(text: str) -> str:
    for old, new in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def to_markdown(html: str, display_name: str, url: str) -> str:
    """Render extracted blocks as a markdown document."""
    lines = [
        f"# {display_name}",
        "",
        f"> Crawled locally from {url} on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. "
        f"Not redistributed (Epic copyright).",
        "",
    ]
    body = "\n".join(extract_texts(html)).strip()
    if not body:
        return ""
    lines.append(body)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crawl_epic_docs",
        description="Crawl UE 5.7 Epic docs into a local markdown corpus (then ue-kb build --source).",
    )
    parser.add_argument("--out", default="epic-docs", help="output corpus dir (default: epic-docs/)")
    parser.add_argument("--cache-dir", default=".cache/epic-docs", help="HTML cache dir for resume (default: .cache/epic-docs)")
    parser.add_argument("--version", default="5.7", help="docs version query param (default: 5.7)")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"UE {args.version} Epic Docs Crawler")
    print(f"  out      : {out_dir.resolve()}")
    print(f"  cache    : {cache_dir.resolve()}")
    print("=" * 50)

    stats = {"fetched": 0, "cached": 0, "failed": 0, "chars": 0, "blocks": 0}
    for slug, name in PAGES.items():
        url = f"{BASE_URL}/{slug}?application_version={args.version}"
        cache_file = cache_dir / f"{slug}.html"
        print(f"\n[{name}] ({slug})")

        if cache_file.is_file():
            html = cache_file.read_text(encoding="utf-8", errors="replace")
            stats["cached"] += 1
            print(f"  Using cached HTML ({cache_file.stat().st_size} bytes)")
        else:
            html = fetch(url)
            if not html:
                stats["failed"] += 1
                continue
            cache_file.write_text(html, encoding="utf-8")
            stats["fetched"] += 1
            time.sleep(POLITE_DELAY_SECONDS)

        markdown = to_markdown(html, name, url)
        if not markdown:
            print("  No SSR content (Angular SPA) — skipping")
            stats["failed"] += 1
            continue
        target = out_dir / f"{slug}.md"
        target.write_text(markdown, encoding="utf-8")
        stats["chars"] += len(markdown)
        stats["blocks"] += markdown.count("\n## ")
        print(f"  Wrote {target.name} ({len(markdown)} chars, {markdown.count(chr(10))} lines)")

    print("\n" + "=" * 50)
    print(f"Summary: {stats['fetched']} fetched, {stats['cached']} from cache, "
          f"{stats['failed']} skipped/failed, {stats['blocks']} sections, {stats['chars']} chars")
    print(f"Corpus:  {out_dir.resolve()}")
    print(f"Next:    ue-kb build --source {out_dir} --append")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
