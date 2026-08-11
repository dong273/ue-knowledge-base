"""ue_knowledge — offline semantic search over Unreal Engine development docs.

Build a local vector index from the bundled knowledge/ markdown corpus
(BAAI/bge-small-zh-v1.5 embeddings + ChromaDB), then query it with a CLI
or from Python. Zero API cost, fully offline after the one-time model download.
"""

__version__ = "0.1.0"
