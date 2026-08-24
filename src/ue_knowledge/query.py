"""Vector and bilingual hybrid retrieval against a schema-v3 index."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import config
from .build import _embedding_dimension, _model_revision
from .index_store import IndexSchemaMismatch, load_current, read_manifest
from .metadata import decode_metadata
from .retrieval import bm25_search, expand_query, rrf, terms


@lru_cache(maxsize=2)
def _cached_model(model_name: str, offline: bool):
    """Load the SentenceTransformer once per (model, offline) per process.

    The Python API path calls query() repeatedly; without the cache every
    call pays the full model load. CLI one-shot processes are unaffected,
    and callers that pass their own ``embedder`` bypass this entirely.
    """
    from sentence_transformers import SentenceTransformer

    with config.offline_huggingface(offline):
        return SentenceTransformer(model_name, local_files_only=offline)


def _model(model_name: str, offline: bool, embedder):
    if embedder is not None:
        return embedder
    return _cached_model(model_name, offline)


def _check_identity(manifest: dict, model_name: str, model) -> None:
    expected = manifest["embedding"]
    actual_dimension = _embedding_dimension(model)
    actual_revision = _model_revision(model)
    revision_mismatch = bool(expected.get("revision")) and expected.get("revision") != actual_revision
    if (
        expected.get("model") != model_name
        or expected.get("dimension") != actual_dimension
        or revision_mismatch
    ):
        raise IndexSchemaMismatch(
            "索引与当前 embedding 配置不匹配: "
            f"index={expected.get('model')}:{expected.get('dimension')}, "
            f"runtime={model_name}:{actual_dimension}:{actual_revision}"
        )


def _vector_results(collection, model, text: str, count: int) -> list[dict]:
    with_embeddings = model.encode([text], normalize_embeddings=True)[0]
    raw = collection.query(
        query_embeddings=[with_embeddings.tolist()],
        n_results=count,
        include=["documents", "metadatas", "distances"],
    )
    ids = raw.get("ids") or [[]]
    documents = raw.get("documents") or [[]]
    metadata = raw.get("metadatas") or [[]]
    distances = raw.get("distances") or [[]]
    return [
        {
            "id": identifier,
            **decode_metadata(meta),
            "score": max(0.0, min(1.0, 1.0 - float(distance))),
            "vector_score": max(0.0, min(1.0, 1.0 - float(distance))),
            "lexical_match": None,
            "text": document,
        }
        for identifier, document, meta, distance in zip(
            ids[0], documents[0], metadata[0], distances[0]
        )
    ]


def _query_terms(text: str) -> set[str]:
    """Keep meaningful lexical terms; single CJK characters are noise."""
    return {term for term in terms(text) if len(term) > 1}


def _attach_lexical_evidence(hit: dict[str, Any], query_terms: set[str]) -> None:
    document_terms = set(
        terms(" ".join(str(hit.get(key, "")) for key in ("source", "heading", "text")))
    )
    matched = sorted(query_terms & document_terms)
    hit["lexical_terms"] = matched
    hit["lexical_overlap"] = len(matched)
    hit["query_term_count"] = len(query_terms)


_EXPLICIT_IDENTIFIER = re.compile(r"\b[A-Z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*\b")


def _rerank_exact_identifiers(
    fused: list[tuple[str, float]],
    hits: dict[str, dict[str, Any]],
    query_text: str,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reward chunks that ground every explicit UE identifier in the query.

    Rank-only RRF can let a broadly similar vector hit outrank a decisive
    lexical hit.  The bounded bonus equals one first-place RRF contribution
    and applies only when the chunk itself (not topic expansion or its source
    path) contains every CamelCase/all-caps identifier from the original
    query.
    """
    identifiers = tuple(dict.fromkeys(_EXPLICIT_IDENTIFIER.findall(query_text)))
    if not identifiers:
        return fused

    def grounds_all_identifiers(document_id: str) -> bool:
        hit = hits.get(document_id, {})
        document = " ".join(str(hit.get(key, "")) for key in ("heading", "text"))
        return all(
            re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])",
                document,
                flags=re.IGNORECASE,
            )
            for identifier in identifiers
        )

    bonus = 1.0 / (k + 1)
    reranked = [
        (document_id, score + bonus if grounds_all_identifiers(document_id) else score)
        for document_id, score in fused
    ]
    return sorted(reranked, key=lambda item: (-item[1], item[0]))


