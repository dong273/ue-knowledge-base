#!/usr/bin/env python3
"""Run the 0.5 held-out retrieval, regression, performance and size gates."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge import config
from ue_knowledge.build import build_index
from ue_knowledge.chunking import collect_markdown, token_count
from ue_knowledge.index_store import load_current
from ue_knowledge.query import query


def load_queries() -> list[dict]:
    topics = json.loads(
        (REPO_ROOT / "tests/data/golden_queries.json").read_text(encoding="utf-8")
    )
    return [
        {**item, "topic": topic["topic"]}
        for topic in topics
        for item in topic["queries"]
    ]


def reciprocal_rank(hits: list[dict], topic: str, limit: int = 5) -> float:
    for rank, hit in enumerate(hits[:limit], 1):
        if hit["source"].replace("\\", "/").startswith(topic + "/"):
            return 1.0 / rank
    return 0.0


def evaluate_profile(entries, profile, db, model_name, model) -> list[dict]:
    rows = []
    for entry in entries:
        hits = query(
            entry["text"], top_k=5, chroma_dir=db, model_name=model_name,
            embedder=model, profile=profile,
        )
        rows.append({
            **entry,
            "recall_at_3": reciprocal_rank(hits, entry["topic"], 3) > 0,
            "reciprocal_rank_at_5": reciprocal_rank(hits, entry["topic"], 5),
            "top_sources": [hit["source"] for hit in hits],
        })
    return rows


def rate(rows, language):
    selected = [row for row in rows if row["language"] == language]
    return sum(row["recall_at_3"] for row in selected) / len(selected)


def mrr(rows):
    return statistics.fmean(row["reciprocal_rank_at_5"] for row in rows)


def cached_model_bytes(model_name: str) -> int | None:
    """Measure the selected Hugging Face repository without downloading."""
    try:
        from huggingface_hub import scan_cache_dir

        repository = next(
            item for item in scan_cache_dir().repos if item.repo_id == model_name
        )
        return int(repository.size_on_disk)
    except (ImportError, StopIteration, OSError):
        return None


def has_balanced_fences(text: str) -> bool:
    stack: list[str] = []
    for match in re.finditer(r"^\s*(`{3,}|~{3,})", text, re.MULTILINE):
        marker = match.group(1)
        if stack and marker[0] == stack[-1][0] and len(marker) >= len(stack[-1]):
            stack.pop()
        else:
            stack.append(marker)
    return not stack


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=config.DEFAULT_SOURCE_DIR)
    parser.add_argument("--model", default=config.MODEL_NAME)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(args.model, local_files_only=True)
    model.max_seq_length = 512
    chunks = collect_markdown(args.source, tokenizer=model.tokenizer)
    chunk_token_counts = [token_count(chunk["text"], model.tokenizer) for chunk in chunks]
    unbalanced_fences = sum(not has_balanced_fences(chunk["text"]) for chunk in chunks)
    if args.build:
        build_index(
            source_dir=args.source, chroma_dir=args.db,
            model_name=args.model, embedder=model, force=True,
            progress=lambda message: print(message, file=sys.stderr),
        )

    heldout = [entry for entry in load_queries() if entry["split"] == "heldout"]
    vector = evaluate_profile(heldout, "vector", args.db, args.model, model)
    hybrid = evaluate_profile(heldout, "hybrid", args.db, args.model, model)

    # Warm first, then measure complete public query() calls on this machine.
    hot_text = "角色移动 速度衰减"
    query(hot_text, top_k=5, chroma_dir=args.db, model_name=args.model, embedder=model)
    timings = []
    for _ in range(30):
        start = time.perf_counter()
        query(hot_text, top_k=5, chroma_dir=args.db, model_name=args.model, embedder=model)
        timings.append(time.perf_counter() - start)
    p95 = statistics.quantiles(timings, n=20)[18]

    generation = load_current(args.db)
    overhead = (generation / "bm25.json").stat().st_size
    overhead += (REPO_ROOT / "src/ue_knowledge/glossary.json").stat().st_size
    model_bytes = cached_model_bytes(args.model)
    gates = {
        "heldout_zh_recall_at_3": rate(hybrid, "zh") >= 0.80,
        "zh_gain_20pp": rate(hybrid, "zh") - rate(vector, "zh") >= 0.20,
        "heldout_en_recall_at_3": rate(hybrid, "en") >= 0.90,
        "en_regression_within_2pp": rate(hybrid, "en") >= rate(vector, "en") - 0.02,
        "overall_mrr_at_5_not_lower": mrr(hybrid) >= mrr(vector),
        "hot_query_p95_under_1s": p95 < 1.0,
        "default_model_about_100mb": (
            args.model == config.MODEL_NAME
            and model_bytes is not None
            and 80 * 1024 * 1024 <= model_bytes <= 150 * 1024 * 1024
        ),
        "added_index_and_package_under_20mb": overhead <= 20 * 1024 * 1024,
        "all_chunks_at_most_384_tokens": max(chunk_token_counts) <= 384,
        "all_chunk_code_fences_balanced": unbalanced_fences == 0,
    }
    report = {
        "query_counts": {"golden": 124, "heldout": len(heldout)},
        "vector": {
            "zh_recall_at_3": rate(vector, "zh"),
            "en_recall_at_3": rate(vector, "en"),
            "mrr_at_5": mrr(vector),
        },
        "hybrid": {
            "zh_recall_at_3": rate(hybrid, "zh"),
            "en_recall_at_3": rate(hybrid, "en"),
            "mrr_at_5": mrr(hybrid),
        },
        "hot_query_p95_seconds": p95,
        "default_model_cached_bytes": model_bytes,
        "added_bytes": overhead,
        "chunking": {
            "chunks": len(chunks),
            "max_tokens": max(chunk_token_counts),
            "over_384": sum(count > 384 for count in chunk_token_counts),
            "unbalanced_fences": unbalanced_fences,
        },
        "gates": gates,
        "passed": all(gates.values()),
        "failures": {
            "vector": [row for row in vector if not row["recall_at_3"]],
            "hybrid": [row for row in hybrid if not row["recall_at_3"]],
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
