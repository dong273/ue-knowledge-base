#!/usr/bin/env python3
"""Verify the checked-in public publication manifest against the corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def check(manifest_path: Path, corpus: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read manifest: {type(exc).__name__}: {exc}"]
    files = payload.get("files")
    hashes = payload.get("sha256")
    if payload.get("schema_version") != 1 or not isinstance(files, list) or not isinstance(hashes, dict):
        return ["manifest requires schema_version=1, files list and sha256 object"]
    actual = {}
    for path in sorted(corpus.rglob("*.md")):
        relative = path.relative_to(corpus).as_posix()
        actual[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if files != sorted(files) or set(files) != set(actual):
        errors.append("manifest file set does not equal the public corpus")
    for relative, digest in actual.items():
        if hashes.get(relative) != digest:
            errors.append(f"manifest hash mismatch: {relative}")
    if set(hashes) != set(actual):
        errors.append("manifest hash keys do not equal the public corpus")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check public corpus publication manifest")
    parser.add_argument("--manifest", type=Path, default=Path("validation/publication-manifest.json"))
    parser.add_argument("--corpus", type=Path, default=Path("src/ue_knowledge/knowledge"))
    args = parser.parse_args(argv)
    errors = check(args.manifest, args.corpus)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print(f"[PASS] publication manifest covers {len(json.loads(args.manifest.read_text(encoding='utf-8'))['files'])} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
