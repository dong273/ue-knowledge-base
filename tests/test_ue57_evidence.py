import json
import hashlib

from scripts.check_ue57_evidence import check


def _payload():
    return {
        "schema_version": 1,
        "validation": "UEKnowledgeValidation",
        "engine": {"version": "5.7.4", "changelist": 51494982, "root": "<UE_ENGINE_ROOT>"},
        "build_exit_code": 0,
        "automation_exit_code": 0,
        "reports": ["index.json"],
        "validation_ids": ["UEKnowledgeValidation.ActorCollisionEnableState"],
        "passed": True,
    }


def test_ue57_evidence_contract_accepts_sanitized_manifest(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    assert check(path) == []


def test_ue57_evidence_contract_rejects_absolute_paths_and_failed_runs(tmp_path):
    payload = _payload()
    payload["engine"]["root"] = "E:/UE_5.7"
    payload["automation_exit_code"] = 1
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    errors = check(path)
    assert any("exit codes" in error for error in errors)
    assert any("absolute drive path" in error for error in errors)


def test_ue57_evidence_contract_rejects_detailed_failed_or_duplicate_ids(tmp_path):
    payload = _payload()
    payload["compile_validations"] = [
        {"id": "UEKB.Compile.Core", "state": "Success", "fixture_sha256": "a" * 64}
    ]
    payload["tests"] = [{"id": "UEKB.Runtime.Core", "state": "NotRun"}]
    payload["validation_ids"] = ["UEKB.Compile.Core"]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    errors = check(path)
    assert any("did not pass" in error for error in errors)
    assert any("must equal" in error for error in errors)


def test_ue57_evidence_cross_checks_report_hash_and_test_projection(tmp_path):
    automation = tmp_path / "automation"
    automation.mkdir()
    report = {
        "tests": [
            {"fullTestPath": "UEKnowledgeValidation.ActorCollisionEnableState", "state": "Success"}
        ]
    }
    report_path = automation / "index.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    payload = _payload()
    payload["report_sha256"] = {"index.json": hashlib.sha256(report_path.read_bytes()).hexdigest()}
    payload["compile_validations"] = []
    payload["tests"] = [
        {"id": "UEKnowledgeValidation.ActorCollisionEnableState", "state": "Success"}
    ]
    payload["validation_ids"] = ["UEKnowledgeValidation.ActorCollisionEnableState"]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert check(path) == []

    report_path.write_text(json.dumps({"tests": []}), encoding="utf-8")
    errors = check(path)
    assert any("report hash mismatch" in error for error in errors)


def test_ue57_evidence_rejects_unregistered_automation_warning(tmp_path):
    payload = _payload()
    payload["tests"] = [{
        "id": "UEKnowledgeValidation.ActorCollisionEnableState",
        "state": "Success",
        "warnings": 1,
        "errors": 0,
    }]
    payload["validation_ids"] = ["UEKnowledgeValidation.ActorCollisionEnableState"]
    path = tmp_path / "warning.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    errors = check(path)
    assert any("contains warnings" in error for error in errors)


def test_ue57_evidence_checks_terminal_claim_coverage(tmp_path):
    claim_id = "uekb.test.claim"
    source_root = tmp_path / "UEKnowledgeValidation" / "Source"
    source_root.mkdir(parents=True)
    fixture_source = source_root / "Fixture.cpp"
    fixture_source.write_text("// fixture\n", encoding="utf-8")
    registry = tmp_path / "fixture-registry.json"
    registry_payload = {
        "schema_version": 2,
        "engine": {"version": "5.7.4", "changelist": 51494982},
        "fixtures": [{
            "id": "UEKB.Compile.Test",
            "source": "Source/Fixture.cpp",
            "symbols": ["TestSymbol"],
            "covers_claims": [claim_id],
        }],
        "tests": [],
    }
    registry.write_text(json.dumps(registry_payload), encoding="utf-8")
    registry_digest = hashlib.sha256(registry.read_bytes()).hexdigest()
    fixture_digest = hashlib.sha256(fixture_source.read_bytes()).hexdigest()
    payload = _payload()
    payload["fixture_registry_sha256"] = registry_digest
    payload["fixture_hashes"] = {"UEKB.Compile.Test": fixture_digest}
    payload["compile_validations"] = [{
        "id": "UEKB.Compile.Test",
        "state": "Success",
        "fixture_sha256": fixture_digest,
        "symbols": ["TestSymbol"],
        "covers_claims": [claim_id],
    }]
    payload["tests"] = []
    payload["validation_ids"] = ["UEKB.Compile.Test"]
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    ledger = tmp_path / "corpus-audit.json"
    ledger.write_text(json.dumps({
        "schema_version": 2,
        "documents": {"doc.md": {"claims": [{
            "claim_id": claim_id,
            "review_state": "verified",
            "status": "verified",
            "requirements": ["compile"],
            "validation_ids": ["UEKB.Compile.Test"],
        }]}},
    }), encoding="utf-8")
    assert check(evidence, fixture_registry=registry, claim_ledger=ledger) == []

    registry_payload["fixtures"][0]["covers_claims"] = []
    registry.write_text(json.dumps(registry_payload), encoding="utf-8")
    errors = check(evidence, fixture_registry=registry, claim_ledger=ledger)
    assert any("does not cover claim" in error for error in errors)

    registry_payload["fixtures"][0]["covers_claims"] = [claim_id]
    registry_payload["expected_failures"] = [{
        "id": "UEKB.ExpectedFailure.Test",
        "diagnostic": "expected compile diagnostic",
        "project": "UEKnowledgeValidation/Test.uproject",
        "target": "UEKBExpectedFailureEditor",
        "source": "UEKnowledgeValidation/Source/Fixture.cpp",
    }]
    registry.write_text(json.dumps(registry_payload), encoding="utf-8")
    payload["fixture_registry_sha256"] = hashlib.sha256(registry.read_bytes()).hexdigest()
    payload["expected_failures"] = [{
        "id": "UEKB.ExpectedFailure.Test",
        "state": "ExpectedFailure",
        "exit_code": 6,
        "diagnostic": "expected compile diagnostic",
        "fixture_sha256": fixture_digest,
        "matched": True,
    }]
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert check(evidence, fixture_registry=registry, claim_ledger=ledger) == []
    payload["validation_ids"] = ["UEKB.Compile.Test", "UEKB.ExpectedFailure.Test"]
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check(evidence, fixture_registry=registry, claim_ledger=ledger)
    assert any("expected failure must not be exported" in error for error in errors)
