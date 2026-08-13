"""Versioned index generations and atomic activation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

INDEX_SCHEMA_VERSION = 2
CURRENT_FILE = "CURRENT"
GENERATIONS_DIR = "generations"


class IndexErrorBase(RuntimeError):
    code = "INDEX_ERROR"
    action = "ue-kb build"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self), "action": self.action}


class IndexSchemaMismatch(IndexErrorBase):
    code = "INDEX_SCHEMA_MISMATCH"
    action = "ue-kb build --force"


def corpus_fingerprint(source_dir: Path) -> tuple[str, int]:
    """Hash normalized relative paths and complete file bytes."""
    digest = hashlib.sha256()
    files = sorted(source_dir.rglob("*.md"))
    for path in files:
        relative = path.relative_to(source_dir).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), len(files)


def new_generation(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    generations = root / GENERATIONS_DIR
    generations.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = generations / f"gen-{stamp}-{uuid.uuid4().hex[:8]}"
    path.mkdir()
    (path / "BUILDING").write_text("incomplete\n", encoding="ascii")
    return path


def _legacy_content(root: Path) -> bool:
    if not root.exists():
        return False
    ignored = {CURRENT_FILE, GENERATIONS_DIR, ".build.lock"}
    return any(child.name not in ignored for child in root.iterdir())


def load_current(root: Path) -> Path:
    """Resolve and validate the active schema-v2 generation."""
    pointer = root / CURRENT_FILE
    if not pointer.is_file():
        if _legacy_content(root):
            raise IndexSchemaMismatch(
                f"索引不是 schema v{INDEX_SCHEMA_VERSION}，不能安全读取: {root}"
            )
        raise FileNotFoundError(f"索引不存在: {root}（请先运行: ue-kb build）")
    generation_name = pointer.read_text(encoding="utf-8").strip()
    if not generation_name or Path(generation_name).name != generation_name:
        raise IndexSchemaMismatch(f"CURRENT 指针无效: {pointer}")
    generation = root / GENERATIONS_DIR / generation_name
    if not generation.is_dir() or _abandoned(generation):
        raise IndexSchemaMismatch(f"CURRENT 指向不完整的索引 generation: {generation_name}")
    manifest = read_manifest(generation)
    if manifest.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise IndexSchemaMismatch(
            f"索引 schema={manifest.get('schema_version')!r}，需要 v{INDEX_SCHEMA_VERSION}"
        )
    return generation


def read_manifest(generation: Path) -> dict:
    try:
        return json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IndexSchemaMismatch(f"manifest 缺失或损坏: {generation}") from exc


def activate(root: Path, generation: Path) -> None:
    """Atomically switch CURRENT after the generation has been validated."""
    building = generation / "BUILDING"
    if building.exists():
        building.unlink()
    temporary = root / f".{CURRENT_FILE}.{uuid.uuid4().hex}.tmp"
    temporary.write_text(generation.name + "\n", encoding="ascii")
    os.replace(temporary, root / CURRENT_FILE)


def cleanup_generations(root: Path, keep: int = 2) -> None:
    """Retain the active generation and one rollback generation."""
    try:
        active = load_current(root).name
    except (FileNotFoundError, IndexSchemaMismatch):
        return
    generations_root = root / GENERATIONS_DIR
    complete = [
        path for path in generations_root.iterdir()
        if path.is_dir() and not _abandoned(path)
    ]
    complete.sort(key=lambda path: path.name, reverse=True)
    retained = {active}
    previous = [path.name for path in complete if path.name != active]
    retained.update(previous[: max(0, keep - 1)])
    for path in complete:
        if path.name not in retained:
            try:
                shutil.rmtree(path)
            except OSError:
                # A reader may still hold a Windows file handle. It is safe to
                # leave an inactive generation for a later cleanup pass.
                pass


def discard_incomplete(generation: Path, close=None) -> None:
    """Best-effort removal of an aborted generation.

    ``close`` is an optional callable invoked before removal (e.g. a chromadb
    client's ``clear_system_cache``) so Windows file handles are released.
    The FAILED marker is written FIRST: if ``rmtree`` is blocked by a held
    file handle and only partially succeeds, the leftovers still carry a
    marker, so they can never be mistaken for a complete generation and are
    reclaimed by ``sweep_incomplete`` later.
    """
    failed = generation / "FAILED"
    try:
        failed.write_text("failed\n", encoding="ascii")
    except OSError:
        pass
    if close is not None:
        try:
            close()
        except Exception:
            pass
    try:
        shutil.rmtree(generation)
    except OSError:
        pass


def _abandoned(generation: Path) -> bool:
    return (generation / "BUILDING").is_file() or (generation / "FAILED").is_file()


def sweep_incomplete(root: Path, max_age_seconds: int = 24 * 3600) -> list[str]:
    """Remove generations abandoned by crashed or failed builds.

    ``discard_incomplete`` only runs on the exception path; a hard kill
    (taskkill / power loss) leaves the BUILDING marker behind forever and
    ``cleanup_generations`` deliberately skips incomplete generations. This
    sweep is age-bounded so an in-flight build (marker younger than
    ``max_age_seconds``) is never touched.
    """
    removed: list[str] = []
    generations_root = root / GENERATIONS_DIR
    if not generations_root.is_dir():
        return removed
    now = time.time()
    for path in generations_root.iterdir():
        if not path.is_dir() or not _abandoned(path):
            continue
        try:
            age = now - max(
                (path / name).stat().st_mtime for name in ("BUILDING", "FAILED")
                if (path / name).is_file()
            )
        except OSError:
            continue
        if age > max_age_seconds:
            try:
                shutil.rmtree(path)
                removed.append(path.name)
            except OSError:
                pass
    return removed


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
