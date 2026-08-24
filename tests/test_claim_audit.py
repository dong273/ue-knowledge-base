import copy
import json

from scripts.scaffold_corpus_audit import scaffold
from scripts.prepare_corpus_audit import prepare
from ue_knowledge.corpus_audit import audit_ledger, scan_corpus
from ue_knowledge.audit import TrustAudit


def _evidence(tmp_path):
    payload = {
        "schema_version": 1,
        "engine": {"version": "5.7.4", "changelist": 51494982, "root": "<UE_ENGINE_ROOT>"},
        "compile_validations": [
            {"id": "UEKB.Compile.Core", "state": "Success", "fixture_sha256": "a" * 64}
        ],
        "tests": [{"id": "UEKB.Runtime.Core", "state": "Success"}],
        "validation_ids": ["UEKB.Compile.Core", "UEKB.Runtime.Core"],
        "build_exit_code": 0,
        "automation_exit_code": 0,
        "reports": ["index.json"],
        "report_sha256": {"index.json": "b" * 64},
        "passed": True,
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_scaffold_claim_inventory_is_deterministic(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text(
        "# Topic\n\n```cpp\nFString Value;\n```\n", encoding="utf-8"
    )
    first = scan_corpus(corpus)
    second = scan_corpus(corpus)
    assert first == second
    output = tmp_path / "ledger.json"
    summary = scaffold(corpus, output)
    assert summary["documents"] == 1
    assert summary["claims"] == 2
    assert first["corpus"] == "<CORPUS_ROOT>"


def test_claim_ledger_requires_evidence_for_each_claim(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text(
        "# Topic\n\nRuntime API claim.\n\n```cpp\nFString Value;\n```\n", encoding="utf-8"
    )
    ledger = scan_corpus(corpus)
    for claim in ledger["documents"]["doc.md"]["claims"]:
        claim["status"] = "verified"
        claim["evidence_refs"] = ["EngineSource:validated"]
        claim["validation_ids"] = ["UEKB.Compile.Core", "UEKB.Runtime.Core"]
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    result = audit_ledger(corpus, ledger_path, evidence_manifest=_evidence(tmp_path))
    assert result["release_ready"] is True
    assert result["issue_count"] == 0


def test_claim_ledger_detects_changed_content_and_failed_test(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    doc = corpus / "doc.md"
    doc.write_text("# Topic\n\nRuntime behavior API claim\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    for claim in ledger["documents"]["doc.md"]["claims"]:
        claim["status"] = "verified"
        claim["evidence_refs"] = ["EpicDocs:validated"]
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    doc.write_text("# Topic\n\nchanged\n", encoding="utf-8")
    payload = json.loads(_evidence(tmp_path).read_text(encoding="utf-8"))
    payload["tests"][0]["state"] = "Failure"
    payload["validation_ids"] = ["UEKB.Compile.Core", "UEKB.Runtime.Core"]
    evidence = tmp_path / "failed.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    result = audit_ledger(corpus, ledger_path, evidence_manifest=evidence)
    assert result["release_ready"] is False
    assert any(issue["code"] == "CLAIM_CONTENT_CHANGED" for issue in result["issues"])
    assert any(issue["code"] == "CLAIM_RUNTIME_EVIDENCE_MISSING" for issue in result["issues"])


def test_claim_ledger_rejects_duplicate_and_unknown_validation_links(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# RPC API\n\nUFUNCTION Server RPC claim.\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    claim = ledger["documents"]["doc.md"]["claims"][0]
    claim["status"] = "verified"
    claim["evidence_refs"] = ["EngineSource:validated"]
    claim["validation_ids"] = ["UEKB.Compile.Unknown"]
    ledger["documents"]["doc.md"]["claims"].append(copy.deepcopy(claim))
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")

    result = audit_ledger(corpus, ledger_path, evidence_manifest=_evidence(tmp_path))
    codes = {issue["code"] for issue in result["issues"]}
    assert "CLAIM_DUPLICATE" in codes
    assert "CLAIM_VALIDATION_ID_UNKNOWN" in codes
    assert "CLAIM_COMPILE_EVIDENCE_MISSING" in codes
    assert result["release_ready"] is False


def test_failed_compile_does_not_satisfy_api_claim(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# API\n\nUFUNCTION claim.\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    for claim in ledger["documents"]["doc.md"]["claims"]:
        claim["status"] = "verified"
        claim["evidence_refs"] = ["EngineSource:validated"]
        claim["validation_ids"] = ["UEKB.Compile.Core"]
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    payload = json.loads(_evidence(tmp_path).read_text(encoding="utf-8"))
    payload["compile_validations"][0]["state"] = "Failure"
    failed = tmp_path / "failed-compile.json"
    failed.write_text(json.dumps(payload), encoding="utf-8")

    result = audit_ledger(corpus, ledger_path, evidence_manifest=failed)
    codes = {issue["code"] for issue in result["issues"]}
    assert "EVIDENCE_COMPILE_FAILED" in codes
    assert "CLAIM_COMPILE_EVIDENCE_MISSING" in codes
    assert result["release_ready"] is False


def test_prepare_preserves_manual_evidence_candidates(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "ue-networking-replication.md").write_text(
        "# RPC\n\nUFUNCTION Server RPC claim.\n", encoding="utf-8"
    )
    ledger_path = tmp_path / "ledger.json"
    scaffold(corpus, ledger_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    claim = ledger["documents"]["ue-networking-replication.md"]["claims"][0]
    claim["evidence_candidates"] = ["Manual:review-note"]
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    summary = prepare(corpus, ledger_path, tmp_path / "provenance.json")
    assert summary["documents"] == 1
    refreshed = json.loads(ledger_path.read_text(encoding="utf-8"))
    candidates = refreshed["documents"]["ue-networking-replication.md"]["claims"][0]["evidence_candidates"]
    assert "Manual:review-note" in candidates
    assert len(candidates) == len(set(candidates))


def test_trust_audit_exposes_single_scan_and_release_seam(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# Concept\n\nA short claim.\n", encoding="utf-8")
    audit = TrustAudit(corpus)
    inventory = audit.scan()
    assert inventory["schema_version"] == 2
    assert inventory["documents"]["doc.md"]["claims"]
    result = audit.run()
    assert result["documents"] == 1
    assert result["release_ready"] is False


def test_public_sidecar_must_match_generated_ledger_projection(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# Concept\n\nA short claim.\n", encoding="utf-8")
    ledger_path = tmp_path / "corpus-audit.json"
    provenance_path = corpus / ".ue-kb-provenance.json"
    prepare(corpus, ledger_path, provenance_path)
    sidecar = json.loads(provenance_path.read_text(encoding="utf-8"))
    sidecar["documents"]["doc.md"]["engine_versions"] = ["5.6.0"]
    provenance_path.write_text(json.dumps(sidecar), encoding="utf-8")

    result = TrustAudit(
        corpus,
        provenance=provenance_path,
        claim_ledger=ledger_path,
    ).run()
    assert any(
        issue["code"] == "PROVENANCE_PROJECTION_MISMATCH"
        for issue in result["issues"]
    )
