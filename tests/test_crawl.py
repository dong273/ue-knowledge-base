"""crawl_epic_docs extraction, resume-cache and markdown rendering tests."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import crawl_epic_docs  # noqa: E402

SAMPLE_HTML = """
<html><body><article>
<h1>Modules</h1>
<p>Modules are the building blocks of Unreal Engine. Each module encapsulates a set of functionality.</p>
<p>Modules can depend on other modules, forming a dependency graph.</p>
<block-callout><div class="block-callout-content"><div><p>Modules are declared in Build.cs files.</p></div></div></block-callout>
</article>
<meta name="description" content="An overview of the Unreal Engine module system." />
</body></html>
"""


def test_extract_texts_paragraphs_headings_callout(tmp_path):
    texts = crawl_epic_docs.extract_texts(SAMPLE_HTML)
    joined = " ".join(texts)
    assert "building blocks of Unreal Engine" in joined
    assert "dependency graph" in joined
    assert "[Note]" in joined
    assert any("## Modules" in t for t in texts)


def test_to_markdown_renders_document(tmp_path):
    markdown = crawl_epic_docs.to_markdown(
        SAMPLE_HTML, "Unreal Engine Modules", "https://example.test/modules"
    )
    assert markdown.startswith("# Unreal Engine Modules")
    assert "Crawled locally" in markdown
    assert "building blocks" in markdown


def test_crawl_uses_cache_and_skips_fetch(tmp_path, monkeypatch):
    out = tmp_path / "out"
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "unreal-engine-modules.html").write_text(SAMPLE_HTML, encoding="utf-8")

    calls = {"n": 0}

    def fake_fetch(url, timeout=30):
        calls["n"] += 1
        return SAMPLE_HTML

    monkeypatch.setattr(crawl_epic_docs, "fetch", fake_fetch)
    # Only the cached page in PAGES to keep the test hermetic.
    crawl_epic_docs.PAGES = {"unreal-engine-modules": "Unreal Engine Modules"}
    code = crawl_epic_docs.main(["--out", str(out), "--cache-dir", str(cache)])
    assert code == 0
    assert calls["n"] == 0  # served from cache, never fetched
    assert (out / "unreal-engine-modules.md").is_file()
    assert "building blocks" in (out / "unreal-engine-modules.md").read_text(encoding="utf-8")
