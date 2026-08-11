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
