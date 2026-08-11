"""CLI smoke tests — argparse wiring only (no model/index required)."""

from ue_knowledge.cli import main


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "ue-kb" in out


def test_build_missing_source_errors(capsys):
    # --db must be ASCII: the repo path itself may contain non-ASCII chars
    # (e.g. C:\\Users\\张三\\...), which would trip the path guard first.
    rc = main(["build", "--source", "C:/definitely/not/here", "--db", "C:/ascii_uekb/db"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_query_missing_index_reports_index_not_model(capsys):
    """A missing index must be reported as such, not as a model problem.

    This must work without a model cached (CI-safe): the index check runs
    before any model loading.
    """
    rc = main(["query", "anything", "--db", "C:/definitely/not/exists"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "索引" in err
    assert "Model" not in err


def test_build_rejects_non_ascii_chroma_path(capsys):
    """hnswlib on Windows cannot open index files under non-ASCII paths;
    build must reject them early with a clear hint (before loading a model)."""
    rc = main(["build", "--source", "C:/definitely/not/here", "--db", "C:/中文路径/db"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "ASCII" in err


def test_query_rejects_non_ascii_chroma_path(capsys):
    rc = main(["query", "anything", "--db", "C:/中文路径/db"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "ASCII" in err
