#!/usr/bin/env python3
"""Release gate: the corpus inside a built wheel/sdist == the source corpus.

Usage:
    python scripts/verify_package.py dist/ue_knowledge_base-0.6.0-py3-none-any.whl
    python scripts/verify_package.py dist/*.whl dist/*.tar.gz

For every artifact this checks:

  - every markdown file under ``src/ue_knowledge/knowledge/`` exists in the
    artifact at the same relative path with an identical SHA-256 — no
    missing files, no stale copies, no extra leftovers (the corpus must be
    the single source of truth for source checkouts, wheels and sdists);
  - ``LICENSE`` is packaged (SPDX license metadata + license file);
  - the artifact version matches the package ``__version__``.

Exit code 0 = gate passed, 1 = failed. Run it in CI after ``python -m build``.
"""

import argparse
import hashlib
import re
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CORPUS = REPO_ROOT / "src/ue_knowledge/knowledge"


def source_chunk_stats() -> dict[str, int]:
    """Generate dependency-free release stats from the shipped chunker."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from ue_knowledge.chunking import collect_markdown, token_count

    chunks = collect_markdown(SOURCE_CORPUS)
    return {
        "chunks": len(chunks),
        "unique_ids": len({chunk["id"] for chunk in chunks}),
        "max_tokens": max(token_count(chunk["text"]) for chunk in chunks),
        "unbalanced_fences": sum(
            chunk["text"].count("```") % 2 or chunk["text"].count("~~~") % 2
            for chunk in chunks
        ),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_manifest() -> dict[str, str]:
    """Relative path -> sha256 for every .md in the source corpus."""
    return {
        p.relative_to(SOURCE_CORPUS).as_posix(): _sha256(p.read_bytes())
        for p in sorted(SOURCE_CORPUS.rglob("*.md"))
    }


def wheel_manifest(wheel: Path) -> dict[str, str]:
    """Relative path -> sha256 for .md files in the wheel's package data."""
    out: dict[str, str] = {}
    with zipfile.ZipFile(wheel) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if "/knowledge/" in name and name.endswith(".md"):
                rel = name.split("/knowledge/", 1)[1]
                out[rel] = _sha256(zf.read(info))
    return out


