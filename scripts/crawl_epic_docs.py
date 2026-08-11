#!/usr/bin/env python3
"""
Crawl UE 5.7 Epic Games documentation pages and index into the knowledge base.
Usage:
    ue-kb-crawl or: python scripts/crawl_epic_docs.py

Fetches landing pages → extracts sub-page URLs → extracts paragraph content →
chunks → indexes into ChromaDB (ue_knowledge collection).

Pages crawled:
  - Unreal Engine 5.7 Release Notes (full text)
  - Unreal Engine Modules (full text)
  - Project Settings (sub-section descriptions)
  - Data Assets (summary)
  - Architecture sub-topics (13 page summaries)

Limitations:
  - Some pages are Angular SPAs with no SSR content (C++ Programming, Materials).
    These are skipped — coverage is provided by engine source API comments instead.
  - 0.5s polite delay between requests to Epic's servers.
"""

import re, os, time
from pathlib import Path
import subprocess

CHROMA_DIR = Path(os.environ.get("UE_KB_CHROMA_DIR", str(Path(__file__).resolve().parents[1] / ".chroma_db")))
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
BASE_URL = "https://dev.epicgames.com/documentation/unreal-engine"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Pages to crawl (slug → display name)
PAGES = {
    "unreal-engine-5-7-release-notes": "Unreal Engine 5.7 Release Notes",
    "unreal-engine-modules": "Unreal Engine Modules",
    "data-assets-in-unreal-engine": "Data Assets in Unreal Engine",
    "project-settings-in-unreal-engine": "Project Settings",
}


def fetch(url):
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "-A", UA, url],
            capture_output=True, text=True, timeout=30
        )
        return r.stdout if r.returncode == 0 else None
    except:
        return None


def extract_texts(html):
    texts = []
    idx = html.find("<article")
    if idx >= 0:
        end = html.find("</article>", idx)
        article = html[idx:end] if end > 0 else html[idx:]
        for m in re.finditer(r"<p[^>]*>(.*?)</p>", article, re.DOTALL):
            t = re.sub(r"<[^>]+>", "", m.group(1))
            t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
            t = re.sub(r"\s+", " ", t).strip()
            if len(t) > 40:
                texts.append(t)
    for m in re.finditer(r'description="([^"]+)"', html):
        t = m.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 30:
            texts.append(t)
    for m in re.finditer(r"block-callout-content[^>]*>(.*?)</div></div></block-callout>", html, re.DOTALL):
        t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 30:
            texts.append(f"[Note] {t}")
    for m in re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", html, re.DOTALL):
        t = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
        if t and len(t) > 5:
            texts.append(f"\n## {t}\n")
    return texts


def chunk_texts(texts):
    chunks = []
    current = ""
    for t in texts:
        if len(current) + len(t) > 1200 and current:
            chunks.append(current.strip())
            current = t
        else:
            current += (" " if current else "") + t
    if current.strip():
        chunks.append(current.strip())
    return chunks


def index_chunks(chunks, source_prefix, heading):
    from sentence_transformers import SentenceTransformer
    import chromadb

    model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("ue_knowledge")
    existing = set(collection.get(include=[])["ids"] or [])

    all_docs = []
    for i, text in enumerate(chunks):
        if len(text) < 40:
            continue
        chunk_id = f"epic-docs:{source_prefix}:{i}"
        if chunk_id in existing:
            continue
        all_docs.append({
            "id": chunk_id,
            "text": text,
            "source": f"epic-docs/{source_prefix}",
            "heading": heading,
            "doc_type": "documentation"
        })

    if not all_docs:
        print(f"  Nothing new (all {len(chunks)} chunks already exist)")
        return

    texts = [d["text"] for d in all_docs]
    ids = [d["id"] for d in all_docs]
    metas = [{"source": d["source"], "heading": d["heading"], "doc_type": d["doc_type"]} for d in all_docs]

    for i in range(0, len(texts), 64):
        batch = texts[i:i+64]
        batch_ids = ids[i:i+64]
        batch_metas = metas[i:i+64]
        embeddings = model.encode(batch, show_progress_bar=False, normalize_embeddings=True)
        collection.add(ids=batch_ids, embeddings=embeddings.tolist(), documents=batch, metadatas=batch_metas)

    print(f"  Indexed {len(all_docs)} new / {len(chunks)} total chunks (collection: {collection.count()})")


def main():
    print("UE 5.7 Epic Docs Crawler")
    print("=" * 50)

    for slug, name in PAGES.items():
        url = f"{BASE_URL}/{slug}?application_version=5.7"
        print(f"\n[{name}] ({slug})")

        html = fetch(url)
        if not html:
            print("  FAILED to fetch")
            continue

        texts = extract_texts(html)
        print(f"  Extracted {len(texts)} text blocks ({sum(len(t) for t in texts)} chars)")

        if not texts:
            print("  No SSR content (Angular SPA) — skipping")
            continue

        chunks = chunk_texts(texts)
        print(f"  Chunked into {len(chunks)} blocks")
        index_chunks(chunks, slug, name)

        time.sleep(0.5)  # polite delay

    print("\nDone!")


if __name__ == "__main__":
    main()
