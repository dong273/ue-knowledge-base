"""v0.7 provenance, envelope and federated-index contracts."""

import json

import pytest

from fake_embedder import FakeEmbedder
from scripts.scaffold_provenance import scaffold
from ue_knowledge.build import build_index
from ue_knowledge.cli import main
from ue_knowledge.federation import federated_query
from ue_knowledge.metadata import audit_corpus, stable_knowledge_id
from ue_knowledge.query import coverage_for_hits, query_envelope


def _write_doc(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sidecar(root, relative, *, scope="public", claim_types=None, source_ids=None, verification=None, validation_ids=None):
    entry = {
        "knowledge_id": stable_knowledge_id(relative),
        "scope": scope,
        "engine_versions": ["5.7.4"],
        "verification": verification or ["engine_source"],
        "claim_types": claim_types or ["concept"],
        "verified_at": "2026-08-23",
        "evidence_refs": ["EngineSource:validated-symbol"],
        "source_ids": source_ids or [],
        "validation_ids": validation_ids or [],
        "audit_status": "verified",
        "human_evidence": "not_run",
    }
    path = root / ".ue-kb-provenance.json"
    path.write_text(
        json.dumps({"schema_version": 1, "scope": scope, "documents": {relative: entry}}, indent=2),
        encoding="utf-8",
    )
    return path


def test_scaffold_creates_explicit_pending_entries(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "topic/doc.md", "# Topic\n\ncontent")
    output = tmp_path / "provenance.json"
    summary = scaffold(corpus, output)
    assert summary["documents"] == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    entry = payload["documents"]["topic/doc.md"]
    assert entry["audit_status"] == "pending"
    assert entry["knowledge_id"].startswith("uekb.")


def test_audit_corpus_is_fail_closed_until_every_document_is_verified(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("engine source " * 30))

    rc = main(["audit-corpus", "--source", str(corpus), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["documents"] == 1
    assert payload["covered"] == 0
    assert payload["release_ready"] is False
    assert any(issue["code"] == "DOCUMENT_METADATA_MISSING" for issue in payload["issues"])

    _sidecar(corpus, "ue-topic/doc.md")
    rc = main(["audit-corpus", "--source", str(corpus), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["verified"] == 1
    assert payload["release_ready"] is True

    rc = main(["audit-corpus", "--source", str(corpus), "--allow-pending", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["working_ready"] is True


def test_project_audit_requires_a_source_registry(tmp_path):
    corpus = tmp_path / "project"
    _write_doc(corpus, "notes/doc.md", "# Project\n\n" + ("evidence " * 30))
    _sidecar(corpus, "notes/doc.md", scope="project", source_ids=["SRC-1"])
    payload = audit_corpus(corpus, scope="project")
    assert payload["release_ready"] is False
    assert any(issue["code"] == "REGISTRY_REQUIRED" for issue in payload["issues"])


def test_compile_evidence_requires_a_validation_link(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("engine source " * 30))
    _sidecar(
        corpus,
        "ue-topic/doc.md",
        claim_types=["api"],
        verification=["engine_source", "compile_test"],
    )
    payload = audit_corpus(corpus)
    assert payload["release_ready"] is False
    assert any(issue["code"] == "VALIDATION_LINK_MISSING" for issue in payload["issues"])


def test_strict_build_records_scope_and_provenance(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("engine source " * 30))
    _sidecar(corpus, "ue-topic/doc.md")
    db = tmp_path / "db"
    summary = build_index(
        source_dir=corpus,
        chroma_dir=db,
        model_name="fake",
        embedder=FakeEmbedder(),
        strict_provenance=True,
    )
    assert summary["scope"] == "public"
    assert summary["provenance"]["release_ready"] is True


def test_query_envelope_adds_coverage_and_metadata_without_changing_legacy(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("engine source " * 30))
    _sidecar(corpus, "ue-topic/doc.md")
    db = tmp_path / "db"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())

    envelope = query_envelope(
        "engine source", chroma_dir=db, model_name="fake", embedder=FakeEmbedder()
    )
    assert envelope["schema_version"] == 1
    assert envelope["coverage"]["status"] == "supported"
    assert envelope["scope"] == "public"
    assert envelope["hits"][0]["knowledge_id"].startswith("uekb.")
    assert envelope["hits"][0]["audit_status"] == "verified"


def test_public_no_coverage_envelope_is_an_explicit_refusal(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("generic engine pattern " * 30))
    _sidecar(corpus, "ue-topic/doc.md")
    db = tmp_path / "db"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())

    envelope = query_envelope(
        "白盒关卡首次游玩引导可发现性如何自动验证",
        chroma_dir=db,
        model_name="fake",
        embedder=FakeEmbedder(),
    )
    assert envelope["coverage"]["status"] == "none"
    assert envelope["coverage"]["reason"] == "public_scope_excludes_project_facts"
    assert envelope["hits"] == []


def test_federated_query_keeps_public_and_project_scores_separate(tmp_path):
    public = tmp_path / "public-corpus"
    project = tmp_path / "project-corpus"
    _write_doc(public, "ue-topic/public.md", "# Public\n\n" + ("generic engine pattern " * 30))
    project_relative = "project/project.md"
    _write_doc(project, project_relative, "# Project\n\n" + ("generic engine pattern private project evidence " * 30))
    _sidecar(public, "ue-topic/public.md")
    _sidecar(project, project_relative, scope="project", source_ids=["SRC-1"])

    public_db = tmp_path / "public-db"
    project_db = tmp_path / "project-db"
    build_index(source_dir=public, chroma_dir=public_db, model_name="fake", embedder=FakeEmbedder())
    build_index(
        source_dir=project,
        chroma_dir=project_db,
        model_name="fake",
        embedder=FakeEmbedder(),
        scope="project",
    )

    payload = federated_query(
        "generic engine pattern", {"public": public_db, "project": project_db},
        model_name="fake", embedder=FakeEmbedder(), top_k=2,
    )
    assert set(payload["groups"]) == {"public", "project"}
    assert payload["errors"] == {}
    assert payload["project_hits"][0]["scope"] == "project"
    assert payload["public_hits"][0]["scope"] == "public"


def test_federated_query_rejects_named_scope_mismatch(tmp_path):
    corpus = tmp_path / "corpus"
    _write_doc(corpus, "ue-topic/doc.md", "# Topic\n\n" + ("generic engine pattern " * 30))
    _sidecar(corpus, "ue-topic/doc.md")
    db = tmp_path / "db"
    build_index(source_dir=corpus, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())

    payload = federated_query(
        "generic engine pattern",
        {"project": db},
        model_name="fake",
        embedder=FakeEmbedder(),
    )
    assert payload["groups"] == {}
    assert payload["errors"]["project"]["code"] == "INDEX_SCOPE_MISMATCH"


def test_append_cannot_cross_public_and_project_scopes(tmp_path):
    public = tmp_path / "public"
    project = tmp_path / "project"
    _write_doc(public, "ue-topic/public.md", "# Public\n\n" + ("generic engine pattern " * 30))
    _write_doc(project, "project/private.md", "# Project\n\n" + ("generic engine pattern " * 30))
    _sidecar(public, "ue-topic/public.md")
    db = tmp_path / "db"
    build_index(source_dir=public, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    with pytest.raises(RuntimeError, match="cannot append across index scopes"):
        build_index(
            source_dir=project,
            chroma_dir=db,
            model_name="fake",
            embedder=FakeEmbedder(),
            scope="project",
            append=True,
        )


def test_force_cannot_replace_public_index_with_project_scope(tmp_path):
    public = tmp_path / "public"
    project = tmp_path / "project"
    _write_doc(public, "ue-topic/public.md", "# Public\n\n" + ("generic engine pattern " * 30))
    _write_doc(project, "project/private.md", "# Project\n\n" + ("generic engine pattern " * 30))
    _sidecar(public, "ue-topic/public.md")
    _sidecar(project, "project/private.md", scope="project", source_ids=["SRC-1"])
    db = tmp_path / "db"
    build_index(source_dir=public, chroma_dir=db, model_name="fake", embedder=FakeEmbedder())
    with pytest.raises(RuntimeError, match="cannot reuse an index directory across scopes"):
        build_index(
            source_dir=project,
            chroma_dir=db,
            model_name="fake",
            embedder=FakeEmbedder(),
            scope="project",
            force=True,
        )


def test_coverage_classification_requires_lexical_grounding_for_strong_result():
    assert coverage_for_hits([])["status"] == "none"
    assert coverage_for_hits([{"raw_score": 0.016, "lexical_match": False}])["status"] == "none"
    assert coverage_for_hits([{"raw_score": 0.016, "lexical_match": True}])["status"] == "weak"
    assert coverage_for_hits([{"raw_score": 0.032, "lexical_match": True}])["status"] == "supported"
    assert coverage_for_hits(
        [{"raw_score": 0.032, "lexical_match": True}],
        query_text="Z" + "SWM H1 Bead 首次游玩可发现性",
        scope="public",
    )["status"] == "none"
    assert coverage_for_hits(
        [{"raw_score": 0.032, "lexical_match": True}],
        query_text="白盒关卡首次游玩引导可发现性如何自动验证",
        scope="public",
    )["status"] == "none"
