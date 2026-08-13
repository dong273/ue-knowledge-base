"""Machine-readable console-script contracts for every command."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fake_embedder import FakeEmbedder
from ue_knowledge.build import build_index
from ue_knowledge.cli import main


def _json_stdout(capsys):
    captured = capsys.readouterr()
    return json.loads(captured.out), captured.err


def test_build_json_failure_is_one_stable_object(capsys):
    rc = main([
        "build", "--source", "C:/definitely/not/here",
        "--db", "C:/ascii_uekb/db", "--json",
    ])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["code"] == "CORPUS_NOT_FOUND"
    assert set(payload) == {"code", "message", "action"}


def test_query_json_failure_is_parseable(capsys, tmp_path):
    rc = main(["query", "anything", "--db", str(tmp_path / "missing"), "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["code"] == "INDEX_NOT_FOUND"
    assert payload["action"] == "ue-kb build"


def test_info_json_success_exposes_manifest(capsys, tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text(
        "# Movement\n\n" + ("movement speed braking " * 30), encoding="utf-8"
    )
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )

    rc = main(["info", "--db", str(db), "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 0
    assert payload["manifest"]["schema_version"] == 2
    assert payload["stale"] is False
    assert payload["model_matches"] is True


def test_query_profile_flag_reaches_query(monkeypatch, capsys):
    called = {}

    def fake_query(*args, **kwargs):
        called.update(kwargs)
        return [{"source": "s", "heading": "h", "score": 1.0, "text": "t"}]

    monkeypatch.setattr("ue_knowledge.cli.query", fake_query)
    rc = main(["query", "x", "--profile", "vector", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 0
    assert isinstance(payload, list)
    assert called["profile"] == "vector"


def test_console_script_json_failure_has_no_stdout_noise(tmp_path):
    result = subprocess.run(
        [
            sys.executable, "-m", "ue_knowledge.cli", "query", "anything",
            "--db", str(tmp_path / "missing"), "--json",
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=30,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["code"] == "INDEX_NOT_FOUND"


def test_console_script_info_json_success(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text(
        "# Topic\n\n" + ("movement speed braking " * 30), encoding="utf-8"
    )
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    result = subprocess.run(
        [
            sys.executable, "-m", "ue_knowledge.cli", "info",
            "--db", str(db), "--model", "fake", "--json",
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["manifest"]["schema_version"] == 2
    assert payload["model_matches"] is True


def test_download_model_json_success(monkeypatch, capsys):
    monkeypatch.setattr("ue_knowledge.cli._download_model_once", lambda _name: None)
    rc = main(["download-model", "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 0
    assert payload == {"model": "fake", "cached": True}


def test_offline_env_is_restored_after_build_failure(tmp_path):
    previous = os.environ.pop("HF_HUB_OFFLINE", None)
    try:
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "doc.md").write_text(
            "# Topic\n\n" + ("enough body " * 30), encoding="utf-8"
        )

        class Broken(FakeEmbedder):
            def encode(self, texts, **kwargs):
                assert os.environ["HF_HUB_OFFLINE"] == "1"
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            build_index(
                source_dir=corpus, chroma_dir=tmp_path / "db",
                model_name="fake", embedder=Broken(), offline=True,
            )
        assert "HF_HUB_OFFLINE" not in os.environ
    finally:
        if previous is not None:
            os.environ["HF_HUB_OFFLINE"] = previous
