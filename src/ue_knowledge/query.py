"""Semantic querying against the built index."""

from pathlib import Path

from . import config


def query(
    query_text: str,
    top_k: int = 5,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    offline: bool = True,
) -> list[dict]:
    """Search the knowledge base. Returns [{source, heading, score, text}]."""
    from sentence_transformers import SentenceTransformer
    import chromadb

    chroma = chroma_dir or config.chroma_dir()
    model_name = model_name or config.MODEL_NAME

    model = SentenceTransformer(model_name, local_files_only=offline)
    client = chromadb.PersistentClient(path=str(chroma))
    collection = client.get_collection(config.COLLECTION_NAME)

    query_embedding = model.encode(
        [query_text], normalize_embeddings=True
    )[0]

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    out = []
    docs = results["documents"] or [[]]
    metas = results["metadatas"] or [[]]
    dists = results["distances"] or [[]]
    for doc, meta, dist in zip(docs[0], metas[0], dists[0]):
        out.append({
            "source": meta.get("source", "?"),
            "heading": meta.get("heading", "?"),
            "score": round(1.0 - dist, 4),
            "text": doc,
        })
    return out


def format_results(results: list[dict], query_text: str) -> str:
    """Human-readable rendering of query results."""
    if not results:
        return "没有找到相关结果。"
    lines = [f"🔍 UE 知识库检索：{query_text}", ""]
    for i, r in enumerate(results, 1):
        score = f"{r['score']:.1%}"
        lines.append(f"[{i}] {r['source']} › {r['heading']} (匹配度: {score})")
        lines.append(f"    {r['text'][:200].replace(chr(10), ' ')}...")
        lines.append("")
    return "\n".join(lines)
