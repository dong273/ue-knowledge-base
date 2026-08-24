#!/usr/bin/env python3
"""Report a bounded corpus-review wave without weakening the global gate."""

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

from ue_knowledge.corpus_audit import audit_ledger  # noqa: E402

TERMINAL_REVIEW_STATES = {"verified", "rewritten", "excluded"}
STALE_CODES = {"CLAIM_CONTENT_CHANGED", "ENGINE_VERSION_MISMATCH", "EVIDENCE_EXPIRED"}


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_documents(manifest: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    if manifest.get("schema_version") != 1:
        errors.append({"code": "WAVE_SCHEMA_MISMATCH", "source": "<wave-manifest>", "message": "schema_version must be 1", "severity": "error"})
    raw_documents = manifest.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        errors.append({"code": "WAVE_DOCUMENTS_INVALID", "source": "<wave-manifest>", "message": "documents must be a non-empty list", "severity": "error"})
        return [], errors
    documents: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_documents):
        if not isinstance(item, dict):
            errors.append({"code": "WAVE_DOCUMENT_INVALID", "source": "<wave-manifest>", "message": f"documents[{index}] must be an object", "severity": "error"})
            continue
        path = str(item.get("path", "")).replace("\\", "/").strip("/")
        cohort = str(item.get("cohort", "")).strip()
        initial_hash = str(item.get("initial_content_sha256", "")).lower()
        if not path or Path(path).is_absolute() or ".." in Path(path).parts:
            errors.append({"code": "WAVE_PATH_INVALID", "source": path or "<wave-manifest>", "message": "path must be a safe corpus-relative path", "severity": "error"})
            continue
        if path in seen:
            errors.append({"code": "WAVE_PATH_DUPLICATE", "source": path, "message": "document appears more than once", "severity": "error"})
            continue
        if not cohort:
            errors.append({"code": "WAVE_COHORT_MISSING", "source": path, "message": "cohort is required", "severity": "error"})
        if len(initial_hash) != 64 or any(char not in "0123456789abcdef" for char in initial_hash):
            errors.append({"code": "WAVE_INITIAL_HASH_INVALID", "source": path, "message": "initial_content_sha256 must be lowercase SHA-256", "severity": "error"})
        seen.add(path)
        documents.append({"path": path, "cohort": cohort, "initial_content_sha256": initial_hash})
    return documents, errors


