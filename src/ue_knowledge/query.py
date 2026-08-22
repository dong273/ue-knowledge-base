"""Vector and bilingual hybrid retrieval against a schema-v2 index."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import config
from .build import _embedding_dimension, _model_revision
from .index_store import IndexSchemaMismatch, load_current, read_manifest
from .retrieval import bm25_search, expand_query, rrf


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
            "source": meta.get("source", "?"),
            "heading": meta.get("heading", "?"),
            "type": meta.get("type") or "content",
            "score": max(0.0, min(1.0, 1.0 - float(distance))),
            "text": document,
        }
        for identifier, document, meta, distance in zip(
            ids[0], documents[0], metadata[0], distances[0]
        )
    ]


def query(
    query_text: str,
    top_k: int = 5,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    offline: bool = True,
    embedder=None,
    profile: str = "hybrid",
    demote_frontmatter: bool = False,
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
    vector = _vector_results(collection, model, vector_text, candidate_count)
    if profile == "vector":
        return [
            {
                "source": hit["source"],
                "heading": hit["heading"],
                "type": hit.get("type", "content"),
                "score": hit["score"],
                "raw_score": hit["score"],
                "rank": index + 1,
                "text": hit["text"],
            }
            for index, hit in enumerate(vector[:top_k])
        ]

    lexical = bm25_search(generation / "bm25.json", vector_text, limit=30)
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
                "text": document,
            }
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
        output.append(
            {
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
        )
        if len(output) == top_k:
            break
    return output


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
