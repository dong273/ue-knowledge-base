#!/usr/bin/env python3
"""Check that public artifacts contain no project-index material."""

from __future__ import annotations

import argparse
import re
import tarfile
import zipfile
from pathlib import Path

FORBIDDEN = (
    re.compile(r"ZSWM", re.IGNORECASE),
    re.compile(r"Source-Registry\.tsv", re.IGNORECASE),
    re.compile(r"我的项目"),
    re.compile(r"(?:^|[\\/])\.beads(?:[\\/]|$)"),
    re.compile(r"[A-Za-z]:[\\/]unreal projects[\\/]", re.IGNORECASE),
)


def _artifact_files(path: Path):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is not None:
                        yield member.name, handle.read()
    else:
        raise ValueError(f"unsupported artifact: {path}")


def scan_artifact(path: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for name, data in _artifact_files(path):
        name_match = next((pattern.pattern for pattern in FORBIDDEN if pattern.search(name)), None)
        if name_match:
            findings.append({"file": name, "pattern": name_match, "location": "filename"})
        text = data.decode("utf-8", errors="replace")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                findings.append({"file": name, "pattern": pattern.pattern, "location": "content"})
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check wheel/sdist for project-scope leaks")
    parser.add_argument("artifacts", nargs="+")
    args = parser.parse_args(argv)
    failed = False
    for raw in args.artifacts:
        path = Path(raw)
        findings = scan_artifact(path)
        if findings:
            failed = True
            print(f"scope scan failed: {path}")
            for finding in findings:
                print(f"  {finding['file']} [{finding['location']}] {finding['pattern']}")
        else:
            print(f"scope scan clean: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
