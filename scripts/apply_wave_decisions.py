#!/usr/bin/env python3
"""Apply an explicit, exhaustive review decision set to one audit wave."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge.corpus_audit import DISPOSITIONS, REQUIREMENTS  # noqa: E402
from ue_knowledge.metadata import public_provenance_from_ledger  # noqa: E402

TERMINAL_STATES = {"verified", "rewritten", "excluded"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def apply_decisions(
    ledger_path: Path,
    provenance_path: Path,
    registry_path: Path,
    wave_path: Path,
    decisions_path: Path,
) -> dict[str, int]:
    ledger = _load(ledger_path)
    registry = _load(registry_path)
    wave = _load(wave_path)
    decisions = _load(decisions_path)
    if decisions.get("wave_id") != wave.get("wave_id"):
        raise ValueError("decision wave_id does not match wave manifest")

    selected_paths = [item.get("path") for item in wave.get("documents", []) if isinstance(item, dict)]
    selected_records: dict[str, dict[str, Any]] = {}
    for source in selected_paths:
        document = ledger.get("documents", {}).get(source)
        if not isinstance(document, dict):
            raise ValueError(f"wave document is missing from ledger: {source}")
        for record in document.get("claims", []):
            claim_id = record.get("claim_id") if isinstance(record, dict) else None
            if not isinstance(claim_id, str):
                raise ValueError(f"invalid claim in wave document: {source}")
            if claim_id in selected_records:
                raise ValueError(f"duplicate claim id in ledger: {claim_id}")
            selected_records[claim_id] = record

    groups = decisions.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("decisions groups must be a non-empty list")
    assigned: dict[str, dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("decision group must be an object")
        disposition = group.get("disposition")
        if disposition not in DISPOSITIONS:
            raise ValueError(f"invalid disposition: {disposition}")
        requirements = group.get("requirements", [])
        if not isinstance(requirements, list) or any(item not in REQUIREMENTS for item in requirements):
            raise ValueError(f"invalid requirements for disposition: {disposition}")
        state = group.get("review_state", "excluded" if disposition == "non_claim" else "verified")
        if state not in TERMINAL_STATES:
            raise ValueError(f"invalid terminal review state: {state}")
        claim_ids = group.get("claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids:
            raise ValueError("decision group requires claim_ids")
        for claim_id in claim_ids:
            if claim_id not in selected_records:
                raise ValueError(f"decision references unknown wave claim: {claim_id}")
            if claim_id in assigned:
                raise ValueError(f"wave claim has multiple decisions: {claim_id}")
            assigned[claim_id] = group
    missing = sorted(set(selected_records) - set(assigned))
    if missing:
        raise ValueError(f"wave decisions omit {len(missing)} claims; first={missing[0]}")

    catalog_templates = decisions.get("evidence_catalog", {})
    if not isinstance(catalog_templates, dict):
        raise ValueError("evidence_catalog must be an object")
    catalog = ledger.setdefault("evidence_catalog", {})
    selected_claim_ids = set(selected_records)
    for evidence_id, template in catalog_templates.items():
        if not isinstance(template, dict):
            raise ValueError(f"invalid evidence template: {evidence_id}")
        item = dict(template)
        prior = catalog.get(evidence_id, {})
        prior_coverage = prior.get("covers_claims", []) if isinstance(prior, dict) else []
        item["covers_claims"] = sorted(
            claim_id for claim_id in prior_coverage
            if isinstance(claim_id, str) and claim_id not in selected_claim_ids
        )
        catalog[evidence_id] = item

    validation_entries: dict[str, dict[str, Any]] = {}
    for field in ("fixtures", "tests"):
        for item in registry.get(field, []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                validation_entries[item["id"]] = item
                item["covers_claims"] = sorted(
                    claim_id for claim_id in item.get("covers_claims", [])
                    if isinstance(claim_id, str) and claim_id not in selected_claim_ids
                )

    reviewer = str(decisions.get("reviewer", "wave-01-review"))
    reviewed_at = str(decisions.get("reviewed_at", ""))
    if not reviewed_at:
        raise ValueError("reviewed_at is required")
    disposition_counts: Counter[str] = Counter()
    for claim_id, record in selected_records.items():
        group = assigned[claim_id]
        disposition = str(group["disposition"])
        evidence_ids = list(group.get("evidence_ids", []))
        validation_ids = list(group.get("validation_ids", []))
        for evidence_id in evidence_ids:
            if evidence_id not in catalog:
                raise ValueError(f"unknown evidence id in decision: {evidence_id}")
            catalog[evidence_id]["covers_claims"] = sorted(set(catalog[evidence_id]["covers_claims"]) | {claim_id})
        for validation_id in validation_ids:
            if validation_id not in validation_entries:
                raise ValueError(f"unknown successful validation id in decision: {validation_id}")
            validation_entries[validation_id]["covers_claims"] = sorted(
                set(validation_entries[validation_id].get("covers_claims", [])) | {claim_id}
            )
        record.update({
            "disposition": disposition,
            "review_state": group.get("review_state", "excluded" if disposition == "non_claim" else "verified"),
            "status": group.get("review_state", "excluded" if disposition == "non_claim" else "verified"),
            "reviewed_at": reviewed_at,
            "reviewer": reviewer,
            "requirements": list(group.get("requirements", [])),
            "evidence_ids": evidence_ids,
            "validation_ids": validation_ids,
            "human_evidence": group.get("human_evidence", "not_applicable"),
            "notes": group.get("notes", ""),
        })
        if disposition == "non_claim":
            reason = str(group.get("exclusion_reason", "")).strip()
            if not reason:
                raise ValueError("non_claim decision requires exclusion_reason")
            record["exclusion_reason"] = reason
        else:
            record.pop("exclusion_reason", None)
        disposition_counts[disposition] += 1

    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ledger_digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    sidecar = public_provenance_from_ledger(ledger, ledger_digest, scope="public")
    provenance_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "documents": len(selected_paths),
        "claims": len(selected_records),
        "evidence": len(catalog_templates),
        "validations": sum(1 for item in validation_entries.values() if item.get("covers_claims")),
        **dict(disposition_counts),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="apply explicit review decisions for one corpus wave")
    parser.add_argument("--ledger", type=Path, default=REPO_ROOT / "validation/corpus-audit.json")
    parser.add_argument("--provenance", type=Path, default=REPO_ROOT / "src/ue_knowledge/knowledge/.ue-kb-provenance.json")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "validation/fixture-registry.json")
    parser.add_argument("--wave", type=Path, default=REPO_ROOT / "validation/audit-waves/wave-01-high-risk.json")
    parser.add_argument("--decisions", type=Path, default=REPO_ROOT / "validation/audit-waves/wave-01-decisions.json")
    args = parser.parse_args(argv)
    print(json.dumps(apply_decisions(args.ledger, args.provenance, args.registry, args.wave, args.decisions), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
