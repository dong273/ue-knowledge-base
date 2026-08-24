#!/usr/bin/env python3
"""Fail-closed local candidate gate for the v0.7 release checklist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from scripts.check_ue57_evidence import check as check_ue57_evidence
from ue_knowledge.metadata import audit_corpus


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="check v0.7 candidate release prerequisites")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "src/ue_knowledge/knowledge")
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--scope", choices=("public", "project"), default="public")
    parser.add_argument("--evidence-manifest", type=Path, required=True)
    parser.add_argument(
        "--claim-ledger",
        type=Path,
        default=REPO_ROOT / "validation/corpus-audit.json",
        help="claim-level audit ledger (required for a v0.7 candidate)",
    )
    args = parser.parse_args(argv)

    audit = audit_corpus(
        args.source,
        provenance_path=args.provenance,
        source_registry=args.source_registry,
        evidence_manifest=args.evidence_manifest,
        claim_ledger=args.claim_ledger,
        scope=args.scope,
    )
    fixture_registry = REPO_ROOT / "validation/fixture-registry.json"
    evidence_errors = check_ue57_evidence(
        args.evidence_manifest,
        fixture_registry=fixture_registry,
        claim_ledger=args.claim_ledger,
    )
    payload = {
        "schema_version": 2,
        "scope": args.scope,
        "audit": {
            "documents": audit["documents"],
            "covered": audit["covered"],
            "reviewed": audit.get("reviewed", audit["verified"]),
            "verified": audit["verified"],
            "pending": audit["pending"],
            "issue_count": audit["issue_count"],
            "blocking_issue_count": audit.get("blocking_issue_count", audit["issue_count"]),
            "warning_count": audit.get("warning_count", 0),
            "claim_summary": audit.get("claim_summary", {}),
            "code_summary": audit.get("code_summary", {}),
            "policy_version": audit.get("policy_version", 0),
            "release_ready": audit["release_ready"],
        },
        "evidence_errors": evidence_errors,
        "passed": bool(
            audit["release_ready"]
            and audit.get("documents") == audit.get("reviewed") == audit.get("verified")
            and audit.get("pending") == 0
            and audit.get("blocking_issue_count", audit["issue_count"]) == 0
            and audit.get("issue_count") == 0
            and not evidence_errors
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
