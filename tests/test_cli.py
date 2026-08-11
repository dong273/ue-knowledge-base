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
    rc = main(["build", "--source", "C:/definitely/not/here"])
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
