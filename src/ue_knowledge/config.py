"""Shared configuration: default paths and the embedding model name."""

import os
import sys
from pathlib import Path

# Default model — English-first corpus (81/86 docs are English), small and
# runs on CPU. Chinese speakers can override with --model BAAI/bge-small-zh-v1.5
# and rebuild for better Chinese retrieval precision.
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# The corpus ships INSIDE the package as package data, so the default source
# dir resolves identically for source checkouts, wheels and sdists — no
# repo-root path guessing (which broke after `pip install` because the
# installed package has no repo root).
DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent / "knowledge"


def _default_chroma_dir() -> Path:
    """User-writable data directory for the vector store.

    Never inside site-packages: a wheel install must not try to write into
    Python's Lib/ or site-packages (read-only for normal users).
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "ue-knowledge-base" / "chroma_db"


# Default vector store location (user data dir).
DEFAULT_CHROMA_DIR = _default_chroma_dir()

# ChromaDB collection name.
COLLECTION_NAME = "ue_knowledge"


def source_dir(override: str | None = None) -> Path:
    """Resolve the markdown corpus directory (CLI flag > env > default)."""
    if override:
        return Path(override)
    env = os.environ.get("UE_KB_SOURCE")
    return Path(env) if env else DEFAULT_SOURCE_DIR


def chroma_dir(override: str | None = None) -> Path:
    """Resolve the ChromaDB store directory (CLI flag > env > default)."""
    if override:
        return Path(override)
    env = os.environ.get("UE_KB_CHROMA_DIR")
    return Path(env) if env else DEFAULT_CHROMA_DIR


class AsciiPathError(ValueError):
    """Raised when an index/corpus path contains non-ASCII characters."""


def chroma_settings():
    """ChromaDB client settings with product telemetry explicitly OFF.

    chromadb 0.6.x sends product telemetry through posthog, and the
    capture() call signature differs across posthog majors — resolvers
    routinely install posthog 7.x (pins are not enforced on already-
    installed packages), which prints a noisy stderr traceback on every
    build/query ("capture() takes 1 positional argument but 3 were
    given"). Disabling telemetry at the settings level silences this
    regardless of which posthog version is installed.
    """
    import chromadb

    return chromadb.config.Settings(anonymized_telemetry=False)


def check_ascii_path(p: Path, what: str) -> None:
    """Reject non-ASCII paths early.

    hnswlib on Windows cannot open its index files under non-ASCII paths
    ('Cannot open header file') — e.g. C:\\用户\\... — so fail fast with a
    clear hint instead of a cryptic crash deep inside ChromaDB.
    """
    s = str(p)
    if any(ord(c) > 127 for c in s):
        raise AsciiPathError(
            f"{what} 路径包含非 ASCII 字符（hnswlib 在 Windows 上无法打开此类路径）:\n"
            f"    {s}\n"
            f"    请改用纯英文路径，例如: C:/uekb/.chroma_db（可通过 "
            f"--db 或 UE_KB_CHROMA_DIR 覆盖）"
        )
