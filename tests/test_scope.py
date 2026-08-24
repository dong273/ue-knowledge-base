from pathlib import Path
import tarfile
import zipfile

from scripts.check_scope import scan_artifact


def test_scope_scan_accepts_clean_wheel_and_sdist(tmp_path):
    wheel = tmp_path / "clean.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("ue_knowledge-0.7.0.dist-info/METADATA", "Name: ue-knowledge\n")
    sdist = tmp_path / "clean.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        payload = b"generic Unreal Engine guidance"
        info = tarfile.TarInfo("ue-knowledge-0.7.0/README.md")
        info.size = len(payload)
        import io
        archive.addfile(info, io.BytesIO(payload))
    assert scan_artifact(wheel) == []
    assert scan_artifact(sdist) == []


def test_scope_scan_allows_generic_source_registry_command_reference(tmp_path):
    wheel = tmp_path / "public-docs.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "ue_knowledge/knowledge/ue-knowledge-rag/SKILL.md",
            "ue-kb build --scope project --source-registry Source-Registry.tsv",
        )

    assert scan_artifact(wheel) == []


def test_scope_scan_rejects_source_registry_file(tmp_path):
    wheel = tmp_path / "registry-file.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("private/Source-Registry.tsv", "source_id\tpath\n")

    findings = scan_artifact(wheel)
    assert findings
    assert any(item["location"] == "filename" for item in findings)


def test_scope_scan_reports_project_material(tmp_path):
    path = tmp_path / "leaky.whl"
    marker = "Z" + "SWM"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ue_knowledge/data.txt", marker + " private evidence")
    findings = scan_artifact(path)
    assert findings
    assert any(item["location"] == "content" for item in findings)


def test_scope_patterns_are_available():
    from scripts.check_scope import FORBIDDEN_CONTENT, FORBIDDEN_FILENAMES

    assert any(pattern.search("Z" + "SWM") for pattern in FORBIDDEN_CONTENT)
    assert not any(pattern.search("Source-" + "Registry.tsv") for pattern in FORBIDDEN_CONTENT)
    assert any(pattern.search("Source-" + "Registry.tsv") for pattern in FORBIDDEN_FILENAMES)
