import json

from scripts import audit_wave as audit_wave_module
from scripts.audit_wave import audit_wave
from scripts.prepare_corpus_audit import prepare


def _manifest(path, source_name, digest):
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "wave_id": "wave-test",
            "documents": [{"cohort": "A", "path": source_name, "initial_content_sha256": digest}],
        }),
        encoding="utf-8",
    )


def test_wave_gate_is_independent_from_global_release(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    selected = corpus / "selected.md"
    selected.write_text("# Checklist\n\nReviewer workflow.\n", encoding="utf-8")
    (corpus / "remaining.md").write_text("# Pending\n\nUnreviewed material.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.json"
    prepare(corpus, ledger_path, tmp_path / "provenance.json")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    record = ledger["documents"]["selected.md"]["claims"][0]
    record.update({
        "disposition": "non_claim",
        "review_state": "excluded",
        "status": "excluded",
        "reviewer": "test",
        "reviewed_at": "2026-08-23",
        "exclusion_reason": "Procedural checklist; no factual assertion.",
        "requirements": [],
        "evidence_ids": [],
        "validation_ids": [],
        "human_evidence": "not_applicable",
    })
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    wave_path = tmp_path / "wave.json"
    import hashlib
    _manifest(wave_path, "selected.md", hashlib.sha256(selected.read_bytes()).hexdigest())

    result = audit_wave(corpus, ledger_path, wave_path)

    assert result["documents"] == 1
    assert result["reviewed"] == 1
    assert result["pending"] == 0
    assert result["wave_ready"] is True
    assert result["global_release_ready"] is False
    assert result["global_pending"] == 1


def test_wave_gate_reports_unclassified_code_and_stale_ledger(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    selected = corpus / "selected.md"
    selected.write_text("# API\n\n```cpp\nFString Value;\n```\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.json"
    prepare(corpus, ledger_path, tmp_path / "provenance.json")
    wave_path = tmp_path / "wave.json"
    import hashlib
    _manifest(wave_path, "selected.md", hashlib.sha256(selected.read_bytes()).hexdigest())
    selected.write_text("# API\n\nChanged.\n\n```cpp\nFString Value;\n```\n", encoding="utf-8")

    result = audit_wave(corpus, ledger_path, wave_path)

    assert result["wave_ready"] is False
    assert result["unclassified_code"] == 1
    assert result["stale_evidence"] == 1
    assert "selected.md" in result["changed_since_wave_start"]


def test_wave_manifest_rejects_duplicate_paths(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    selected = corpus / "selected.md"
    selected.write_text("# Topic\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.json"
    prepare(corpus, ledger_path, tmp_path / "provenance.json")
    import hashlib
    digest = hashlib.sha256(selected.read_bytes()).hexdigest()
    wave_path = tmp_path / "wave.json"
    wave_path.write_text(json.dumps({
        "schema_version": 1,
        "documents": [
            {"cohort": "A", "path": "selected.md", "initial_content_sha256": digest},
            {"cohort": "A", "path": "selected.md", "initial_content_sha256": digest},
        ],
    }), encoding="utf-8")

    result = audit_wave(corpus, ledger_path, wave_path)

    assert result["wave_ready"] is False
    assert any(issue["code"] == "WAVE_PATH_DUPLICATE" for issue in result["issues"])


def test_cli_defaults_to_generated_ue_evidence(monkeypatch, capsys):
    captured = {}

    def fake_audit_wave(source, ledger, wave, *, evidence_manifest=None):
        captured["evidence_manifest"] = evidence_manifest
        return {"wave_ready": True}

    monkeypatch.setattr(audit_wave_module, "audit_wave", fake_audit_wave)

    assert audit_wave_module.main([]) == 0
    assert captured["evidence_manifest"] == (
        audit_wave_module.REPO_ROOT
        / "validation/artifacts/ue57/ue57-validation-evidence.json"
    )
    assert '"wave_ready": true' in capsys.readouterr().out
