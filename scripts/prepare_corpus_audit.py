#!/usr/bin/env python3
"""Prepare a schema-v2 claim review queue without approving evidence.

The queue is deliberately explicit: candidate classifications and source
locators help a reviewer, while ``review_state=pending`` keeps the release gate
closed until every claim and code artifact has been checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ue_knowledge.corpus_audit import (  # noqa: E402
    AUDIT_POLICY_VERSION,
    DISPOSITIONS,
    scan_corpus,
)
from ue_knowledge.metadata import public_provenance_from_ledger  # noqa: E402

ENGINE_SOURCES = {
    "ue-networking-replication": "Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h",
    "ue-gameplay-abilities": "Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities/Public/AbilitySystemComponent.h",
    "ue-module-build-system": "Engine/Source/Programs/UnrealBuildTool/Configuration/ModuleRules.cs",
    "ue-editor-tools": "Engine/Source/Editor/UnrealEd/Public/Editor/EditorEngine.h",
    "ue-ui-umg-slate": "Engine/Source/Runtime/UMG/Public/Blueprint/UserWidget.h",
    "ue-input-system": "Engine/Plugins/EnhancedInput/Source/EnhancedInput/Public/InputAction.h",
    "ue-physics-collision": "Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h",
    "ue-animation-system": "Engine/Source/Runtime/Engine/Classes/Animation/AnimInstance.h",
    "ue-materials-rendering": "Engine/Source/Runtime/Engine/Classes/Materials/MaterialInstanceDynamic.h",
    "ue-niagara-effects": "Engine/Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h",
    "ue-audio-system": "Engine/Source/Runtime/Engine/Classes/Components/AudioComponent.h",
    "ue-world-level-streaming": "Engine/Source/Runtime/Engine/Classes/Engine/World.h",
}


def _source_ref(source: str) -> str:
    domain = source.split("/", 1)[0]
    return f"EngineSource:UE5.7.4/{ENGINE_SOURCES.get(domain, 'Engine/Source/Runtime/Core/Public/CoreMinimal.h')}"


def _candidate_disposition(record: dict) -> str:
    kinds = set(record.get("claim_types", []))
    if "visual" in kinds:
        return "human_outcome"
    if "runtime" in kinds:
        return "runtime_behavior"
    if "api" in kinds:
        return "api_contract"
    return "concept"


def _requirements(record: dict, disposition: str) -> list[str]:
    if disposition == "non_claim":
        return []
    requirements: list[str] = ["authoritative_source"]
    kinds = set(record.get("claim_types", []))
    if disposition == "api_contract" or (record.get("kind") == "code_artifact" and "api" in kinds):
        requirements.append("compile")
    if disposition == "runtime_behavior" or "runtime" in kinds:
        requirements.append("runtime")
    if disposition == "human_outcome":
        requirements.append("human")
    return list(dict.fromkeys(requirements))


def _copy_review_fields(previous: dict, target: dict) -> None:
    """Carry only explicit reviewer fields across a rescan."""
    for field in (
        "disposition", "review_state", "reviewed_at", "reviewer", "exclusion_reason",
        "requirements", "evidence_ids", "validation_ids", "human_evidence", "notes",
    ):
        if field in previous:
            target[field] = previous[field]


def prepare(source: Path, ledger_path: Path, provenance_path: Path, *, scope: str = "public") -> dict[str, int | str]:
    scanned = scan_corpus(source)
    previous: dict = {}
    if ledger_path.exists():
        try:
            raw = json.loads(ledger_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("schema_version") == 2:
                previous = raw
        except (OSError, json.JSONDecodeError):
            previous = {}

    documents: dict[str, dict] = {}
    for relative, document in scanned["documents"].items():
        old_document = previous.get("documents", {}).get(relative, {})
        old_records = {
            item.get("claim_id"): item
            for item in old_document.get("claims", [])
            if isinstance(item, dict) and item.get("claim_id")
        }
        records: list[dict] = []
        for record in document["claims"]:
            old = old_records.get(record["claim_id"], {})
            target = dict(record)
            old_terminal = old.get("review_state") in {"verified", "rewritten", "excluded"}
            disposition = old.get("disposition") if old_terminal else _candidate_disposition(record)
            if disposition not in DISPOSITIONS:
                disposition = _candidate_disposition(record)
            target.update({
                "disposition": disposition,
                "review_state": old.get("review_state") if old_terminal else "pending",
                "reviewed_at": old.get("reviewed_at") if old_terminal else None,
                "reviewer": old.get("reviewer") if old_terminal else None,
                "requirements": old.get("requirements", _requirements(record, disposition)) if old_terminal else _requirements(record, disposition),
                "evidence_ids": old.get("evidence_ids", []) if old_terminal else [],
                "notes": old.get("notes", "") if old_terminal else "",
            })
            if disposition == "non_claim":
                target["exclusion_reason"] = old.get("exclusion_reason", "")
            if old_terminal:
                _copy_review_fields(old, target)
            # Candidates are reviewer input, not approval state. Preserve them
            # across rescans even while a claim remains pending; only the
            # terminal review/evidence fields are otherwise carried forward.
            target["evidence_candidates"] = sorted(set(old.get("evidence_candidates", [])) | {_source_ref(relative)})
            records.append(target)
        documents[relative] = {
            "source": relative,
            "knowledge_id": document["knowledge_id"],
            "content_sha256": document["content_sha256"],
            "claims": sorted(records, key=lambda item: item.get("claim_id", "")),
        }

    ledger = {
        "schema_version": 2,
        "policy_version": AUDIT_POLICY_VERSION,
        "corpus": "<CORPUS_ROOT>",
        "engine": {"version": "5.7.4", "changelist": 51494982},
        "evidence_catalog": previous.get("evidence_catalog", {}),
        "documents": dict(sorted(documents.items())),
    }
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger_digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    sidecar = public_provenance_from_ledger(ledger, ledger_digest, scope=scope)
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    kinds = {}
    for document in documents.values():
        for record in document["claims"]:
            kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
    return {
        "documents": len(documents),
        "claims": sum(len(document["claims"]) for document in documents.values()),
        "code_artifacts": kinds.get("code_artifact", 0),
        "status": "pending_review",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prepare, but do not approve, a UE-KB schema-v2 claim audit")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--scope", choices=("public", "project"), default="public")
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.source, args.ledger, args.provenance, scope=args.scope), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