def audit_wave(
    source: Path,
    ledger_path: Path,
    wave_path: Path,
    *,
    evidence_manifest: Path | None = None,
) -> dict[str, Any]:
    """Return selected-wave progress while retaining the global result separately."""
    try:
        manifest = _load_object(wave_path, "wave manifest")
        ledger = _load_object(ledger_path, "claim ledger")
    except ValueError as exc:
        return {
            "wave_id": wave_path.stem,
            "documents": 0,
            "reviewed": 0,
            "pending": 0,
            "blocking_issue_count": 1,
            "warning_count": 0,
            "unclassified_code": 0,
            "stale_evidence": 0,
            "wave_ready": False,
            "global_release_ready": False,
            "issues": [{"code": "WAVE_INPUT_INVALID", "source": "<wave>", "message": str(exc), "severity": "error"}],
        }

    wave_documents, manifest_issues = _manifest_documents(manifest)
    selected = {item["path"] for item in wave_documents}
    global_audit = audit_ledger(source, ledger_path, evidence_manifest=evidence_manifest)
    relevant_issues = [
        issue for issue in global_audit.get("issues", [])
        if issue.get("source") in selected or str(issue.get("source", "")).startswith("<")
    ]
    relevant_issues.extend(manifest_issues)

    ledger_documents = ledger.get("documents", {}) if isinstance(ledger.get("documents"), dict) else {}
    reviewed = 0
    unclassified = 0
    changed_since_start: list[str] = []
    cohorts: dict[str, dict[str, Any]] = {}
    for item in wave_documents:
        relative = item["path"]
        cohort_name = item["cohort"]
        cohort = cohorts.setdefault(cohort_name, {"documents": 0, "reviewed": 0, "pending": 0, "blocking_issue_count": 0, "wave_ready": False})
        cohort["documents"] += 1
        corpus_path = source / Path(relative)
        if not corpus_path.is_file():
            relevant_issues.append({"code": "WAVE_DOCUMENT_MISSING", "source": relative, "message": "document is absent from corpus", "severity": "error"})
            continue
        current_hash = _sha256(corpus_path)
        if current_hash != item["initial_content_sha256"]:
            changed_since_start.append(relative)
        entry = ledger_documents.get(relative)
        if not isinstance(entry, dict):
            continue
        records = entry.get("claims")
        if not isinstance(records, list) or not records:
            continue
        is_reviewed = True
        for record in records:
            if not isinstance(record, dict) or record.get("review_state", record.get("status")) not in TERMINAL_REVIEW_STATES:
                is_reviewed = False
            if isinstance(record, dict) and record.get("kind") == "code_artifact" and record.get("code_kind") == "unclassified":
                unclassified += 1
        if is_reviewed:
            reviewed += 1
            cohort["reviewed"] += 1

    unique_issues: dict[tuple[str, str, str], dict[str, Any]] = {}
    for issue in relevant_issues:
        key = (str(issue.get("code", "")), str(issue.get("source", "")), str(issue.get("claim_id", "")))
        unique_issues.setdefault(key, issue)
    relevant_issues = list(unique_issues.values())
    blocking = [item for item in relevant_issues if item.get("severity", "error") == "error"]
    warnings = [item for item in relevant_issues if item.get("severity", "error") != "error"]

    blocking_by_cohort: Counter[str] = Counter()
    cohort_by_path = {item["path"]: item["cohort"] for item in wave_documents}
    global_blocking = 0
    for issue in blocking:
        cohort_name = cohort_by_path.get(str(issue.get("source", "")))
        if cohort_name is None:
            global_blocking += 1
        else:
            blocking_by_cohort[cohort_name] += 1
    for name, cohort in cohorts.items():
        cohort["pending"] = cohort["documents"] - cohort["reviewed"]
        cohort["blocking_issue_count"] = blocking_by_cohort[name] + global_blocking
        cohort["wave_ready"] = cohort["pending"] == 0 and cohort["blocking_issue_count"] == 0

    stale_evidence = sum(1 for item in blocking if item.get("code") in STALE_CODES)
    pending = len(wave_documents) - reviewed
    wave_ready = bool(wave_documents) and pending == 0 and not blocking and not warnings and unclassified == 0 and stale_evidence == 0
    return {
        "schema_version": 1,
        "wave_id": manifest.get("wave_id", wave_path.stem),
        "documents": len(wave_documents),
        "reviewed": reviewed,
        "pending": pending,
        "blocking_issue_count": len(blocking),
        "warning_count": len(warnings),
        "unclassified_code": unclassified,
        "stale_evidence": stale_evidence,
        "wave_ready": wave_ready,
        "global_release_ready": bool(global_audit.get("release_ready", False)),
        "global_reviewed": int(global_audit.get("reviewed", 0)),
        "global_pending": int(global_audit.get("pending", 0)),
        "changed_since_wave_start": changed_since_start,
        "cohorts": cohorts,
        "issues": relevant_issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="audit a bounded UE-KB corpus review wave")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "src/ue_knowledge/knowledge")
    parser.add_argument("--ledger", type=Path, default=REPO_ROOT / "validation/corpus-audit.json")
    parser.add_argument("--wave", type=Path, default=REPO_ROOT / "validation/audit-waves/wave-01-high-risk.json")
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        default=REPO_ROOT / "validation/artifacts/ue57/ue57-validation-evidence.json",
    )
    args = parser.parse_args(argv)
    payload = audit_wave(args.source, args.ledger, args.wave, evidence_manifest=args.evidence_manifest)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["wave_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
