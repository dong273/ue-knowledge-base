"""ue_knowledge — offline hybrid search over Unreal Engine development docs.

Build a local vector index from the bundled knowledge/ markdown corpus
(BGE embeddings + BM25 + ChromaDB), then query it with a CLI
or from Python. Zero API cost, fully offline after the one-time model download.
"""

__version__ = "0.6.1"
