"""``ue-kb serve`` — a minimal MCP (Model Context Protocol) stdio server.

Loads the embedding model ONCE, then answers ``tools/call`` queries in
process. This is the answer to the cold-start cost of per-query CLI
spawning (measured ~12s cold vs ~0.07s warm in the quality gate): an agent
that keeps the server running pays the model load once per session instead
of once per query.

Protocol: JSON-RPC 2.0 over stdin/stdout, newline-delimited JSON messages
(MCP stdio transport). Only the tools subset is implemented — exactly what
agents need, with zero new dependencies.

Usage:
    ue-kb serve [--db <dir>] [--model <name>] [--top-k N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config
from .query import query

PROTOCOL_VERSION = "2024-11-05"
TOOL_NAME = "ue_kb_query"
TOOL_DESCRIPTION = (
    "Hybrid semantic search over the local Unreal Engine knowledge base "
    "(31 topics, 86 docs, BGE + BM25 RRF fusion). Returns top hits with "
    "source / heading / text / raw_score / rank. Use raw_score for "
    "confidence: >=0.025 strong, 0.015-0.025 moderate, <0.012 weak; all "
    "hits below 0.012 means the KB has no coverage."
)


def _tool_definition(top_k_default: int) -> dict:
    return {
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
    }


def _rpc_response(request_id, result=None, error=None) -> str:
    payload: dict = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return json.dumps(payload, ensure_ascii=False)


def _call_tool(params: dict, chroma_dir, model_name, embedder, top_k_default) -> dict:
    name = (params or {}).get("name")
    arguments = (params or {}).get("arguments") or {}
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
        results = query(
            query_text,
            top_k=int(top_k),
            chroma_dir=Path(chroma_dir) if chroma_dir else None,
            model_name=model_name,
            offline=True,
            embedder=embedder,
            profile=profile,
        )
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
    if embedder is None:
        from sentence_transformers import SentenceTransformer

        with config.offline_huggingface(True):
            embedder = SentenceTransformer(selected, local_files_only=True)
    tool = _tool_definition(top_k)
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
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ue-knowledge-base", "version": __version__},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [tool]}
        elif method == "tools/call":
            result = _call_tool(params, chroma_dir, selected, embedder, top_k)
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
