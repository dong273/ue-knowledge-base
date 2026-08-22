"""``ue-kb serve`` — a minimal MCP (Model Context Protocol) stdio server.

Loads the embedding model ONCE, then answers ``tools/call`` queries in
process. This is the answer to the cold-start cost of per-query CLI
spawning (measured ~12s cold vs ~0.07s warm in the quality gate): an agent
that keeps the server running pays the model load once per session instead
of once per query.

Protocol: JSON-RPC 2.0 over stdin/stdout, newline-delimited JSON messages
(MCP stdio transport). Implements the tools + resources subsets with zero
new dependencies.

Tools:
  ue_kb_query     — hybrid semantic search (top hits with raw_score/rank)
  ue_kb_info      — index status: generation, chunk count, model, schema
  ue_kb_topics    — the 31 topic identifiers (canonical + aliases)
  ue_kb_glossary  — terminology expansion table (topic -> canonical/aliases/identifiers)

Resources:
  ue-kb://topic/<id> — one resource per topic (SKILL.md content via resources/read)

Usage:
    ue-kb serve [--db <dir>] [--model <name>] [--top-k N]
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

import ue_knowledge
from . import __version__, config
from .query import query
from .retrieval import glossary

PROTOCOL_VERSION = "2024-11-05"
TOOL_NAME = "ue_kb_query"
TOOL_DESCRIPTION = (
    "Hybrid semantic search over the local Unreal Engine knowledge base "
    "(BGE + BM25 RRF fusion). Call ue_kb_info for current corpus inventory. "
    "Returns top hits with "
    "source / heading / text / raw_score / rank. Use raw_score for "
    "confidence: >=0.025 strong, 0.015-0.025 moderate, <0.012 weak; all "
    "hits below 0.012 means the KB has no coverage."
)

INFO_TOOL_NAME = "ue_kb_info"
INFO_TOOL_DESCRIPTION = (
    "Index status and runtime identity: generation id, schema version, corpus "
    "source/hash/document/chunk counts, stale state, embedding model, module "
    "path, package version and topic count. Use before querying to learn "
    "whether an index exists and matches the configured model."
)

TOPICS_TOOL_NAME = "ue_kb_topics"
TOPICS_TOOL_DESCRIPTION = (
    "List the topic identifiers of the knowledge base with their canonical "
    "names and aliases. Useful to scope a query or to learn the vocabulary "
    "the KB covers."
)

GLOSSARY_TOOL_NAME = "ue_kb_glossary"
GLOSSARY_TOOL_DESCRIPTION = (
    "The terminology expansion table: for each topic the canonical name, "
    "Chinese aliases and code identifiers. Optionally filter by topic."
)


def _topics() -> list[dict]:
    return [
        {
            "topic": entry["topic"],
            "canonical": entry.get("canonical", ""),
            "aliases": entry.get("aliases", []),
        }
        for entry in glossary()
    ]


RESOURCE_URI_PREFIX = "ue-kb://topic/"


def _read_resource(uri) -> dict | None:
    """MCP resources/read result for a ``ue-kb://topic/<id>`` URI, or None."""
    if not isinstance(uri, str) or not uri.startswith(RESOURCE_URI_PREFIX):
        return None
    topic = uri[len(RESOURCE_URI_PREFIX):]
    if not topic or "/" in topic or "\\" in topic:
        return None
    if topic not in {entry["topic"] for entry in glossary()}:
        return None
    path = config.DEFAULT_SOURCE_DIR / topic / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}


def _tool_definitions(top_k_default: int) -> list[dict]:
    return [
        {
            "name": TOOL_NAME,
            "description": TOOL_DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The UE development question (English API terms work best).",
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": top_k_default,
                    },
                    "profile": {
                        "type": "string",
                        "enum": ["hybrid", "vector"],
                        "default": "hybrid",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": INFO_TOOL_NAME,
            "description": INFO_TOOL_DESCRIPTION,
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": TOPICS_TOOL_NAME,
            "description": TOPICS_TOOL_DESCRIPTION,
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": GLOSSARY_TOOL_NAME,
            "description": GLOSSARY_TOOL_DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional topic id filter, e.g. ue-gameplay-abilities.",
                    },
                },
            },
        },
    ]


