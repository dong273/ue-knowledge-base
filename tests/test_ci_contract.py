from pathlib import Path


def test_ci_runs_pytest_as_a_module_for_repository_script_imports():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "pip install pytest && python -m pytest tests/ -v" in workflow
    assert "pip install pytest && pytest tests/ -v" not in workflow


def test_ci_smoke_uses_manifest_identity_instead_of_a_stale_chunk_floor():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "d['manifest']['corpus']['documents'] == 90" in workflow
    assert "d['documents'] == d['manifest']['corpus']['chunks']" in workflow
    assert "d['documents'] >= 1500" not in workflow