def sdist_manifest(sdist: Path) -> dict[str, str]:
    """Relative path -> sha256 for .md files in the sdist."""
    out: dict[str, str] = {}
    with tarfile.open(sdist, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if "/knowledge/" in name and name.endswith(".md"):
                rel = name.split("/knowledge/", 1)[1]
                out[rel] = _sha256(tf.extractfile(member).read())
    return out


def metadata_version(artifact: Path) -> str | None:
    """Version from wheel METADATA / sdist PKG-INFO."""
    try:
        if artifact.suffix == ".whl":
            with zipfile.ZipFile(artifact) as zf:
                meta_name = next(
                    n for n in zf.namelist()
                    if n.endswith(".dist-info/METADATA")
                )
                content = zf.read(meta_name).decode("utf-8", "replace")
        else:
            with tarfile.open(artifact, "r:gz") as tf:
                pkg_info = next(
                    m for m in tf.getmembers()
                    if m.isfile() and m.name.endswith("/PKG-INFO")
                )
                content = tf.extractfile(pkg_info).read().decode("utf-8", "replace")
    except (StopIteration, KeyError, tarfile.TarError, zipfile.BadZipFile) as e:
        print(f"[!] cannot read metadata from {artifact}: {e}")
        return None
    m = re.search(r"^Version:\s*(\S+)", content, re.M)
    return m.group(1) if m else None


def license_present(artifact: Path) -> bool:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as zf:
            return any(
                n.endswith("/LICENSE") or n == "LICENSE" for n in zf.namelist()
            )
    with tarfile.open(artifact, "r:gz") as tf:
        return any(
            m.isfile() and m.name.endswith("/LICENSE") for m in tf.getmembers()
        )


def packaged_json(artifact: Path, filename: str) -> bytes | None:
    """Read a packaged JSON data file (glossary.json / zh_dict.json)."""
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as zf:
            name = next(
                (item for item in zf.namelist() if item.endswith(f"ue_knowledge/{filename}")),
                None,
            )
            return zf.read(name) if name else None
    with tarfile.open(artifact, "r:gz") as tf:
        member = next(
            (
                item for item in tf.getmembers()
                if item.isfile() and item.name.endswith(f"/src/ue_knowledge/{filename}")
            ),
            None,
        )
        return tf.extractfile(member).read() if member else None


def check_artifact(artifact: Path, expected_version: str) -> bool:
    ok = True
    print(f"== {artifact.name} ==")

    manifest = (
        wheel_manifest(artifact)
        if artifact.suffix == ".whl"
        else sdist_manifest(artifact)
    )
    source = source_manifest()
    chunk_stats = source_chunk_stats()

    missing = sorted(set(source) - set(manifest))
    stale = sorted(
        rel for rel in set(source) & set(manifest)
        if source[rel] != manifest[rel]
    )
    extra = sorted(set(manifest) - set(source))

    print(f"    corpus .md in artifact : {len(manifest)}")
    print(f"    corpus .md in source  : {len(source)}")
    print(f"    generated chunks      : {chunk_stats['chunks']}")
    print(f"    fallback max tokens   : {chunk_stats['max_tokens']}")
    if chunk_stats["chunks"] <= len(source):
        ok = False
        print("    [FAIL] generated chunk count is implausibly small")
    if chunk_stats["unique_ids"] != chunk_stats["chunks"]:
        ok = False
        print("    [FAIL] generated chunk ids are not unique")
    if chunk_stats["max_tokens"] > 384:
        ok = False
        print("    [FAIL] generated chunk exceeds 384 fallback tokens")
    if chunk_stats["unbalanced_fences"]:
        ok = False
        print("    [FAIL] generated chunk contains an unbalanced code fence")
    if missing:
        ok = False
        print(f"    [FAIL] {len(missing)} file(s) missing from artifact:")
        for rel in missing:
            print(f"           - {rel}")
    if stale:
        ok = False
        print(f"    [FAIL] {len(stale)} stale file(s) (content hash differs):")
        for rel in stale:
            print(f"           - {rel}")
    if extra:
        ok = False
        print(f"    [FAIL] {len(extra)} unexpected file(s) in artifact "
              f"(not in source corpus):")
        for rel in extra:
            print(f"           - {rel}")
    if not missing and not stale and not extra:
        print("    [ok]  corpus identical to source (paths + hashes)")

    ver = metadata_version(artifact)
    if ver == expected_version:
        print(f"    [ok]  version {ver}")
    else:
        ok = False
        print(f"    [FAIL] version {ver!r}, expected {expected_version!r}")

    lic = license_present(artifact)
    if lic:
        print("    [ok]  LICENSE packaged")
    else:
        ok = False
        print("    [FAIL] LICENSE missing from artifact")

    for filename in ("glossary.json", "zh_dict.json"):
        source_file = REPO_ROOT / f"src/ue_knowledge/{filename}"
        packaged = packaged_json(artifact, filename)
        if packaged == source_file.read_bytes():
            print(f"    [ok]  {filename} packaged with identical hash")
        else:
            ok = False
            print(f"    [FAIL] {filename} missing or stale")

    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify wheel/sdist corpus matches the source corpus"
    )
    parser.add_argument(
        "artifacts", nargs="+",
        help="built artifacts: dist/*.whl and/or dist/*.tar.gz",
    )
    args = parser.parse_args(argv)

    # expected version from the source tree (single source of truth)
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from ue_knowledge import __version__

    results = [check_artifact(Path(p), __version__) for p in args.artifacts]
    if all(results):
        print(f"\n[PASS] {len(results)} artifact(s) OK")
        return 0
    print(f"\n[FAIL] {results.count(False)} artifact(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
