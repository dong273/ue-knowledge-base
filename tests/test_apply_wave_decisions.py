import json

import pytest

from scripts.apply_wave_decisions import apply_decisions
from scripts.prepare_corpus_audit import prepare


def _inputs(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("# Method\n\nA review procedure.\n", encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    provenance = tmp_path / "provenance.json"
    prepare(corpus, ledger, provenance)
    claim_id = json.loads(ledger.read_text(encoding="utf-8"))["documents"]["doc.md"]["claims"][0]["claim_id"]
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"fixtures": [], "tests": []}), encoding="utf-8")
    wave = tmp_path / "wave.json"
    wave.write_text(json.dumps({"wave_id": "test", "documents": [{"path": "doc.md"}]}), encoding="utf-8")
    decisions = tmp_path / "decisions.json"
    return ledger, provenance, registry, wave, decisions, claim_id


def test_explicit_wave_decisions_apply_only_when_exhaustive(tmp_path):
    ledger, provenance, registry, wave, decisions, claim_id = _inputs(tmp_path)
    decisions.write_text(json.dumps({
        "wave_id": "test",
        "reviewer": "test",
        "reviewed_at": "2026-08-23",
        "evidence_catalog": {},
        "groups": [{
            "disposition": "non_claim",
            "requirements": [],
            "exclusion_reason": "Procedure, not an asserted outcome.",
            "claim_ids": [claim_id],
        }],
    }), encoding="utf-8")

    result = apply_decisions(ledger, provenance, registry, wave, decisions)

    assert result["claims"] == 1
    record = json.loads(ledger.read_text(encoding="utf-8"))["documents"]["doc.md"]["claims"][0]
    assert record["review_state"] == "excluded"
    assert record["disposition"] == "non_claim"


def test_explicit_wave_decisions_reject_missing_or_duplicate_claims(tmp_path):
    ledger, provenance, registry, wave, decisions, claim_id = _inputs(tmp_path)
    decisions.write_text(json.dumps({
        "wave_id": "test",
        "reviewer": "test",
        "reviewed_at": "2026-08-23",
        "evidence_catalog": {},
        "groups": [{
            "disposition": "non_claim",
            "requirements": [],
            "exclusion_reason": "Procedure.",
            "claim_ids": [claim_id, claim_id],
        }],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="multiple decisions"):
        apply_decisions(ledger, provenance, registry, wave, decisions)

    payload = json.loads(decisions.read_text(encoding="utf-8"))
    payload["groups"] = []
    decisions.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        apply_decisions(ledger, provenance, registry, wave, decisions)
