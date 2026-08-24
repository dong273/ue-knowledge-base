"""Focused contracts for the schema-v2 trust-audit seam."""

import json

from ue_knowledge.corpus_audit import audit_ledger, scan_document, scan_corpus


def _write_ledger(tmp_path, corpus, payload):
    path = tmp_path / "corpus-audit.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _evidence(tmp_path, *, compile_id=None, test_id=None):
    payload = {
        "schema_version": 1,
        "engine": {"version": "5.7.4", "changelist": 51494982},
        "compile_validations": ([{"id": compile_id, "state": "Success"}] if compile_id else []),
        "tests": ([{"id": test_id, "state": "Success", "warnings": 0, "errors": 0}] if test_id else []),
        "validation_ids": [item for item in (compile_id, test_id) if item],
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_scanner_avoids_lowercase_u_false_positives_and_owns_artifacts():
    text = "# Topic\n\nUse unloaded uniform Unreal.\n\n```cpp\nUUserWidget* Widget;\n```\n"
    scanned = scan_document("topic/doc.md", text)
    assert scanned["claims"][0]["claim_types"] == ["concept"]
    artifact = scanned["claims"][1]
    assert artifact["kind"] == "code_artifact"
    assert artifact["parent_claim_id"] == scanned["claims"][0]["claim_id"]
    assert "code_artifacts" in scanned and scanned["code_artifacts"] == [artifact["claim_id"]]


def test_claim_ids_ignore_line_movement_but_change_with_artifact_content():
    first = scan_document("topic/doc.md", "# Topic\n\n```cpp\nUUserWidget* Widget;\n```\n")
    moved = scan_document("topic/doc.md", "# Topic\n\n\n\n```cpp\nUUserWidget* Widget;\n```\n")
    inserted = scan_document("topic/doc.md", "# Topic\n\nInserted prose.\n\n```cpp\nUUserWidget* Widget;\n```\n")
    changed = scan_document("topic/doc.md", "# Topic\n\n```cpp\nUUserWidget* OtherWidget;\n```\n")
    assert [item["claim_id"] for item in first["claims"]] == [item["claim_id"] for item in moved["claims"]]
    assert first["claims"][1]["claim_id"] == inserted["claims"][1]["claim_id"]
    assert first["claims"][1]["claim_id"] != changed["claims"][1]["claim_id"]


def test_scanner_honors_explicit_config_and_command_code_kinds():
    scanned = scan_document(
        "topic/doc.md",
        "# Topic\n\n```csharp config\nPrivateDependencyModuleNames.Add(\"UMG\");\n```\n"
        "\n```command\nue-kb build --scope public\n```\n",
    )
    artifacts = [item for item in scanned["claims"] if item["kind"] == "code_artifact"]
    assert [item["code_kind"] for item in artifacts] == ["config", "command"]


def test_pending_v2_claim_has_one_root_issue(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# Topic\n\nA concept.\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    for record in ledger["documents"]["doc.md"]["claims"]:
        record["disposition"] = "concept"
        record["review_state"] = "pending"
        record["requirements"] = ["authoritative_source"]
    ledger_path = _write_ledger(tmp_path, corpus, ledger)
    result = audit_ledger(corpus, ledger_path)
    assert result["issue_count"] == 1
    assert result["issues"][0]["code"] == "CLAIM_REVIEW_PENDING"


def test_v2_non_claim_can_pass_without_human_evidence(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# Evidence method\n\nDescribe the layers.\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    for record in ledger["documents"]["doc.md"]["claims"]:
        record.update({
            "disposition": "non_claim",
            "review_state": "excluded",
            "exclusion_reason": "method description, not a result assertion",
            "requirements": [],
        })
    result = audit_ledger(corpus, _write_ledger(tmp_path, corpus, ledger))
    assert result["release_ready"] is True
    assert result["blocking_issue_count"] == 0


def test_v2_copy_ready_artifact_requires_successful_compile(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# API\n\n```cpp\nUUserWidget* Widget;\n```\n", encoding="utf-8")
    ledger = scan_corpus(corpus)
    records = ledger["documents"]["doc.md"]["claims"]
    section, artifact = records
    section.update({
        "disposition": "non_claim",
        "review_state": "excluded",
        "exclusion_reason": "parent heading only",
        "requirements": [],
    })
    artifact.update({
        "code_kind": "copy_ready",
        "disposition": "api_contract",
        "review_state": "verified",
        "requirements": ["authoritative_source", "compile"],
        "evidence_ids": ["engine.userwidget"],
        "validation_ids": ["UEKB.Compile.InputUi"],
    })
    ledger["evidence_catalog"] = {
        "engine.userwidget": {
            "kind": "engine_source",
            "locator": "Engine/Runtime/UMG/UserWidget.h::UUserWidget",
            "covers_claims": [artifact["claim_id"]],
        }
    }
    result = audit_ledger(
        corpus,
        _write_ledger(tmp_path, corpus, ledger),
        evidence_manifest=_evidence(tmp_path, compile_id="UEKB.Compile.InputUi"),
    )
    assert result["release_ready"] is True