def _rpc_response(request_id, result=None, error=None) -> str:
    payload: dict = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return json.dumps(payload, ensure_ascii=False)


def _index_info(chroma_dir, model_name) -> dict:
    """Lightweight index status without loading chroma (reads bm25.json)."""
    from .index_store import corpus_fingerprint, load_current, read_manifest

    root = Path(chroma_dir) if chroma_dir else config.chroma_dir()
    module_path = str(Path(ue_knowledge.__file__).resolve())
    package = {
        "module_path": module_path,
        "model_name": model_name,
        "package_version": __version__,
        "topic_count": len(_topics()),
        "chroma_dir": str(root),
    }
    try:
        generation = load_current(root)
        manifest = read_manifest(generation)
        bm25 = generation / "bm25.json"
        chunk_count = 0
        if bm25.is_file():
            chunk_count = len(json.loads(bm25.read_text(encoding="utf-8"))["documents"])
        corpus = manifest.get("corpus", {})
        source = Path(corpus["source"]) if corpus.get("source") else None
        stale = None
        if source is not None and source.is_dir() and corpus.get("sha256"):
            fingerprint, _ = corpus_fingerprint(source)
            stale = fingerprint != corpus["sha256"]
        embedding = manifest.get("embedding", {})
        return {
            "index_ready": True,
            "generation": manifest.get("generation") or generation.name,
            "schema_version": manifest.get("schema_version"),
            "chunk_count": chunk_count,
            "embedding": embedding,
            "model_matches": embedding.get("model") == model_name,
            "corpus": {
                "source": corpus.get("source"),
                "sha256": corpus.get("sha256"),
                "documents": corpus.get("documents"),
                "chunks": corpus.get("chunks", chunk_count),
                "stale": stale,
            },
            **package,
            "chroma_dir": str(generation),
        }
    except Exception as exc:
        return {
            "index_ready": False,
            "error": f"{type(exc).__name__}: {exc}",
            "model_matches": False,
            "corpus": {
                "source": None,
                "sha256": None,
                "documents": None,
                "chunks": None,
                "stale": None,
            },
            **package,
        }


def _call_tool(params: dict, chroma_dir, model_name, embedder, top_k_default, search) -> dict:
    name = (params or {}).get("name")
    arguments = (params or {}).get("arguments") or {}
    if name == INFO_TOOL_NAME:
        info = _index_info(chroma_dir, model_name)
        return {
            "content": [{"type": "text", "text": json.dumps(info, ensure_ascii=False)}],
            "structuredContent": info,
            "isError": False,
        }
    if name == TOPICS_TOOL_NAME:
        topics = _topics()
        return {
            "content": [{"type": "text", "text": json.dumps(topics, ensure_ascii=False)}],
            "structuredContent": topics,
            "isError": False,
        }
    if name == GLOSSARY_TOOL_NAME:
        topic_filter = arguments.get("topic")
        entries = [
            {"topic": e["topic"], "canonical": e.get("canonical", ""),
             "aliases": e.get("aliases", []), "identifiers": e.get("identifiers", [])}
            for e in glossary()
            if not topic_filter or e["topic"] == topic_filter
        ]
        if topic_filter and not entries:
            return {
                "content": [{"type": "text", "text": f"unknown topic: {topic_filter}"}],
                "isError": True,
            }
        return {
            "content": [{"type": "text", "text": json.dumps(entries, ensure_ascii=False)}],
            "structuredContent": entries,
            "isError": False,
        }
    if name != TOOL_NAME:
        return {
            "content": [{"type": "text", "text": f"unknown tool: {name}"}],
            "isError": True,
        }
    query_text = arguments.get("query")
    if not query_text or not isinstance(query_text, str):
        return {
            "content": [{"type": "text", "text": "missing string argument: query"}],
            "isError": True,
        }
    top_k = arguments.get("top_k", top_k_default)
    profile = arguments.get("profile", "hybrid")
    try:
        results = search(query_text, int(top_k), profile)
    except Exception as exc:  # surfaced to the agent as a tool error
        return {
            "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
            "isError": True,
        }
    return {
        "content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False)}],
        "structuredContent": results,
        "isError": False,
    }


