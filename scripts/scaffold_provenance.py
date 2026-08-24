#!/usr/bin/env python3
"""Create a fail-closed provenance sidecar for a Markdown corpus.

The generated entries deliberately contain no evidence claims. They are a
review queue, not a declaration that the corpus is verified. Run
``ue-kb audit-corpus`` after filling each entry with real UE evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge.metadata import PROVENANCE_SCHEMA_VERSION, stable_knowledge_id
from ue_knowledge.corpus_audit import sha256_bytes


def scaffold(source: Path, output: Path, scope: str = "public") -> dict:
    if scope not in {"public", "project"}:
        raise ValueError("scope must be 'public' or 'project'")
    if not source.is_dir():
        raise FileNotFoundError(source)
    documents = {}
    for path in sorted(source.rglob("*.md")):
        relative = path.relative_to(source).as_posix()
        documents[relative] = {
            "knowledge_id": stable_knowledge_id(relative),
            "scope": scope,
            "content_sha256": sha256_bytes(path.read_bytes()),
            "engine_versions": [],
            "verification": [],
            "claim_types": [],
            "verified_at": None,
            "evidence_refs": [],
            "source_ids": [],
            "validation_ids": [],
            "expires_at": None,
            "audit_status": "pending",
            "human_evidence": "not_run",
        }
    payload = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "scope": scope,
        "documents": documents,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"source": str(source.resolve()), "output": str(output.resolve()), "documents": len(documents)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scaffold pending UE-KB provenance entries")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", choices=("public", "project"), default="public")
    parser.add_argument("--force", action="store_true", help="overwrite an existing sidecar")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        parser.error(f"output exists; pass --force to replace it: {args.output}")
    print(json.dumps(scaffold(args.source, args.output, args.scope), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
