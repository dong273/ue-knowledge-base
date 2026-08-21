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


def test_doctor_json_reports_runtime_and_missing_index(capsys, tmp_path):
    rc = main(["doctor", "--db", str(tmp_path / "missing"), "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["schema_version"] == 1
    assert payload["ok"] is False
    assert payload["package"]["module_path"].endswith("__init__.py")
    assert payload["package"]["corpus_path"]
    assert payload["index"]["ready"] is False
    assert payload["mcp"]["checked"] is False


def test_doctor_mcp_smoke_reports_tools_and_ready_index(capsys, tmp_path):
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

    rc = main([
        "doctor", "--db", str(db), "--model", "fake",
        "--mcp-smoke", "--json",
    ])
    payload, _ = _json_stdout(capsys)
    assert rc == 0
    assert payload["ok"] is True
    assert payload["mcp"]["checked"] is True
    assert payload["mcp"]["info_ready"] is True
    assert payload["mcp"]["tools"] == [
        "ue_kb_query", "ue_kb_info", "ue_kb_topics", "ue_kb_glossary",
    ]
    assert payload["mcp"]["tools_complete"] is True


def test_doctor_json_reports_model_mismatch(capsys, tmp_path):
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

    rc = main(["doctor", "--db", str(db), "--model", "other", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["index"]["ready"] is True
    assert payload["index"]["model_matches"] is False
    assert payload["ok"] is False


def test_doctor_json_reports_stale_corpus(capsys, tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    document = corpus / "doc.md"
    document.write_text("# Movement\n\n" + ("movement speed braking " * 30), encoding="utf-8")
    db = tmp_path / "db"
    build_index(
        source_dir=corpus, chroma_dir=db,
        model_name="fake", embedder=FakeEmbedder(),
    )
    document.write_text("# Movement\n\nchanged", encoding="utf-8")

    rc = main(["doctor", "--db", str(db), "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["index"]["corpus"]["stale"] is True
    assert payload["ok"] is False


def test_doctor_json_reports_non_ascii_index_path(capsys, tmp_path):
    rc = main(["doctor", "--db", str(tmp_path / "索引"), "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    assert payload["ok"] is False
    assert payload["index"]["error"]["code"] == "INVALID_INDEX_PATH"
    assert payload["index"]["corpus"]["stale"] is None


def test_doctor_package_identity_matches_ci_install_mode(capsys, tmp_path):
    mode = os.environ.get("UE_KB_EXPECT_PACKAGE_MODE")
    if not mode:
        pytest.skip("CI install mode not requested")

    rc = main(["doctor", "--db", str(tmp_path / "missing"), "--model", "fake", "--json"])
    payload, _ = _json_stdout(capsys)
    assert rc == 1
    module_path = Path(payload["package"]["module_path"])
    if mode == "source":
        assert module_path.is_relative_to(Path(__file__).resolve().parents[1] / "src")
    elif mode == "wheel":
        assert "site-packages" in str(module_path).lower()
    else:
        raise AssertionError(f"unknown install mode: {mode}")


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
        encoding="utf-8",  # the CLI always emits UTF-8 (reconfigured in main)
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
        encoding="utf-8",  # the CLI always emits UTF-8 (reconfigured in main)
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


def test_console_script_json_works_under_legacy_encoding(tmp_path):
    """The CLI must emit parseable UTF-8 JSON even when the environment
    forces a legacy code page (en-US Windows runners are cp1252, many
    Chinese systems are gbk). Printing Chinese payloads to such a pipe used
    to raise UnicodeEncodeError and kill the CLI with a traceback."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    result = subprocess.run(
        [
            sys.executable, "-m", "ue_knowledge.cli", "query", "anything",
            "--db", str(tmp_path / "missing"), "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",  # the CLI always emits UTF-8 (reconfigured in main)
        env=env,
        timeout=30,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["code"] == "INDEX_NOT_FOUND"


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
