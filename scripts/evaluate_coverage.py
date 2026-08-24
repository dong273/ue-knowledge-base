#!/usr/bin/env python3
"""Evaluate coverage/abstention queries against a built index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge.query import query_envelope


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--dataset", type=Path, default=REPO_ROOT / "tests/data/coverage_queries.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    rows = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = []
    failures = []
    categories = {row.get("category") for row in rows}
    required_categories = {"chapter", "confusable", "natural_zh", "unsupported"}
    for row in rows:
        envelope = query_envelope(row["query"], chroma_dir=args.db, model_name=args.model)
        status = envelope["coverage"]["status"]
        top_source = envelope["hits"][0]["source"] if envelope["hits"] else None
        result = {**row, "observed_coverage": status, "top_source": top_source}
        report.append(result)
        if status != row["expected_coverage"]:
            failures.append(result)
        expected_source = row.get("expected_source_contains")
        if expected_source and not any(expected_source in hit["source"] for hit in envelope["hits"][:3]):
            failures.append({**result, "failure": "expected source not in top 3"})
        expected_heading = row.get("expected_heading_contains")
        if expected_heading and not any(
            expected_heading.casefold() in hit["heading"].casefold()
            for hit in envelope["hits"][:3]
        ):
            failures.append({**result, "failure": "expected heading not in top 3"})
        if envelope.get("scope") != row.get("expected_scope", "public"):
            failures.append({**result, "failure": "unexpected scope"})

    unsupported = [row for row in report if row.get("expected_coverage") == "none"]
    false_positives = [row for row in unsupported if row["observed_coverage"] != "none"]
    false_positive_rate = len(false_positives) / len(unsupported) if unsupported else 0.0
    if not required_categories.issubset(categories):
        failures.append({"failure": "coverage dataset missing required category", "missing": sorted(required_categories - categories)})
    if false_positive_rate > 0.10:
        failures.append({"failure": "unsupported-query false-positive rate exceeds 10%", "rate": false_positive_rate})

    payload = {
        "schema_version": 1,
        "queries": len(rows),
        "failures": len(failures),
        "pass": not failures,
        "categories": sorted(categories),
        "unsupported_queries": len(unsupported),
        "unsupported_false_positives": len(false_positives),
        "unsupported_false_positive_rate": false_positive_rate,
        "results": report,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
