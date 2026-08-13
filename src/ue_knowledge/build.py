"""Build validated schema-v2 index generations and activate atomically."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import __version__, config
from .chunking import (
    CHUNKER_VERSION,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    collect_markdown,
)
from .index_store import (
    INDEX_SCHEMA_VERSION,
    IndexSchemaMismatch,
    activate,
    cleanup_generations,
    corpus_fingerprint,
    discard_incomplete,
    load_current,
    new_generation,
    read_manifest,
    utc_now,
)
from .retrieval import build_bm25

Progress = Callable[[str], None]


def _embedding_dimension(model) -> int:
    modern = getattr(model, "get_embedding_dimension", None)
    if callable(modern):
        return int(modern())
    try:
        for module in model:
            function = getattr(module, "get_embedding_dimension", None)
            if callable(function):
                return int(function())
            function = getattr(module, "get_sentence_embedding_dimension", None)
            if callable(function):
                return int(function())
    except (TypeError, AttributeError):
        pass
    function = getattr(model, "get_sentence_embedding_dimension", None)
    if callable(function):
        return int(function())
    raise RuntimeError(f"cannot determine embedding dimension for {type(model).__name__}")


def _existing_ids(root: Path) -> set[str]:
    try:
        generation = load_current(root)
    except (FileNotFoundError, IndexSchemaMismatch):
        return set()
    import chromadb

    client = chromadb.PersistentClient(
        path=str(generation / "chroma"), settings=config.chroma_settings()
    )
    collection = client.get_collection(config.COLLECTION_NAME)
    return set(collection.get()["ids"])


def _load_embedder(model_name: str, offline: bool):
    from sentence_transformers import SentenceTransformer

    with config.offline_huggingface(offline):
        model = SentenceTransformer(model_name, local_files_only=offline)
    model.max_seq_length = 512
    return model


def _model_revision(model):
    revision = getattr(model, "revision", None)
    if revision:
        return str(revision)
    try:
        configuration = getattr(getattr(model[0], "auto_model", None), "config", None)
        revision = getattr(configuration, "_commit_hash", None)
    except (TypeError, AttributeError, IndexError):
        revision = None
    return str(revision) if revision else None


def build_index(
    source_dir: Path | None = None,
    chroma_dir: Path | None = None,
    model_name: str | None = None,
    force: bool = False,
    offline: bool = True,
    embedder=None,
    append: bool = False,
    progress: Progress | None = None,
) -> dict:
    """Build a complete generation, validate it, then atomically activate it.

    ``append`` is the compatibility spelling for schema-v2 sync: the corpus is
    reconciled as a full snapshot, so additions, edits and deletions are all
    reflected and stale chunks cannot survive.
    """
    source = Path(source_dir) if source_dir is not None else config.source_dir()
    root = Path(chroma_dir) if chroma_dir is not None else config.chroma_dir()
    selected_model = model_name or config.MODEL_NAME
    report = progress or (lambda _message: None)

    config.check_ascii_path(root, "索引")
    if not source.is_dir():
        raise FileNotFoundError(f"corpus directory not found: {source}")

    try:
        current = load_current(root)
    except FileNotFoundError:
        current = None
    except IndexSchemaMismatch:
        if not force:
            raise
        current = None
    if current is not None and not force and not append:
        manifest = read_manifest(current)
        raise RuntimeError(
            f"index already has {manifest['corpus']['chunks']} chunks; "
            "use --force to rebuild or --append to sync"
        )

    report(f"Loading model: {selected_model}")
    model = embedder if embedder is not None else _load_embedder(selected_model, offline)
    dimension = _embedding_dimension(model)
    tokenizer = getattr(model, "tokenizer", None)
    report(f"Embedding dimension: {dimension}")

    report(f"Reading corpus: {source}")
    documents = collect_markdown(
        source,
        max_tokens=DEFAULT_MAX_TOKENS,
        overlap_tokens=DEFAULT_OVERLAP_TOKENS,
        tokenizer=tokenizer,
    )
    markdown_files = list(source.rglob("*.md"))
    if not documents:
        if not markdown_files:
            raise RuntimeError(f"corpus contains no markdown files: {source}")
        raise RuntimeError(
            f"corpus has {len(markdown_files)} markdown file(s) but zero chunks"
        )

    old_ids = _existing_ids(root)
    new_ids = {document["id"] for document in documents}
    generation = new_generation(root)
    try:
        import chromadb

        client = chromadb.PersistentClient(
            path=str(generation / "chroma"), settings=config.chroma_settings()
        )
        collection = client.create_collection(
            name=config.COLLECTION_NAME,
            metadata={
                "description": "UE Game Development Knowledge Base",
                "hnsw:space": "cosine",
                "schema_version": INDEX_SCHEMA_VERSION,
                "embedding_model": selected_model,
                "embedding_dimension": dimension,
            },
        )

        texts = [document["text"] for document in documents]
        identifiers = [document["id"] for document in documents]
        metadata = [
            {"source": document["source"], "heading": document["heading"]}
            for document in documents
        ]
        batch_size = 64
        report(f"Embedding {len(texts)} chunks")
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            with config.offline_huggingface(offline):
                embeddings = model.encode(
                    batch, show_progress_bar=False, normalize_embeddings=True
                )
            collection.add(
                ids=identifiers[start : start + batch_size],
                embeddings=embeddings.tolist(),
                documents=batch,
                metadatas=metadata[start : start + batch_size],
            )
            report(f"Embedded {min(start + batch_size, len(texts))}/{len(texts)}")

        build_bm25(documents, generation / "bm25.json")
        fingerprint, document_count = corpus_fingerprint(source)
        manifest = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "package_version": __version__,
            "built_at": utc_now(),
            "embedding": {
                "model": selected_model,
                "revision": _model_revision(model),
                "dimension": dimension,
                "normalization": "l2",
            },
            "chunker": {
                "version": CHUNKER_VERSION,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "overlap_tokens": DEFAULT_OVERLAP_TOKENS,
            },
            "corpus": {
                "sha256": fingerprint,
                "source": str(source.resolve()),
                "documents": document_count,
                "chunks": len(documents),
            },
        }
        import json

        (generation / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if collection.count() != len(documents):
            raise RuntimeError(
                f"index validation failed: {collection.count()} != {len(documents)}"
            )
        if not (generation / "bm25.json").is_file():
            raise RuntimeError("index validation failed: bm25.json missing")

        activate(root, generation)
        cleanup_generations(root, keep=2)
    except Exception:
        discard_incomplete(generation)
        raise

    report(f"Index ready: {root} ({len(documents)} chunks)")
    return {
        "files": len(markdown_files),
        "chunks": len(documents),
        "added": len(new_ids - old_ids),
        "removed": len(old_ids - new_ids),
        "unchanged": len(old_ids & new_ids),
        "collection": config.COLLECTION_NAME,
        "chroma_dir": str(root),
        "generation": generation.name,
        "schema_version": INDEX_SCHEMA_VERSION,
    }
