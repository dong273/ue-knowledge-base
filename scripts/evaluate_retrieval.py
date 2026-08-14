#!/usr/bin/env python3
"""Run the held-out retrieval, regression, performance, passage and size gates.

Splits:
  heldout    — the release gate: 2 queries per topic (en + zh), topic-level
               and (when labeled) passage-level recall.  tune       — the tuning split: evaluated and reported for regression
               visibility; not gated (it is the pool used to tune, so gating
               on it would overfit).
  natural_zh — independent Chinese queries written WITHOUT glossary-alias
               wording (tests/data/golden_queries_zh_natural.json). Reported
               separately; the alias-derived heldout zh numbers tend to
               overestimate real-world Chinese phrasing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
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
from ue_knowledge.retrieval import expand_query

GOLDEN = REPO_ROOT / "tests/data/golden_queries.json"
PASSAGE_EXPECTED = REPO_ROOT / "tests/data/passage_expected.json"
NATURAL_ZH = REPO_ROOT / "tests/data/golden_queries_zh_natural.json"


def load_queries() -> list[dict]:
    topics = json.loads(GOLDEN.read_text(encoding="utf-8"))
    entries = [
        {**item, "topic": topic["topic"]}
        for topic in topics
        for item in topic["queries"]
    ]
    if PASSAGE_EXPECTED.is_file():
        expectations = json.loads(PASSAGE_EXPECTED.read_text(encoding="utf-8"))
        by_query = {item["query"]: item["expected"] for item in expectations}
        for entry in entries:
            entry["expected"] = by_query.get(entry["text"])
    if NATURAL_ZH.is_file():
        natural = json.loads(NATURAL_ZH.read_text(encoding="utf-8"))
        entries.extend(
            {
                **item,
                "topic": topic["topic"],
                "language": "zh",
                "split": "natural_zh",
            }
            for topic in natural
            for item in topic["queries"]
        )
    return entries


def reciprocal_rank(hits: list[dict], topic: str, limit: int = 5) -> float:
    for rank, hit in enumerate(hits[:limit], 1):
        if hit["source"].replace("\\", "/").startswith(topic + "/"):
            return 1.0 / rank
    return 0.0


def passage_recall(hits: list[dict], expected, limit: int = 3):
    """Passage-level recall@limit. None when the query has no labels."""
    if not expected:
        return None
    found = {(hit["source"], hit["heading"]) for hit in hits[:limit]}
    return any((item["source"], item["heading"]) in found for item in expected)


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
            "passage_recall_at_3": passage_recall(hits, entry.get("expected"), 3),
            "reciprocal_rank_at_5": reciprocal_rank(hits, entry["topic"], 5),
            # Only the hybrid profile expands the query; report the expanded
            # text so zh_dict misses are debuggable from the failure output.
            "expanded": expand_query(entry["text"]) if profile == "hybrid" else entry["text"],
            "top_hits": [
                {
                    "source": hit["source"],
                    "heading": hit["heading"],
                    "raw_score": hit["raw_score"],
                    "rank": hit["rank"],
                }
                for hit in hits
            ],
        })
    return rows


def rate(rows, language, split=None):
    selected = [row for row in rows if row["language"] == language]
    if split is not None:
        selected = [row for row in selected if row["split"] == split]
    if not selected:
        return None
    return sum(row["recall_at_3"] for row in selected) / len(selected)


def passage_rate(rows, split=None):
    selected = [row for row in rows if row.get("expected")]
    if split is not None:
        selected = [row for row in selected if row["split"] == split]
    if not selected:
        return None
    return sum(row["passage_recall_at_3"] for row in selected) / len(selected)


def mrr(rows, split=None):
    selected = rows if split is None else [row for row in rows if row["split"] == split]
    return statistics.fmean(row["reciprocal_rank_at_5"] for row in selected)


def split_stats(rows, split, profile):
    selected = [row for row in rows if row["split"] == split]
    languages = {row["language"] for row in selected}
    return {
        "zh_recall_at_3": rate(selected, "zh") if "zh" in languages else None,
        "en_recall_at_3": rate(selected, "en") if "en" in languages else None,
        "mrr_at_5": mrr(selected),
        "passage_recall_at_3": passage_rate(selected),
    }


def measure_cold_cli(model_name: str, db: Path) -> float:
    """End-to-end cold CLI query: fresh process, model load + index load.

    This is the latency an agent loop actually pays per subprocess call
    (the warm in-process p95 below does not include model loading).
    """
    command = [
        sys.executable, "-m", "ue_knowledge.cli", "query",
        "角色移动 速度衰减", "--top-k", "5",
        "--db", str(db), "--model", model_name, "--json",
    ]
    env = os.environ.copy()
    start = time.perf_counter()
    result = subprocess.run(
        command, capture_output=True, text=True, env=env, timeout=180
    )
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        raise RuntimeError(
            f"cold CLI query failed (rc={result.returncode}): {result.stderr[-500:]}"
        )
    return elapsed


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

    all_queries = load_queries()
    heldout = [entry for entry in all_queries if entry["split"] == "heldout"]
    tune = [entry for entry in all_queries if entry["split"] == "tune"]
    natural_zh = [entry for entry in all_queries if entry["split"] == "natural_zh"]

    vector = evaluate_profile(heldout, "vector", args.db, args.model, model)
    hybrid = evaluate_profile(heldout, "hybrid", args.db, args.model, model)
    tune_vector = evaluate_profile(tune, "vector", args.db, args.model, model)
    tune_hybrid = evaluate_profile(tune, "hybrid", args.db, args.model, model)
    natural_vector = evaluate_profile(natural_zh, "vector", args.db, args.model, model)
    natural_hybrid = evaluate_profile(natural_zh, "hybrid", args.db, args.model, model)

    # Warm first, then measure complete public query() calls on this machine.
    hot_text = "角色移动 速度衰减"
    query(hot_text, top_k=5, chroma_dir=args.db, model_name=args.model, embedder=model)
    timings = []
    for _ in range(30):
        start = time.perf_counter()
        query(hot_text, top_k=5, chroma_dir=args.db, model_name=args.model, embedder=model)
        timings.append(time.perf_counter() - start)
    p95 = statistics.quantiles(timings, n=20)[18]
    cold = measure_cold_cli(args.model, args.db)

    generation = load_current(args.db)
    overhead = (generation / "bm25.json").stat().st_size
    overhead += (REPO_ROOT / "src/ue_knowledge/glossary.json").stat().st_size
    model_bytes = cached_model_bytes(args.model)
    gates = {
        "heldout_zh_recall_at_3": rate(hybrid, "zh", "heldout") >= 0.80,
        "zh_gain_20pp": rate(hybrid, "zh", "heldout") - rate(vector, "zh", "heldout") >= 0.20,
        "heldout_en_recall_at_3": rate(hybrid, "en", "heldout") >= 0.90,
        "en_regression_within_2pp": rate(hybrid, "en", "heldout") >= rate(vector, "en", "heldout") - 0.02,
        "overall_mrr_at_5_not_lower": mrr(hybrid, "heldout") >= mrr(vector, "heldout"),
        # Passage-level recall: labels in tests/data/passage_expected.json
        # are the most specific section the engine actually returns for each
        # held-out query (refined from a top-10 pass; no "前言" fallbacks).
        # Same-source labels make this a REGRESSION gate (measured 98.4%),
        # not an absolute-quality claim — it fails when a change stops
        # surfacing the right section in the top 3.
        "heldout_passage_recall_at_3": passage_rate(hybrid, "heldout") >= 0.80,
        # natural_zh is the honest bar for spoken-Chinese queries: no
        # glossary-alias wording, plain phrasing (baseline 25.8% before the
        # zh_dict spoken-phrase expansion; threshold keeps headroom).
        "natural_zh_recall_at_3": rate(natural_hybrid, "zh") >= 0.40,
        "hot_query_p95_under_1s": p95 < 1.0,
        # Cold CLI is dominated by loading the ~100MB embedding model into a
        # fresh process (measured 12s on the release machine vs 0.07s warm).
        # The budget is set so regressions (e.g. accidental model upsize or
        # index bloat) still fail, while the honest cost is documented: agent
        # loops should use a persistent process / ue-kb serve.
        "cold_cli_query_under_15s": cold < 15.0,
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
        "query_counts": {
            "golden": len(all_queries),
            "heldout": len(heldout),
            "tune": len(tune),
            "natural_zh": len(natural_zh),
        },
        "splits": {
            "heldout": {"vector": split_stats(vector, "heldout", "vector"),
                        "hybrid": split_stats(hybrid, "heldout", "hybrid")},
            "tune": {"vector": split_stats(tune_vector, "tune", "vector"),
                     "hybrid": split_stats(tune_hybrid, "tune", "hybrid")},
            "natural_zh": {"vector": split_stats(natural_vector, "natural_zh", "vector"),
                           "hybrid": split_stats(natural_hybrid, "natural_zh", "hybrid")},
        },
        "hot_query_p95_seconds": p95,
        "cold_cli_query_seconds": cold,
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
            "heldout_vector": [row for row in vector if not row["recall_at_3"]],
            "heldout_hybrid": [row for row in hybrid if not row["recall_at_3"]],
            "tune_hybrid": [row for row in tune_hybrid if not row["recall_at_3"]],
            "natural_zh_hybrid": [row for row in natural_hybrid if not row["recall_at_3"]],
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
