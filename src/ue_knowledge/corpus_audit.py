"""Deterministic corpus inventory and claim/evidence audit.

The scanner is deliberately conservative: it inventories headings and fenced
blocks, but it never promotes a heuristic classification to verified evidence.
Schema v2 treats a fenced block as a ``code_artifact`` owned by its containing
section.  This keeps code coverage observable without requiring the same fact
to be proven twice (once for the section and once for the block).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .metadata import normalize_source, stable_knowledge_id

CLAIM_LEDGER_SCHEMA_VERSION = 2
AUDIT_POLICY_VERSION = 1

CLAIM_STATUSES = {"pending", "verified", "blocked", "stale", "rewritten"}
DISPOSITIONS = {"non_claim", "concept", "api_contract", "runtime_behavior", "human_outcome"}
CLAIM_KINDS = {"document", "section", "code_artifact"}
CLAIM_TYPES = {"concept", "api", "runtime", "visual", "workflow"}
CODE_KINDS = {"copy_ready", "fragment", "pseudocode", "config", "command", "output", "unclassified"}
HUMAN_EVIDENCE_STATES = {"not_applicable", "not_run", "pass", "fail"}
REQUIREMENTS = {"authoritative_source", "compile", "runtime", "human"}

# Do not use IGNORECASE for the Unreal identifier rule.  The previous
# ``U[A-Z]`` rule was case-insensitive and classified ordinary words such as
# ``Use`` and ``unloaded`` as API claims.
_API_EXACT_RE = re.compile(
    r"\b(?:UCLASS|USTRUCT|UENUM|UFUNCTION|UPROPERTY|Build\.cs|Target\.cs|"
    r"GameplayAbility|AbilitySystem|RPC|Replicated|FGameplay)\b"
)
_API_IDENTIFIER_RE = re.compile(r"\b(?:U[A-Z][A-Za-z0-9_]+|F[A-Z][A-Za-z0-9_]+)\b")
_API_WORD_RE = re.compile(
    r"\b(?:gameplay\s+ability|ability\s+system|server\s+rpc|module\s+dependency|"
    r"replication\s+contract|build\.cs|target\.cs)\b", re.IGNORECASE
)
_RUNTIME_RE = re.compile(
    r"\b(?:runtime\s+behavior|runtime\s+test|fresh\s+PIE|Automation\s+Test|"
    r"OnRep_[A-Za-z0-9_]+|BeginPlay\b|replicat(?:e|ion|ed)\s+(?:state|property|actor))\b|"
    r"运行行为|运行测试|Fresh\s*PIE|自动化测试",
    re.IGNORECASE,
)
_VISUAL_RE = re.compile(
    r"\b(?:visual\s+acceptance|human\s+walkthrough|discoverability|pixel\s+check|"
    r"user-visible\s+result)\b|人工验收|人工走查|可发现性|像素检查",
    re.IGNORECASE,
)
_FRAGMENT_RE = re.compile(
    r"\.\.\.|<[^>]+>|\b(?:My|Your|Project|Example)[A-Z][A-Za-z0-9_]*\b|"
    r"\bTODO\b|/\*.*?\*/|//\s*\.\.\.",
    re.IGNORECASE | re.DOTALL,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "document"


def _normalise_code(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def claim_id(knowledge_id: str, kind: str, locator: str, *, content: str | None = None) -> str:
    """Return an ID stable across line movement.

    Section IDs use a semantic heading path.  Artifact IDs additionally use a
    body digest so that changing a code sample forces a new review record.
    The legacy ``locator`` argument remains accepted for callers from v0.6.
    """
    semantic = re.sub(r"@L\d+(?:-L\d+)?$", "", str(locator))
    material = f"{knowledge_id}|{kind}|{semantic}"
    if content is not None:
        material += f"|{sha256_text(_normalise_code(content))}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{knowledge_id}.c{digest}"


def _claim_types(text: str) -> list[str]:
    types: list[str] = []
    if _API_EXACT_RE.search(text) or _API_IDENTIFIER_RE.search(text) or _API_WORD_RE.search(text):
        types.append("api")
    if _RUNTIME_RE.search(text):
        types.append("runtime")
    if _VISUAL_RE.search(text):
        types.append("visual")
    if not types:
        types.append("concept")
    return types


def _iter_fenced_blocks(lines: list[str]) -> Iterable[dict[str, Any]]:
    in_block = False
    start = 0
    info = ""
    body: list[str] = []
    for index, line in enumerate(lines, start=1):
        match = re.match(r"^\s*```\s*([^`]*)$", line)
        if match and not in_block:
            in_block = True
            start = index
            info = match.group(1).strip().lower()
            body = []
            continue
        if match and in_block:
            yield {
                "start_line": start,
                "end_line": index,
                "info": info,
                "text": "\n".join(body),
            }
            in_block = False
            continue
        if in_block:
            body.append(line)
    if in_block:
        yield {
            "start_line": start,
            "end_line": len(lines),
            "info": info,
            "text": "\n".join(body),
            "unterminated": True,
        }


def _heading_records(lines: list[str]) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    sibling_counts: Counter[tuple[str, ...]] = Counter()
    for index, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        level = len(match.group(1))
        heading = match.group(2)
        while stack and stack[-1][0] >= level:
            stack.pop()
        base_path = tuple(item[1] for item in stack) + (_slug(heading),)
        sibling_counts[base_path] += 1
        semantic_path = base_path
        if sibling_counts[base_path] > 1:
            semantic_path = base_path[:-1] + (f"{base_path[-1]}-{sibling_counts[base_path]}",)
        stack.append((level, semantic_path[-1]))
        headings.append({
            "line": index,
            "level": level,
            "heading": heading,
            "path": semantic_path,
        })
    return headings


def _code_kind(info: str, body: str, unterminated: bool = False) -> str:
    tokens = set(re.split(r"[\s,;]+", info.lower()))
    if "pseudocode" in tokens or "pseudo" in tokens:
        return "pseudocode"
    if "fragment" in tokens or "snippet" in tokens:
        return "fragment"
    if unterminated or _FRAGMENT_RE.search(body):
        return "fragment"
    if tokens.intersection({"config", "ini", "json", "yaml", "yml", "toml", "csv"}):
        return "config"
    if tokens.intersection({"command", "bash", "sh", "shell", "powershell", "pwsh", "cmd"}):
        return "command"
    if tokens.intersection({"text", "output", "log", "console"}):
        return "output"
    # A C++ block without an explicit fragment marker is intentionally left
    # unclassified until a reviewer decides it is copy-ready or a fragment.
    return "unclassified"


def _prose_without_fences(lines: list[str], start: int, end: int) -> str:
    """Return section prose without child code bodies.

    A parent section owns its artifacts; inheriting every identifier from a
    nested fence would recreate the old double-counted API obligation.
    """
    output: list[str] = []
    in_block = False
    for line in lines[start - 1:end]:
        if re.match(r"^\s*```", line):
            in_block = not in_block
            continue
        if not in_block:
            output.append(line)
    return "\n".join(output)


def scan_document(source: str, text: str) -> dict[str, Any]:
    """Inventory semantic sections and owned code artifacts.

    ``claims`` is retained as the v0.6-compatible flat inventory name.  Its
    code entries have ``kind=code_artifact`` and never receive an independent
    section-level evidence obligation in the v2 audit.
    """
    normalized = normalize_source(source)
    knowledge = stable_knowledge_id(normalized)
    lines = text.splitlines()
    headings = _heading_records(lines)
    records: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []

    if headings:
        for ordinal, heading in enumerate(headings):
            start = int(heading["line"])
            end = (int(headings[ordinal + 1]["line"]) - 1) if ordinal + 1 < len(headings) else len(lines)
            locator = f"heading:{'/'.join(heading['path'])}@L{start}-L{end}"
            section = {
                "claim_id": claim_id(knowledge, "section", f"heading:{'/'.join(heading['path'])}"),
                "kind": "section",
                "locator": locator,
                "heading": heading["heading"],
                "heading_path": list(heading["path"]),
                "claim_types": _claim_types(_prose_without_fences(lines, start, end)),
                "status": "pending",
                "evidence_refs": [],
                "validation_ids": [],
                "human_evidence": "not_run",
            }
            sections.append(section)
            records.append(section)
    else:
        section = {
            "claim_id": claim_id(knowledge, "document", "document"),
            "kind": "document",
            "locator": "document",
            "heading": "",
            "heading_path": [],
            "claim_types": _claim_types(text),
            "status": "pending",
            "evidence_refs": [],
            "validation_ids": [],
            "human_evidence": "not_run",
        }
        sections.append(section)
        records.append(section)

    artifacts: list[dict[str, Any]] = []
    artifact_ids: set[str] = set()
    duplicate_artifacts: Counter[str] = Counter()
    for ordinal, block in enumerate(_iter_fenced_blocks(lines)):
        body = str(block["text"])
        info = str(block["info"])
        if not info and not body.strip():
            continue
        parent = sections[0]
        for candidate in sections:
            match = re.search(r"@L(\d+)-L(\d+)$", candidate["locator"])
            if match and int(match.group(1)) <= int(block["start_line"]) <= int(match.group(2)):
                parent = candidate
        language = info.split()[0] if info else ""
        artifact_claim_id = claim_id(
            knowledge,
            "code_artifact",
            f"artifact:{parent['claim_id']}:{language}",
            content=body,
        )
        # Identical duplicate fences need a deterministic tie-breaker for the
        # flat compatibility list, but ordinary line movement or insertion of
        # other fences does not change the parent/language/body-derived ID.
        duplicate_artifacts[artifact_claim_id] += 1
        if artifact_claim_id in artifact_ids:
            artifact_claim_id = claim_id(
                knowledge,
                "code_artifact",
                f"artifact:{parent['claim_id']}:{language}:duplicate-{duplicate_artifacts[artifact_claim_id]}",
                content=body,
            )
        artifact_ids.add(artifact_claim_id)
        artifact = {
            "claim_id": artifact_claim_id,
            "kind": "code_artifact",
            "parent_claim_id": parent["claim_id"],
            "locator": f"fence:{ordinal}@L{block['start_line']}-L{block['end_line']}",
            "language": language,
            "code_kind": _code_kind(info, body, bool(block.get("unterminated"))),
            "claim_types": _claim_types(body),
            "status": "pending",
            "evidence_refs": [],
            "validation_ids": [],
            "human_evidence": "not_run",
        }
        artifacts.append(artifact)
        records.append(artifact)

    return {
        "source": normalized,
        "knowledge_id": knowledge,
        "content_sha256": sha256_text(text),
        "claims": records,
        "sections": [item["claim_id"] for item in sections],
        "code_artifacts": [item["claim_id"] for item in artifacts],
    }


def scan_corpus(source_dir: Path) -> dict[str, Any]:
    source_dir = Path(source_dir)
    documents: dict[str, dict[str, Any]] = {}
    if source_dir.is_dir():
        for path in sorted(source_dir.rglob("*.md")):
            source = path.relative_to(source_dir).as_posix()
            raw = path.read_bytes()
            document = scan_document(source, raw.decode("utf-8"))
            document["content_sha256"] = sha256_bytes(raw)
            documents[source] = document
    return {
        "schema_version": CLAIM_LEDGER_SCHEMA_VERSION,
        "policy_version": AUDIT_POLICY_VERSION,
        "corpus": "<CORPUS_ROOT>",
        "engine": {"version": "5.7.4", "changelist": 51494982},
        "evidence_catalog": {},
        "documents": documents,
    }


def load_ledger(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [{"code": "CLAIM_LEDGER_INVALID", "message": f"{type(exc).__name__}: {exc}"}]
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), dict):
        return None, [{"code": "CLAIM_LEDGER_INVALID", "message": "documents must be an object"}]
    version = payload.get("schema_version")
    if version not in {1, CLAIM_LEDGER_SCHEMA_VERSION}:
        return None, [{"code": "CLAIM_LEDGER_SCHEMA_MISMATCH", "message": "unsupported claim ledger schema"}]
    return payload, []


def _issue(code: str, source: str, message: str, *, severity: str = "error", claim_id_value: str | None = None) -> dict[str, str]:
    item = {"code": code, "source": source, "message": message, "severity": severity}
    if claim_id_value:
        item["claim_id"] = claim_id_value
    return item


def _evidence_ids(path: Path | None) -> tuple[set[str], set[str], dict[str, Any] | None, list[dict[str, str]]]:
    if path is None:
        return set(), set(), None, []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return set(), set(), None, [{"code": "EVIDENCE_MANIFEST_INVALID", "message": f"{type(exc).__name__}: {exc}"}]
    if not isinstance(payload, dict):
        return set(), set(), None, [{"code": "EVIDENCE_MANIFEST_INVALID", "message": "manifest root must be an object"}]
    issues: list[dict[str, str]] = []
    compile_ids: set[str] = set()
    test_ids: set[str] = set()
    for field, target, label in (("compile_validations", compile_ids, "compile"), ("tests", test_ids, "test")):
        values = payload.get(field, [])
        if not isinstance(values, list):
            issues.append({"code": f"EVIDENCE_{label.upper()}S_INVALID", "message": f"{field} must be a list"})
            continue
        for item in values:
            if not isinstance(item, dict) or not item.get("id"):
                issues.append({"code": f"EVIDENCE_{label.upper()}_INVALID", "message": f"{field} entries require id"})
                continue
            identifier = str(item["id"])
            if item.get("state") == "Success":
                target.add(identifier)
            else:
                issues.append({"code": f"EVIDENCE_{label.upper()}_FAILED", "message": identifier})
    if not payload.get("compile_validations") and not payload.get("tests"):
        for item in payload.get("validation_ids", []):
            if isinstance(item, str) and item.strip():
                compile_ids.add(item)
    engine = payload.get("engine", {})
    if not isinstance(engine, dict) or engine.get("version") != "5.7.4" or engine.get("changelist") != 51494982:
        issues.append({"code": "ENGINE_VERSION_MISMATCH", "message": "expected UE 5.7.4 / CL 51494982"})
    return compile_ids, test_ids, payload, issues


def _catalog(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = entry.get("evidence_catalog", {})
    return raw if isinstance(raw, dict) else {}


def _result(scanned: dict[str, Any], verified: int, claim_count: int, issues: list[dict[str, str]], *, ledger_path: Path | None, policy_version: int) -> dict[str, Any]:
    unique: dict[tuple[str, str, str | None], dict[str, str]] = {}
    for item in issues:
        key = (item.get("code", ""), item.get("source", ""), item.get("claim_id"))
        unique.setdefault(key, item)
    issues = list(unique.values())
    blocking = [item for item in issues if item.get("severity", "error") == "error"]
    documents = len(scanned.get("documents", {}))
    covered = documents - sum(1 for item in blocking if item.get("code") == "CLAIM_DOCUMENT_MISSING")
    return {
        "documents": documents,
        "covered": covered,
        "reviewed": verified,
        "claims": claim_count,
        "verified": verified,
        "pending": max(documents - verified, 0),
        "issue_count": len(issues),
        "blocking_issue_count": len(blocking),
        "warning_count": len(issues) - len(blocking),
        "claim_summary": {},
        "code_summary": {},
        "policy_version": policy_version,
        "release_ready": bool(documents) and verified == documents and not blocking,
        "ledger": str(ledger_path.resolve()) if ledger_path else None,
        "issues": issues,
    }


def _legacy_audit(source_dir: Path, ledger: dict[str, Any], *, evidence_manifest: Path | None, target_engine_version: str, today: date) -> dict[str, Any]:
    """Validate v1 ledgers for a non-breaking migration window."""
    compile_ids, test_ids, _evidence, evidence_issues = _evidence_ids(evidence_manifest)
    issues = [_issue(item["code"], "<evidence-manifest>", item["message"]) for item in evidence_issues]
    scanned = scan_corpus(source_dir)
    docs = ledger.get("documents", {})
    verified = 0
    claim_count = 0
    for source, actual in scanned["documents"].items():
        entry = docs.get(source)
        if not isinstance(entry, dict):
            issues.append(_issue("CLAIM_DOCUMENT_MISSING", source, "no claim ledger entry"))
            continue
        if entry.get("content_sha256") != actual["content_sha256"]:
            issues.append(_issue("CLAIM_CONTENT_CHANGED", source, "ledger hash does not match Markdown"))
        records = entry.get("claims")
        actual_by_id = {item["claim_id"]: item for item in actual["claims"]}
        if not isinstance(records, list):
            issues.append(_issue("CLAIMS_INVALID", source, "claims must be a list"))
            continue
        raw_ids = [item.get("claim_id") for item in records if isinstance(item, dict)]
        for duplicate in sorted({item for item in raw_ids if item and raw_ids.count(item) > 1}):
            issues.append(_issue("CLAIM_DUPLICATE", source, str(duplicate), claim_id_value=duplicate))
        ledger_ids = {item for item in raw_ids if item}
        for missing in sorted(set(actual_by_id) - ledger_ids):
            issues.append(_issue("CLAIM_MISSING", source, missing, claim_id_value=missing))
        for orphan in sorted(ledger_ids - set(actual_by_id)):
            issues.append(_issue("CLAIM_ORPHAN", source, orphan, claim_id_value=orphan))
        doc_ok = True
        for record in records:
            if not isinstance(record, dict) or record.get("claim_id") not in actual_by_id:
                doc_ok = False
                issues.append(_issue("CLAIM_INVALID", source, "claim is missing or orphaned"))
                continue
            claim_count += 1
            claim_id_value = record.get("claim_id")
            linked = record.get("validation_ids", [])
            refs = record.get("evidence_refs", [])
            if record.get("status") not in {"verified", "rewritten"}:
                issues.append(_issue("CLAIM_NOT_VERIFIED", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
            if not isinstance(refs, list) or not refs:
                issues.append(_issue("CLAIM_EVIDENCE_MISSING", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
            linked = linked if isinstance(linked, list) else []
            if set(linked) - compile_ids - test_ids:
                issues.append(_issue("CLAIM_VALIDATION_ID_UNKNOWN", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
            types = set(record.get("claim_types", []))
            if "api" in types and not set(linked).intersection(compile_ids):
                issues.append(_issue("CLAIM_COMPILE_EVIDENCE_MISSING", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
            if "runtime" in types and not set(linked).intersection(test_ids):
                issues.append(_issue("CLAIM_RUNTIME_EVIDENCE_MISSING", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
            if "visual" in types and record.get("human_evidence") != "pass":
                issues.append(_issue("CLAIM_HUMAN_GATE_NOT_PASSED", source, str(claim_id_value), claim_id_value=claim_id_value))
                doc_ok = False
        if doc_ok:
            verified += 1
    return _result(scanned, verified, claim_count, issues, ledger_path=None, policy_version=0)


def _v2_audit(source_dir: Path, ledger: dict[str, Any], ledger_path: Path, *, evidence_manifest: Path | None, target_engine_version: str, today: date) -> dict[str, Any]:
    scanned = scan_corpus(source_dir)
    compile_ids, test_ids, _evidence, evidence_issues = _evidence_ids(evidence_manifest)
    issues = [_issue(item["code"], "<evidence-manifest>", item["message"]) for item in evidence_issues]
    docs = ledger.get("documents", {})
    catalog = _catalog(ledger)
    verified = 0
    claim_count = 0
    summary = Counter()
    code_summary = Counter()
    for source, actual in scanned["documents"].items():
        entry = docs.get(source)
        if not isinstance(entry, dict):
            issues.append(_issue("CLAIM_DOCUMENT_MISSING", source, "no claim ledger entry"))
            continue
        if entry.get("content_sha256") != actual["content_sha256"]:
            issues.append(_issue("CLAIM_CONTENT_CHANGED", source, "ledger hash does not match Markdown"))
        records = entry.get("claims")
        actual_by_id = {item["claim_id"]: item for item in actual["claims"]}
        if not isinstance(records, list):
            issues.append(_issue("CLAIMS_INVALID", source, "claims must be a list"))
            continue
        record_by_id = {item.get("claim_id"): item for item in records if isinstance(item, dict)}
        for missing in sorted(set(actual_by_id) - set(record_by_id)):
            issues.append(_issue("CLAIM_MISSING", source, missing, claim_id_value=missing))
        for orphan in sorted(set(record_by_id) - set(actual_by_id)):
            issues.append(_issue("CLAIM_ORPHAN", source, orphan, claim_id_value=orphan))
        doc_ok = True
        for claim_id_value, record in record_by_id.items():
            if claim_id_value not in actual_by_id or not isinstance(record, dict):
                doc_ok = False
                continue
            actual_record = actual_by_id[claim_id_value]
            claim_count += 1
            kind = record.get("kind")
            if kind != actual_record.get("kind"):
                issues.append(_issue("CLAIM_KIND_MISMATCH", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            if kind == "code_artifact":
                code_kind = record.get("code_kind")
                code_summary[str(code_kind)] += 1
                if code_kind not in CODE_KINDS or code_kind == "unclassified":
                    issues.append(_issue("CODE_KIND_UNCLASSIFIED", source, claim_id_value, claim_id_value=claim_id_value))
                    doc_ok = False
                if record.get("parent_claim_id") not in record_by_id:
                    issues.append(_issue("CODE_PARENT_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                    doc_ok = False
            disposition = record.get("disposition")
            summary[str(disposition)] += 1
            if disposition not in DISPOSITIONS:
                issues.append(_issue("CLAIM_DISPOSITION_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            status = record.get("review_state", record.get("status"))
            if status not in {"verified", "rewritten", "excluded"}:
                issues.append(_issue("CLAIM_REVIEW_PENDING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
                # A pending review is one root cause.  Do not cascade the
                # candidate's currently empty evidence/validation fields into
                # several duplicate errors; those checks run once a reviewer
                # has promoted the record to a terminal state.
                continue
            if disposition == "non_claim":
                if not str(record.get("exclusion_reason", "")).strip():
                    issues.append(_issue("NON_CLAIM_REASON_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                    doc_ok = False
                continue
            requirements = record.get("requirements", [])
            if not isinstance(requirements, list) or any(item not in REQUIREMENTS for item in requirements):
                issues.append(_issue("CLAIM_REQUIREMENTS_INVALID", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
                requirements = []
            evidence_ids = record.get("evidence_ids", [])
            if not isinstance(evidence_ids, list):
                evidence_ids = []
            if "authoritative_source" in requirements and not evidence_ids:
                issues.append(_issue("CLAIM_EVIDENCE_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            for evidence_id in evidence_ids:
                item = catalog.get(evidence_id)
                if not isinstance(item, dict):
                    issues.append(_issue("EVIDENCE_ID_UNKNOWN", source, evidence_id, claim_id_value=claim_id_value))
                    doc_ok = False
                    continue
                covered = item.get("covers_claims", [])
                if claim_id_value not in covered:
                    issues.append(_issue("EVIDENCE_COVERAGE_MISSING", source, evidence_id, claim_id_value=claim_id_value))
                    doc_ok = False
                expires_at = item.get("expires_at")
                if expires_at:
                    try:
                        if date.fromisoformat(str(expires_at)) < today:
                            issues.append(_issue("EVIDENCE_EXPIRED", source, evidence_id, claim_id_value=claim_id_value))
                            doc_ok = False
                    except ValueError:
                        issues.append(_issue("EVIDENCE_EXPIRY_INVALID", source, evidence_id, claim_id_value=claim_id_value))
                        doc_ok = False
            linked = record.get("validation_ids", [])
            if not isinstance(linked, list) or any(not isinstance(item, str) or not item.strip() for item in linked):
                issues.append(_issue("VALIDATION_LINK_INVALID", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
                linked = []
            if "compile" in requirements and not set(linked).intersection(compile_ids):
                issues.append(_issue("COMPILE_EVIDENCE_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            if "runtime" in requirements and not set(linked).intersection(test_ids):
                issues.append(_issue("RUNTIME_EVIDENCE_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            unknown = sorted(set(linked) - compile_ids - test_ids)
            if unknown:
                issues.append(_issue("VALIDATION_ID_UNKNOWN", source, ", ".join(unknown), claim_id_value=claim_id_value))
                doc_ok = False
            human = record.get("human_evidence", "not_applicable")
            if human not in HUMAN_EVIDENCE_STATES:
                issues.append(_issue("HUMAN_EVIDENCE_INVALID", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            if "human" in requirements and human != "pass":
                issues.append(_issue("HUMAN_GATE_NOT_PASSED", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
            if kind == "code_artifact" and record.get("language") in {"cpp", "c++", "h", "c"} and record.get("code_kind") == "copy_ready" and "compile" not in requirements:
                issues.append(_issue("COPY_READY_COMPILE_REQUIREMENT_MISSING", source, claim_id_value, claim_id_value=claim_id_value))
                doc_ok = False
        if doc_ok:
            verified += 1
    result = _result(scanned, verified, claim_count, issues, ledger_path=ledger_path, policy_version=ledger.get("policy_version", AUDIT_POLICY_VERSION))
    result["claim_summary"] = dict(summary)
    result["code_summary"] = dict(code_summary)
    return result


def audit_ledger(
    source_dir: Path,
    ledger_path: Path,
    *,
    evidence_manifest: Path | None = None,
    target_engine_version: str = "5.7.4",
    today: date | None = None,
) -> dict[str, Any]:
    """Audit a v2 ledger, retaining a v1 compatibility path."""
    source_dir = Path(source_dir)
    ledger, load_issues = load_ledger(Path(ledger_path))
    if ledger is None:
        scanned = scan_corpus(source_dir)
        return _result(
            scanned,
            0,
            0,
            [_issue(item["code"], "<claim-ledger>", item["message"]) for item in load_issues],
            ledger_path=Path(ledger_path),
            policy_version=0,
        )
    now = today or date.today()
    if ledger.get("schema_version") == 1:
        return _legacy_audit(source_dir, ledger, evidence_manifest=evidence_manifest, target_engine_version=target_engine_version, today=now)
    has_v2_records = any(
        isinstance(record, dict) and "disposition" in record
        for document in ledger.get("documents", {}).values()
        if isinstance(document, dict)
        for record in document.get("claims", [])
        if isinstance(record, dict)
    )
    if not has_v2_records:
        return _legacy_audit(source_dir, ledger, evidence_manifest=evidence_manifest, target_engine_version=target_engine_version, today=now)
    return _v2_audit(source_dir, ledger, Path(ledger_path), evidence_manifest=evidence_manifest, target_engine_version=target_engine_version, today=now)
