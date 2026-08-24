#!/usr/bin/env python3
"""Create a deterministic schema-v2 claim ledger for a Markdown corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge.corpus_audit import scan_corpus  # noqa: E402


def scaffold(source: Path, output: Path, *, force: bool = False) -> dict[str, int | str]:
    if output.exists() and not force:
        raise FileExistsError(f"output exists; pass --force: {output}")
    payload = scan_corpus(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "documents": len(payload["documents"]),
        "claims": sum(len(doc["claims"]) for doc in payload["documents"].values()),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scaffold a pending claim-level UE-KB audit ledger")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(scaffold(args.source, args.output, force=args.force), ensure_ascii=False))
    except (FileExistsError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