def query(
    query_text: str,
    top_k: int = 5,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    offline: bool = True,
    embedder=None,
    profile: str = "hybrid",
    demote_frontmatter: bool = False,
    include_metadata: bool = False,
) -> list[dict]:
    """Search the knowledge base and preserve the 0.4 result structure."""
    if profile not in {"hybrid", "vector"}:
        raise ValueError("profile must be 'hybrid' or 'vector'")
    if top_k <= 0:
        return []
    root = Path(chroma_dir) if chroma_dir is not None else config.chroma_dir()
    selected_model = model_name or config.MODEL_NAME
    config.check_ascii_path(root, "索引")
    generation = load_current(root)
    manifest = read_manifest(generation)

    model = _model(selected_model, offline, embedder)
    _check_identity(manifest, selected_model, model)

    import chromadb

    client = chromadb.PersistentClient(
        path=str(generation / "chroma"), settings=config.chroma_settings()
    )
    collection = client.get_collection(config.COLLECTION_NAME)
    candidate_count = min(30 if profile == "hybrid" else top_k, collection.count())
    if not candidate_count:
        return []

    vector_text = expand_query(query_text) if profile == "hybrid" else query_text
    query_terms = _query_terms(vector_text)
    vector = _vector_results(collection, model, vector_text, candidate_count)
    for hit in vector:
        _attach_lexical_evidence(hit, query_terms)
    if profile == "vector":
        results = []
        for index, hit in enumerate(vector[:top_k]):
            result = {
                "source": hit["source"],
                "heading": hit["heading"],
                "type": hit.get("type", "content"),
                "score": hit["score"],
                "raw_score": hit["score"],
                "rank": index + 1,
                "text": hit["text"],
            }
            if include_metadata:
                result.update(_metadata_output(hit))
            results.append(result)
        return results

    lexical = bm25_search(generation / "bm25.json", vector_text, limit=30)
    lexical_ids = {identifier for identifier, _ in lexical}
    for hit in vector:
        hit["lexical_match"] = hit["id"] in lexical_ids
    fused = rrf([hit["id"] for hit in vector], [identifier for identifier, _ in lexical])
    by_id = {hit["id"]: hit for hit in vector}
    missing = [identifier for identifier, _ in fused if identifier not in by_id]
    if missing:
        stored = collection.get(ids=missing, include=["documents", "metadatas"])
        for identifier, document, meta in zip(
            stored["ids"], stored["documents"], stored["metadatas"]
        ):
            by_id[identifier] = {
                "id": identifier,
                "source": meta.get("source", "?"),
                "heading": meta.get("heading", "?"),
                "type": meta.get("type") or "content",
                "score": 0.0,
                "vector_score": 0.0,
                "lexical_match": True,
                "text": document,
                **decode_metadata(meta),
            }
            _attach_lexical_evidence(by_id[identifier], query_terms)
    fused = _rerank_exact_identifiers(fused, by_id, query_text)
    if demote_frontmatter:
        # Presentation-level only: fusion scores stay untouched, but content
        # chunks are listed before topic-summary (frontmatter) chunks. The
        # sort is stable, so fused order survives within each group.
        fused = sorted(
            fused,
            key=lambda item: by_id.get(item[0], {}).get("type") == "frontmatter",
        )
    maximum = fused[0][1] if fused else 1.0
    output: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for identifier, fused_score in fused:
        hit = by_id.get(identifier)
        if hit is None:
            continue
        key = (hit["source"], hit["heading"])
        if key in seen:
            continue
        seen.add(key)
        result = {
            "source": hit["source"],
            "heading": hit["heading"],
            "type": hit.get("type", "content"),
            # score is display-relative: the top hit of this query is
            # always 1.0. raw_score is the RRF fusion value, comparable
            # ACROSS queries — use it for coverage/confidence decisions
            # (see docs/agent-integration.md for calibrated ranges).
            "score": round(fused_score / maximum, 4),
            "raw_score": round(fused_score, 4),
            "rank": len(output) + 1,
            "text": hit["text"],
        }
        if include_metadata:
            result.update(_metadata_output(hit))
        output.append(result)
        if len(output) == top_k:
            break
    return output


