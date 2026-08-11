"""Index building — embed the corpus and store it in ChromaDB."""

import os
from pathlib import Path

from . import config
from .chunking import collect_markdown


def build_index(
    source_dir: Path | None = None,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    force: bool = False,
    offline: bool = True,
    embedder=None,
) -> dict:
    """Build (or rebuild) the vector index from the markdown corpus.

    ``embedder`` injects a custom embedder for testing (must expose
    ``encode(texts, **kwargs)`` and ``get_sentence_embedding_dimension()``);
    defaults to a local SentenceTransformer when omitted.

    Returns a summary dict: {files, chunks, collection, chroma_dir}.
    """
    if offline:
        # Force huggingface_hub into offline mode so a missing file in the
        # local cache can never trigger network retries (slow in CN networks).
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if embedder is None:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer(
            model_name,
            local_files_only=offline,
        )
        embedder.max_seq_length = 512
    import chromadb

    source = source_dir or config.source_dir()
    chroma = chroma_dir or config.chroma_dir()
    model_name = model_name or config.MODEL_NAME

    if not source.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {source}")

    print(f"[*] Loading model: {model_name}")
    model = embedder
    print(f"    Embedding dim: {model.get_sentence_embedding_dimension()}")

    print(f"[*] Reading corpus: {source}")
    documents = collect_markdown(source)
    if not documents:
        raise RuntimeError("no markdown documents found in corpus")
    print(f"    {len(documents)} chunks")

    chroma.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma))

    if force:
        try:
            client.delete_collection(config.COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={
            "description": "UE Game Development Knowledge Base",
            "hnsw:space": "cosine",
        },
    )
    if collection.count() > 0 and not force:
        raise RuntimeError(
            f"collection already has {collection.count()} docs; use --force to rebuild"
        )

    texts = [d["text"] for d in documents]
    ids = [d["id"] for d in documents]
    metadatas = [{"source": d["source"], "heading": d["heading"]} for d in documents]

    print(f"[*] Embedding {len(texts)} chunks...")
    batch_size = 64
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        embeddings = model.encode(
            batch_texts, show_progress_bar=False, normalize_embeddings=True
        )
        collection.add(
            ids=ids[i:i + batch_size],
            embeddings=embeddings.tolist(),
            documents=batch_texts,
            metadatas=metadatas[i:i + batch_size],
        )
        print(f"    [{min(i + batch_size, len(texts)):4d}/{len(texts)}]")

    print(f"[✓] Index ready: {chroma} ({collection.count()} docs)")
    return {
        "files": len(list(source.rglob("*.md"))),
        "chunks": len(documents),
        "collection": config.COLLECTION_NAME,
        "chroma_dir": str(chroma),
    }
