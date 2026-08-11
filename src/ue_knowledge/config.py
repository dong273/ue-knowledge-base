"""Shared configuration: default paths and the embedding model name."""

import os
from pathlib import Path

# Default model — small, multilingual (Chinese-friendly), runs on CPU.
MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# Repo root (…/ue-knowledge-base)
REPO_ROOT = Path(__file__).resolve().parents[2]

# Default corpus + vector store locations inside the repo.
DEFAULT_SOURCE_DIR = REPO_ROOT / "knowledge"
DEFAULT_CHROMA_DIR = REPO_ROOT / ".chroma_db"

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
