"""Provenance metadata and corpus audit contracts.

The public corpus and a project overlay use the same metadata contract, but
their indexes remain physically separate.  Metadata is kept in a sidecar so
that provenance does not become searchable prose or leak into the published
corpus by accident.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

PROVENANCE_SCHEMA_VERSION = 1
ALLOWED_SCOPES = {"public", "project"}
ALLOWED_VERIFICATION_TYPES = {
    "engine_source",
    "epic_docs",
    "compile_test",
    "runtime_test",
    "human_required",
}
ALLOWED_CLAIM_TYPES = {"concept", "api", "runtime", "workflow", "visual"}
ALLOWED_AUDIT_STATUSES = {"pending", "verified", "blocked"}


def normalize_source(source: str) -> str:
    return source.replace("\\", "/").lstrip("./")


def stable_knowledge_id(source: str) -> str:
    """Return a path-stable identifier that does not expose local paths."""
    normalized = normalize_source(source)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"uekb.{digest}"


def public_provenance_from_ledger(
    ledger: dict[str, Any],
    ledger_sha256: str,
    *,
    scope: str = "public",
) -> dict[str, Any]:
    """Project the public sidecar deterministically from a schema-v2 ledger."""
    engine = ledger.get("engine", {}) if isinstance(ledger.get("engine"), dict) else {}
    engine_version = str(engine.get("version") or "5.7.4")
    documents: dict[str, dict[str, Any]] = {}
    for source, document in sorted((ledger.get("documents") or {}).items()):
        if not isinstance(document, dict):
            continue
        records = [item for item in document.get("claims", []) if isinstance(item, dict)]
        requirements = {
            requirement
            for item in records
            for requirement in item.get("requirements", [])
            if isinstance(requirement, str)
        }
        evidence_ids = sorted({
            identifier
            for item in records
            for identifier in item.get("evidence_ids", [])
            if isinstance(identifier, str)
        })
        validation_ids = sorted({
            identifier
            for item in records
            for identifier in item.get("validation_ids", [])
            if isinstance(identifier, str)
        })
        claim_types = sorted({
            claim_type
            for item in records
            for claim_type in item.get("claim_types", [])
            if isinstance(claim_type, str)
        })
        verification = []
        if "authoritative_source" in requirements:
            verification.append("engine_source")
        if "compile" in requirements:
            verification.append("compile_test")
        if "runtime" in requirements:
            verification.append("runtime_test")
        if "human" in requirements:
            verification.append("human_required")
        terminal = {"verified", "rewritten", "excluded"}
        complete = bool(records) and all(
            item.get("review_state", item.get("status")) in terminal for item in records
        )
        reviewed_dates = [str(item["reviewed_at"]) for item in records if item.get("reviewed_at")]
        documents[normalize_source(str(source))] = {
            "knowledge_id": stable_knowledge_id(str(source)),
            "scope": scope,
            "content_sha256": document.get("content_sha256"),
            "engine_versions": [engine_version],
            "verification": verification,
            "claim_types": claim_types,
            "verified_at": max(reviewed_dates) if reviewed_dates else None,
            "evidence_refs": evidence_ids,
            "source_ids": [],
            "validation_ids": validation_ids,
            "expires_at": None,
            "audit_status": "verified" if complete else "pending",
            "human_evidence": (
                "pass" if any(item.get("human_evidence") == "pass" for item in records)
                else "not_applicable"
            ),
        }
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "scope": scope,
        "generated_from_claim_ledger_sha256": ledger_sha256,
        "documents": documents,
    }


def _empty_payload() -> dict[str, Any]:
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "scope": "public",
        "documents": {},
    }


def resolve_provenance_path(
    source_dir: Path,
    override: str | Path | None = None,
) -> Path | None:
    """Resolve the sidecar without guessing from a repository root.

    Project corpora conventionally keep the sidecar at
    ``<source>/.ue-kb-provenance.json``.  The installed public package keeps
    it beside the bundled ``knowledge`` directory.
    """
    if override:
        return Path(override)
    local = source_dir / ".ue-kb-provenance.json"
    if local.is_file():
        return local
    sibling = source_dir.parent / "provenance.json"
    if sibling.is_file():
        return sibling
    return None


def load_provenance(
    source_dir: Path,
    provenance_path: str | Path | None = None,
) -> tuple[dict[str, Any], Path | None, list[dict[str, str]]]:
    """Load a sidecar and return ``(payload, path, load_issues)``."""
    path = resolve_provenance_path(source_dir, provenance_path)
    if path is None:
        return _empty_payload(), None, [
            {"code": "PROVENANCE_MISSING", "message": "provenance sidecar not found"}
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _empty_payload(), path, [
            {"code": "PROVENANCE_INVALID", "message": f"{type(exc).__name__}: {exc}"}
        ]
    if not isinstance(payload, dict):
        return _empty_payload(), path, [
            {"code": "PROVENANCE_INVALID", "message": "sidecar root must be an object"}
        ]
    documents = payload.get("documents", {})
    if not isinstance(documents, dict):
        return _empty_payload(), path, [
            {"code": "PROVENANCE_INVALID", "message": "documents must be an object"}
        ]
    payload.setdefault("schema_version", PROVENANCE_SCHEMA_VERSION)
    payload.setdefault("scope", "public")
    payload["documents"] = {
        normalize_source(str(key)): value for key, value in documents.items()
    }
    return payload, path, []


def metadata_for(
    source: str,
    payload: dict[str, Any],
    *,
    default_scope: str | None = None,
) -> dict[str, Any]:
    """Return normalized metadata for one Markdown source.

    Missing entries are intentionally represented as ``pending`` rather than
    silently treated as verified.  This keeps retrieval useful during the
    migration while making the release gate fail closed.
    """
    normalized = normalize_source(source)
    raw = payload.get("documents", {}).get(normalized, {})
    if not isinstance(raw, dict):
        raw = {}
    # The requested build scope is authoritative for entries that omit a
    # per-document scope. This matters for a project working index without a
    # sidecar yet; the empty payload defaults to public only for public builds.
    scope = raw.get("scope") or default_scope or payload.get("scope") or "public"
    verification = raw.get("verification", [])
    claims = raw.get("claim_types", [])
    engine_versions = raw.get("engine_versions", [])
    evidence_refs = raw.get("evidence_refs", [])
    source_ids = raw.get("source_ids", [])
    validation_ids = raw.get("validation_ids", [])
    return {
        "knowledge_id": raw.get("knowledge_id") or stable_knowledge_id(normalized),
        "scope": scope,
        "engine_versions": list(engine_versions) if isinstance(engine_versions, list) else [],
        "verification": list(verification) if isinstance(verification, list) else [],
        "claim_types": list(claims) if isinstance(claims, list) else [],
        "verified_at": raw.get("verified_at"),
        "evidence_refs": list(evidence_refs) if isinstance(evidence_refs, list) else [],
        "source_ids": list(source_ids) if isinstance(source_ids, list) else [],
        "validation_ids": list(validation_ids) if isinstance(validation_ids, list) else [],
        "content_sha256": raw.get("content_sha256"),
        "expires_at": raw.get("expires_at"),
        "audit_status": raw.get("audit_status", "pending"),
        "human_evidence": raw.get("human_evidence", "not_run"),
    }


def encode_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    """Encode structured metadata into Chroma's scalar metadata values."""
    return {
        "source": str(metadata.get("source", "")),
        "heading": str(metadata.get("heading", "")),
        "type": str(metadata.get("type", "content")),
        "kb_metadata": json.dumps(
            {key: value for key, value in metadata.items() if key not in {"source", "heading", "type"}},
            ensure_ascii=False,
            sort_keys=True,
        ),
    }