def serve_loop(
    stdin,
    stdout,
    chroma_dir=None,
    model_name: str | None = None,
    embedder=None,
    top_k: int = 5,
) -> None:
    """Run the MCP stdio loop until EOF. Testable with fake streams."""
    selected = model_name or config.MODEL_NAME

    # Lazy model load: the ~100MB embedding model takes ~12-14s to load,
    # which risks exceeding MCP client startup timeouts if paid during the
    # initialize handshake. Defer it to the first tools/call that actually
    # queries — initialize / tools/list / info / topics / glossary all
    # answer without the model.
    loaded_embedder = embedder

    def ensure_embedder():
        nonlocal loaded_embedder
        if loaded_embedder is None:
            from sentence_transformers import SentenceTransformer

            with config.offline_huggingface(True):
                loaded_embedder = SentenceTransformer(selected, local_files_only=True)
        return loaded_embedder

    @lru_cache(maxsize=64)
    def search(query_text: str, count: int, profile: str) -> list[dict]:
        # Embedder/chroma_dir/model are fixed for the process lifetime, so
        # caching on the (query, top_k, profile) tuple is safe. Repeated
        # agent queries skip re-embedding entirely.
        return query(
            query_text,
            top_k=count,
            chroma_dir=Path(chroma_dir) if chroma_dir else None,
            model_name=selected,
            offline=True,
            embedder=ensure_embedder(),
            profile=profile,
        )

    tools = _tool_definitions(top_k)
    resources = [
        {"uri": f"ue-kb://topic/{entry['topic']}", "name": entry["topic"],
         "mimeType": "text/markdown", "description": entry.get("canonical", "")}
        for entry in _topics()
    ]
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(_rpc_response(None, error={"code": -32700, "message": "parse error"}) + "\n")
            stdout.flush()
            continue
        if not isinstance(message, dict) or "id" not in message:
            continue  # notification — no response
        request_id = message["id"]
        method = message.get("method")
        params = message.get("params") or {}
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "ue-knowledge-base", "version": __version__},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tools}
        elif method == "tools/call":
            result = _call_tool(params, chroma_dir, selected, embedder, top_k, search)
        elif method == "resources/list":
            result = {"resources": resources}
        elif method == "resources/read":
            read = _read_resource(params.get("uri"))
            if read is None:
                stdout.write(
                    _rpc_response(
                        request_id,
                        error={"code": -32602, "message": f"unknown resource: {params.get('uri')}"},
                    )
                    + "\n"
                )
                stdout.flush()
                continue
            result = read
        else:
            stdout.write(
                _rpc_response(request_id, error={"code": -32601, "message": f"method not found: {method}"}) + "\n"
            )
            stdout.flush()
            continue
        stdout.write(_rpc_response(request_id, result=result) + "\n")
        stdout.flush()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ue-kb serve",
        description="MCP stdio server: load the model once, answer queries in process.",
    )
    parser.add_argument("--db", help="index root (default: user data dir)")
    parser.add_argument("--model", default=config.MODEL_NAME)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)
    config.force_utf8_streams()
    try:
        serve_loop(
            sys.stdin,
            sys.stdout,
            chroma_dir=args.db,
            model_name=args.model,
            top_k=args.top_k,
        )
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