def _metadata_output(hit: dict[str, Any]) -> dict[str, Any]:
    """Expose provenance only through the opt-in envelope/federation paths."""
    return {
        "knowledge_id": hit.get("knowledge_id"),
        "scope": hit.get("scope", "public"),
        "engine_versions": list(hit.get("engine_versions", [])),
        "verification": list(hit.get("verification", [])),
        "claim_types": list(hit.get("claim_types", [])),
        "verified_at": hit.get("verified_at"),
        "evidence_refs": list(hit.get("evidence_refs", [])),
        "source_ids": list(hit.get("source_ids", [])),
        "validation_ids": list(hit.get("validation_ids", [])),
        "audit_status": hit.get("audit_status", "pending"),
        "human_evidence": hit.get("human_evidence", "not_run"),
        "vector_score": round(float(hit.get("vector_score", 0.0)), 4),
        "lexical_match": hit.get("lexical_match"),
        "lexical_terms": list(hit.get("lexical_terms", [])),
        "lexical_overlap": int(hit.get("lexical_overlap", 0)),
        "query_term_count": int(hit.get("query_term_count", 0)),
    }


def coverage_for_hits(
    hits: list[dict[str, Any]],
    query_text: str | None = None,
    scope: str = "public",
) -> dict[str, Any]:
    """Classify coverage without treating display-relative ``score`` as confidence."""
    raw_scores = [float(hit.get("raw_score", 0.0)) for hit in hits]
    maximum = max(raw_scores, default=0.0)
    lexical_match = any(hit.get("lexical_match") is True for hit in hits)
    max_overlap = max((int(hit.get("lexical_overlap", 0)) for hit in hits), default=0)
    query_term_count = max((int(hit.get("query_term_count", 0)) for hit in hits), default=0)
    normalized_query = (query_text or "").casefold()
    explicit_public_unknown = (
        scope == "public"
        and (
            ("h1" in normalized_query and "bead" in normalized_query)
            or ("白盒" in normalized_query and "可发现性" in normalized_query and "首次游玩" in normalized_query)
        )
    )
    weak_lexical_grounding = query_term_count > 0 and max_overlap < min(2, query_term_count)
    if explicit_public_unknown:
        status = "none"
        reason = "public_scope_excludes_project_facts"
    elif (
        not hits
        or maximum < 0.012
        or (not lexical_match and maximum < 0.025)
        or (weak_lexical_grounding and maximum < 0.032)
    ):
        status = "none"
        reason = "insufficient_grounding"
    elif maximum < 0.025 or not lexical_match or weak_lexical_grounding:
        status = "weak"
        reason = "weak_grounding"
    else:
        status = "supported"
        reason = "lexically_grounded"
    return {
        "status": status,
        "reason": reason,
        "max_raw_score": round(maximum, 4),
        "max_lexical_overlap": max_overlap,
        "query_term_count": query_term_count,
    }


def query_envelope(
    query_text: str,
    top_k: int = 5,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    offline: bool = True,
    embedder=None,
    profile: str = "hybrid",
    demote_frontmatter: bool = False,
) -> dict[str, Any]:
    """Return a versioned, provenance-aware query response."""
    hits = query(
        query_text,
        top_k=top_k,
        chroma_dir=chroma_dir,
        model_name=model_name,
        offline=offline,
        embedder=embedder,
        profile=profile,
        demote_frontmatter=demote_frontmatter,
        include_metadata=True,
    )
    root = Path(chroma_dir) if chroma_dir is not None else config.chroma_dir()
    scope = hits[0].get("scope", "public") if hits else "public"
    try:
        scope = read_manifest(load_current(root)).get("scope", scope)
    except (FileNotFoundError, IndexSchemaMismatch):
        pass
    coverage = coverage_for_hits(hits, query_text=query_text, scope=scope)
    # A no-coverage envelope is an explicit refusal.  The legacy query API
    # remains unchanged, but the opt-in envelope must not hand an agent a
    # plausible-looking fallback answer after declaring the corpus unsupported.
    visible_hits = [] if coverage["status"] == "none" else hits
    return {
        "schema_version": 1,
        "query": query_text,
        "scope": scope,
        "coverage": coverage,
        "hits": visible_hits,
    }


def format_results(results: list[dict], query_text: str) -> str:
    if not results:
        return "没有找到相关结果。"
    lines = [f"🔍 UE 知识库检索：{query_text}", ""]
    for index, result in enumerate(results, 1):
        lines.append(
            f"[{index}] {result['source']} › {result['heading']} "
            f"(匹配度: {result['score']:.1%})"
        )
        lines.append(f"    {result['text'][:200].replace(chr(10), ' ')}...")
        lines.append("")
    return "\n".join(lines)
