"""Federated, physically isolated queries across named indexes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .query import query_envelope


def parse_index_specs(specs: list[str] | None) -> dict[str, Path]:
    """Parse repeatable ``name=path`` CLI/MCP index specifications."""
    indexes: dict[str, Path] = {}
    for spec in specs or []:
        if "=" not in spec:
            raise ValueError(f"invalid --index {spec!r}; expected name=path")
        name, raw_path = spec.split("=", 1)
        name = name.strip()
        raw_path = raw_path.strip()
        if not name or not raw_path:
            raise ValueError(f"invalid --index {spec!r}; expected name=path")
        if name in indexes:
            raise ValueError(f"duplicate index name: {name}")
        indexes[name] = Path(raw_path)
    return indexes


def federated_query(
    query_text: str,
    indexes: Mapping[str, Path],
    *,
    top_k: int = 5,
    model_name: str | None = None,
    offline: bool = True,
    embedder=None,
    profile: str = "hybrid",
    demote_frontmatter: bool = False,
) -> dict[str, Any]:
    """Query each index independently and return a grouped envelope.

    Scores are never compared across indexes.  This is deliberate: a project
    index and a public index have different corpora and therefore different
    RRF score distributions.  Callers choose authority from the group name
    and the per-index coverage status.
    """
    if not indexes:
        raise ValueError("at least one named index is required")
    groups: dict[str, dict[str, Any]] = {}
    errors: dict[str, dict[str, str]] = {}
    for name, path in indexes.items():
        try:
            envelope = query_envelope(
                query_text,
                top_k=top_k,
                chroma_dir=Path(path),
                model_name=model_name,
                offline=offline,
                embedder=embedder,
                profile=profile,
                demote_frontmatter=demote_frontmatter,
            )
            actual_scope = envelope.get("scope")
            if name in {"public", "project"} and actual_scope != name:
                errors[name] = {
                    "code": "INDEX_SCOPE_MISMATCH",
                    "message": f"named {name!r} but manifest scope is {actual_scope!r}",
                }
                continue
            envelope["index"] = name
            groups[name] = envelope
        except Exception as exc:
            errors[name] = {"code": type(exc).__name__, "message": str(exc)}

    public_hits = [
        hit for envelope in groups.values()
        if envelope.get("scope") == "public"
        for hit in envelope.get("hits", [])
    ]
    project_hits = [
        hit for envelope in groups.values()
        if envelope.get("scope") == "project"
        for hit in envelope.get("hits", [])
    ]
    return {
        "schema_version": 1,
        "query": query_text,
        "groups": groups,
        "public_hits": public_hits,
        "project_hits": project_hits,
        "errors": errors,
    }