def decode_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Decode a Chroma row, tolerating rows from the pre-provenance schema."""
    raw = raw or {}
    decoded: dict[str, Any] = {
        "source": raw.get("source", "?"),
        "heading": raw.get("heading", "?"),
        "type": raw.get("type") or "content",
    }
    encoded = raw.get("kb_metadata")
    if encoded:
        try:
            extra = json.loads(encoded)
        except (TypeError, json.JSONDecodeError):
            extra = {}
        if isinstance(extra, dict):
            decoded.update(extra)
    decoded.setdefault("knowledge_id", stable_knowledge_id(str(decoded["source"])))
    decoded.setdefault("scope", "public")
    decoded.setdefault("engine_versions", [])
    decoded.setdefault("verification", [])
    decoded.setdefault("claim_types", [])
    decoded.setdefault("verified_at", None)
    decoded.setdefault("evidence_refs", [])
    decoded.setdefault("source_ids", [])
    decoded.setdefault("validation_ids", [])
    decoded.setdefault("content_sha256", None)
    decoded.setdefault("expires_at", None)
    decoded.setdefault("audit_status", "pending")
    decoded.setdefault("human_evidence", "not_run")
    return decoded


def _issue(code: str, source: str, message: str) -> dict[str, str]:
    return {"code": code, "source": source, "message": message}


def _validate_entry(
    source: str,
    entry: dict[str, Any],
    *,
    expected_scope: str,
    registry_ids: set[str] | None,
    validation_ids: set[str] | None = None,
    target_engine_version: str | None = None,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    expected_id = stable_knowledge_id(source)
    if entry.get("knowledge_id") != expected_id:
        issues.append(_issue("KNOWLEDGE_ID_MISMATCH", source, f"expected {expected_id}"))
    scope = entry.get("scope", expected_scope)
    if scope not in ALLOWED_SCOPES:
        issues.append(_issue("INVALID_SCOPE", source, f"unsupported scope: {scope!r}"))
    if expected_scope == "public" and scope != "public":
        issues.append(_issue("PUBLIC_SCOPE_LEAK", source, "public corpus entry is not public"))

    versions = entry.get("engine_versions")
    if not isinstance(versions, list) or not versions or not all(isinstance(v, str) and v.strip() for v in versions):
        issues.append(_issue("ENGINE_VERSION_MISSING", source, "engine_versions must be a non-empty list"))
    elif target_engine_version and target_engine_version not in versions:
        issues.append(_issue("ENGINE_VERSION_MISMATCH", source, f"target engine is {target_engine_version}"))

    verification = entry.get("verification")
    if not isinstance(verification, list) or not verification:
        issues.append(_issue("VERIFICATION_MISSING", source, "verification must be a non-empty list"))
    else:
        unknown = sorted(set(verification) - ALLOWED_VERIFICATION_TYPES)
        if unknown:
            issues.append(_issue("INVALID_VERIFICATION", source, ", ".join(unknown)))

    claims = entry.get("claim_types", [])
    if not isinstance(claims, list) or any(claim not in ALLOWED_CLAIM_TYPES for claim in claims):
        issues.append(_issue("INVALID_CLAIM_TYPE", source, "claim_types contains an unsupported value"))
        claims = []

    evidence = entry.get("evidence_refs")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(ref, str) and ref.strip() for ref in evidence):
        issues.append(_issue("EVIDENCE_MISSING", source, "evidence_refs must contain at least one locator"))

    verified_at = entry.get("verified_at")
    if not isinstance(verified_at, str) or not verified_at.strip():
        issues.append(_issue("VERIFIED_AT_MISSING", source, "verified_at is required"))
    else:
        try:
            date.fromisoformat(verified_at)
        except ValueError:
            issues.append(_issue("INVALID_VERIFIED_AT", source, "verified_at must be ISO YYYY-MM-DD"))

    expires_at = entry.get("expires_at")
    if expires_at:
        try:
            if date.fromisoformat(str(expires_at)) < date.today():
                issues.append(_issue("EVIDENCE_EXPIRED", source, str(expires_at)))
        except ValueError:
            issues.append(_issue("INVALID_EXPIRES_AT", source, "expires_at must be ISO YYYY-MM-DD"))

    verification_set = set(verification or [])
    if "api" in claims and "compile_test" not in verification_set:
        issues.append(_issue("COMPILE_EVIDENCE_MISSING", source, "API claims require compile_test"))
    if "runtime" in claims and "runtime_test" not in verification_set:
        issues.append(_issue("RUNTIME_EVIDENCE_MISSING", source, "runtime claims require runtime_test"))
    if "visual" in claims:
        if "human_required" not in verification_set:
            issues.append(_issue("HUMAN_GATE_MISSING", source, "visual claims require human_required"))
        if entry.get("human_evidence") != "pass":
            issues.append(_issue("HUMAN_GATE_NOT_PASSED", source, "human_evidence is not pass"))
    if not verification_set.intersection({"engine_source", "epic_docs", "compile_test", "runtime_test"}) and "human_required" not in verification_set:
        issues.append(_issue("AUTHORITATIVE_EVIDENCE_MISSING", source, "no accepted evidence type"))

    if expected_scope == "project" and registry_ids is not None:
        source_ids = entry.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(_issue("SOURCE_IDS_MISSING", source, "project entries require source_ids"))
        else:
            missing = sorted(set(source_ids) - registry_ids)
            if missing:
                issues.append(_issue("SOURCE_ID_UNKNOWN", source, ", ".join(missing)))

    linked_validation = entry.get("validation_ids", [])
    if not isinstance(linked_validation, list) or any(
        not isinstance(item, str) or not item.strip() for item in linked_validation
    ):
        issues.append(_issue("VALIDATION_LINK_INVALID", source, "validation_ids must be strings"))
        linked_validation = []
    if verification_set.intersection({"compile_test", "runtime_test"}) and not linked_validation:
        issues.append(_issue(
            "VALIDATION_LINK_MISSING",
            source,
            "compile/runtime evidence requires at least one validation_id",
        ))
    if validation_ids is not None:
        missing_validation = sorted(set(linked_validation) - validation_ids)
        if missing_validation:
            issues.append(_issue("VALIDATION_ID_UNKNOWN", source, ", ".join(missing_validation)))

    if entry.get("audit_status") != "verified":
        issues.append(_issue("AUDIT_NOT_VERIFIED", source, f"audit_status={entry.get('audit_status', 'missing')}"))
    return issues


def _registry_ids(path: Path | None) -> tuple[set[str] | None, list[dict[str, str]]]:
    if path is None:
        return None, []
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = csv.DictReader(handle, delimiter="\t")
            if not rows.fieldnames or "source_id" not in rows.fieldnames:
                return set(), [{"code": "REGISTRY_INVALID", "message": "source_id column missing"}]
            return {row.get("source_id", "") for row in rows if row.get("source_id")}, []
    except OSError as exc:
        return set(), [{"code": "REGISTRY_NOT_FOUND", "message": str(exc)}]


def audit_corpus(
    source_dir: Path,
    *,
    provenance_path: str | Path | None = None,
    scope: str = "public",
    source_registry: str | Path | None = None,
    evidence_manifest: str | Path | None = None,
    claim_ledger: str | Path | None = None,
    allow_pending: bool = False,
) -> dict[str, Any]:
    """Audit every Markdown file and return a release-gate payload.

    Public v2 provenance is a generated projection of the claim ledger.  It is
    checked for identity and hashes, while claim evidence is validated once by
    :func:`ue_knowledge.corpus_audit.audit_ledger`.  Project overlays retain
    the older independent sidecar contract because their Source Registry is a
    separate authority.
    """
    source_dir = Path(source_dir)
    payload, resolved_path, load_issues = load_provenance(source_dir, provenance_path)
    issues: list[dict[str, str]] = [{**issue, "source": "<provenance>"} for issue in load_issues]
    payload_scope = payload.get("scope")
    if payload.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        issues.append(_issue("PROVENANCE_SCHEMA_MISMATCH", "<provenance>", f"expected schema_version={PROVENANCE_SCHEMA_VERSION}"))
    if payload_scope not in ALLOWED_SCOPES:
        issues.append(_issue("INVALID_SCOPE", "<provenance>", f"unsupported scope: {payload_scope!r}"))
    elif payload_scope != scope:
        issues.append(_issue("SCOPE_MISMATCH", "<provenance>", f"sidecar scope={payload_scope!r}, requested={scope!r}"))
    if scope == "project" and source_registry is None:
        issues.append(_issue("REGISTRY_REQUIRED", "<source-registry>", "project audits require a Source Registry"))
    registry, registry_issues = _registry_ids(Path(source_registry) if source_registry else None)
    issues.extend({**issue, "source": "<source-registry>"} for issue in registry_issues)

    target_engine_version: str | None = None
    if evidence_manifest:
        try:
            evidence_payload = json.loads(Path(evidence_manifest).read_text(encoding="utf-8"))
            engine = evidence_payload.get("engine", {})
            if isinstance(engine, dict) and engine.get("version"):
                target_engine_version = str(engine["version"])
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            issues.append(_issue("EVIDENCE_MANIFEST_INVALID", "<evidence-manifest>", str(exc)))

    files = sorted(path.relative_to(source_dir).as_posix() for path in source_dir.rglob("*.md")) if source_dir.is_dir() else []
    documents = payload.get("documents", {}) if isinstance(payload.get("documents"), dict) else {}
    covered = 0
    for source in files:
        entry = documents.get(source)
        if not isinstance(entry, dict):
            issues.append(_issue("DOCUMENT_METADATA_MISSING", source, "no provenance entry"))
            continue
        covered += 1
        try:
            actual_hash = hashlib.sha256((source_dir / source).read_bytes()).hexdigest()
        except OSError as exc:
            actual_hash = None
            issues.append(_issue("CONTENT_HASH_READ_FAILED", source, str(exc)))
        if claim_ledger and actual_hash and entry.get("content_sha256") != actual_hash:
            issues.append(_issue("CONTENT_HASH_MISMATCH", source, "content_sha256 does not match Markdown"))
        if scope == "project" or not claim_ledger:
            entry_issues = _validate_entry(
                source,
                entry,
                expected_scope=scope,
                registry_ids=registry if scope == "project" else None,
                validation_ids=None,
                target_engine_version=target_engine_version,
            )
            issues.extend(entry_issues)
    extras = sorted(set(documents) - set(files))
    for source in extras:
        issues.append(_issue("PROVENANCE_ORPHAN", source, "entry does not match a Markdown file"))
    if not source_dir.is_dir():
        issues.append(_issue("CORPUS_NOT_FOUND", str(source_dir), "corpus directory not found"))

    claim_audit = None
    if claim_ledger:
        from .corpus_audit import audit_ledger

        claim_path = Path(claim_ledger)
        claim_audit = audit_ledger(
            source_dir,
            claim_path,
            evidence_manifest=Path(evidence_manifest) if evidence_manifest else None,
            target_engine_version=target_engine_version or "5.7.4",
        )
        issues.extend(claim_audit.get("issues", []))
        if scope == "public" and resolved_path:
            expected_ledger_hash = hashlib.sha256(claim_path.read_bytes()).hexdigest() if claim_path.is_file() else None
            generated_hash = payload.get("generated_from_claim_ledger_sha256")
            if expected_ledger_hash and generated_hash != expected_ledger_hash:
                issues.append(_issue("PROVENANCE_LEDGER_HASH_MISMATCH", "<provenance>", "sidecar is not generated from the current claim ledger"))
            if expected_ledger_hash:
                try:
                    ledger_payload = json.loads(claim_path.read_text(encoding="utf-8"))
                    expected_projection = public_provenance_from_ledger(
                        ledger_payload,
                        expected_ledger_hash,
                        scope="public",
                    )
                    expected_documents = expected_projection["documents"]
                    for source in files:
                        if documents.get(source) != expected_documents.get(source):
                            issues.append(_issue(
                                "PROVENANCE_PROJECTION_MISMATCH",
                                source,
                                "public sidecar entry does not match the schema-v2 claim ledger projection",
                            ))
                except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
                    issues.append(_issue(
                        "PROVENANCE_PROJECTION_INVALID",
                        "<provenance>",
                        f"cannot generate ledger projection: {type(exc).__name__}: {exc}",
                    ))

    if claim_audit is not None and scope == "public":
        verified = int(claim_audit.get("verified", 0))
        pending = max(len(files) - verified, 0)
    else:
        verified = sum(1 for source in files if isinstance(documents.get(source), dict) and documents[source].get("audit_status") == "verified")
        pending = max(len(files) - verified, 0)
    blocking = [item for item in issues if item.get("severity", "error") == "error"]
    release_ready = bool(files) and covered == len(files) and verified == len(files) and not blocking
    pending_codes = {"PROVENANCE_MISSING", "DOCUMENT_METADATA_MISSING", "ENGINE_VERSION_MISSING", "VERIFICATION_MISSING", "EVIDENCE_MISSING", "VERIFIED_AT_MISSING", "AUTHORITATIVE_EVIDENCE_MISSING", "AUDIT_NOT_VERIFIED", "COMPILE_EVIDENCE_MISSING", "RUNTIME_EVIDENCE_MISSING", "HUMAN_GATE_MISSING", "HUMAN_GATE_NOT_PASSED", "CLAIM_REVIEW_PENDING", "CLAIM_DISPOSITION_MISSING", "CODE_KIND_UNCLASSIFIED"}
    working_ready = bool(files) and covered == len(files) and not any(issue.get("code") not in pending_codes for issue in issues)
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "scope": scope,
        "source": str(source_dir.resolve()),
        "provenance_path": str(resolved_path.resolve()) if resolved_path else None,
        "documents": len(files),
        "covered": covered,
        "reviewed": int(claim_audit.get("reviewed", verified) if claim_audit else verified),
        "verified": verified,
        "pending": pending,
        "issue_count": len(blocking),
        "blocking_issue_count": len(blocking),
        "warning_count": len(issues) - len(blocking),
        "release_ready": release_ready,
        "working_ready": working_ready,
        "evidence_manifest": str(Path(evidence_manifest).resolve()) if evidence_manifest else None,
        "claim_ledger": str(Path(claim_ledger).resolve()) if claim_ledger else None,
        "claim_audit": claim_audit,
        "claim_summary": claim_audit.get("claim_summary", {}) if claim_audit else {},
        "code_summary": claim_audit.get("code_summary", {}) if claim_audit else {},
        "policy_version": claim_audit.get("policy_version", 0) if claim_audit else 0,
        "issues": issues,
    }
