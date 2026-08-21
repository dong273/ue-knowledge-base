"""ue-kb command-line interface with stable JSON contracts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import ue_knowledge
from . import __version__, config
from .build import build_index
from .index_store import (
    IndexErrorBase,
    IndexSchemaMismatch,
    corpus_fingerprint,
    load_current,
    read_manifest,
)
from .query import format_results, query

HF_MIRROR = "https://hf-mirror.com"


def _emit(payload, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)


def _error_payload(exc: Exception, default_code: str = "RUNTIME_ERROR") -> dict[str, str]:
    if isinstance(exc, IndexErrorBase):
        return exc.as_dict()
    if isinstance(exc, config.AsciiPathError):
        return {"code": "INVALID_INDEX_PATH", "message": str(exc), "action": "choose an ASCII-only --db path"}
    if isinstance(exc, FileNotFoundError):
        message = str(exc)
        if "corpus" in message.lower():
            return {"code": "CORPUS_NOT_FOUND", "message": message, "action": "check --source or UE_KB_SOURCE"}
        return {"code": "INDEX_NOT_FOUND", "message": message, "action": "ue-kb build"}
    message = str(exc)
    lowered = message.lower()
    if any(word in lowered for word in ("hnsw", "segment", "backfill", "corrupt", "sqlite")):
        return {"code": "INDEX_CORRUPT", "message": message, "action": "ue-kb build --force"}
    return {"code": default_code, "message": message, "action": "ue-kb download-model"}


def _fail(exc: Exception, json_mode: bool, default_code: str = "RUNTIME_ERROR") -> int:
    payload = _error_payload(exc, default_code)
    if json_mode:
        _emit(payload, True)
        print(f"[!] {payload['message']}", file=sys.stderr)
    else:
        print(f"[!] {payload['message']}\n    下一步: {payload['action']}", file=sys.stderr)
    return 1


def cmd_build(args: argparse.Namespace) -> int:
    try:
        summary = build_index(
            source_dir=config.source_dir(args.source),
            chroma_dir=config.chroma_dir(args.db),
            model_name=args.model,
            force=args.force,
            append=args.append,
            offline=not args.online,
            progress=lambda message: print(f"[*] {message}", file=sys.stderr),
        )
    except Exception as exc:
        return _fail(exc, args.json)
    _emit(summary, args.json)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    try:
        results = query(
            args.query,
            top_k=args.top_k,
            chroma_dir=config.chroma_dir(args.db),
            model_name=args.model,
            offline=not args.online,
            profile=args.profile,
        )
    except Exception as exc:
        return _fail(exc, args.json)
    _emit(results if args.json else format_results(results, args.query), args.json)
    return 0


def _info(args: argparse.Namespace) -> dict:
    root = config.chroma_dir(args.db)
    config.check_ascii_path(root, "索引")
    generation = load_current(root)
    manifest = read_manifest(generation)
    source = config.source_dir(args.source) if args.source else config.source_dir(
        manifest["corpus"].get("source")
    )
    stale = None
    if source.is_dir():
        fingerprint, _ = corpus_fingerprint(source)
        stale = fingerprint != manifest["corpus"]["sha256"]
    return {
        "collection": config.COLLECTION_NAME,
        "documents": manifest["corpus"]["chunks"],
        "chroma_dir": str(root),
        "generation": generation.name,
        "manifest": manifest,
        "stale": stale,
        "model_matches": manifest["embedding"]["model"] == args.model,
    }


def cmd_info(args: argparse.Namespace) -> int:
    try:
        payload = _info(args)
    except Exception as exc:
        return _fail(exc, args.json)
    if args.json:
        _emit(payload, True)
    else:
        print(f"collection : {payload['collection']}")
        print(f"documents  : {payload['documents']}")
        print(f"generation : {payload['generation']}")
        print(f"schema     : {payload['manifest']['schema_version']}")
        print(f"model      : {payload['manifest']['embedding']['model']}")
        print(f"model match: {payload['model_matches']}")
        print(f"stale      : {payload['stale']}")
        print(f"chroma_dir : {payload['chroma_dir']}")
    return 0


def _doctor_index(args: argparse.Namespace) -> dict:
    """Return a stable, compact index identity for ``ue-kb doctor``."""
    empty = {
        "ready": False,
        "generation": None,
        "schema_version": None,
        "corpus": {
            "source": None,
            "sha256": None,
            "documents": None,
            "chunks": None,
            "stale": None,
        },
        "model_matches": False,
    }
    try:
        info = _info(args)
    except Exception as exc:
        empty["error"] = _error_payload(exc)
        return empty

    manifest = info["manifest"]
    corpus = manifest.get("corpus", {})
    return {
        "ready": True,
        "generation": info["generation"],
        "schema_version": manifest.get("schema_version"),
        "corpus": {
            "source": corpus.get("source"),
            "sha256": corpus.get("sha256"),
            "documents": corpus.get("documents"),
            "chunks": corpus.get("chunks"),
            "stale": info["stale"],
        },
        "model_matches": info["model_matches"],
    }


def _mcp_smoke(args: argparse.Namespace) -> dict:
    """Exercise the local MCP stdio handshake and optionally one query."""
    requests = [
        {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ue-kb-doctor", "version": __version__},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "ue_kb_info", "arguments": {}},
        },
    ]
    if args.mcp_smoke_query:
        requests.append({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "ue_kb_query",
                "arguments": {"query": args.mcp_smoke_query, "top_k": 3},
            },
        })
    command = [sys.executable, "-m", "ue_knowledge.cli", "serve", "--model", args.model]
    if args.db:
        command.extend(["--db", str(config.chroma_dir(args.db))])
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    payload = {
        "checked": True,
        "ok": False,
        "protocol_version": None,
        "server_version": None,
        "tools": [],
        "info_ready": False,
        "query_ok": None,
    }
    try:
        result = subprocess.run(
            command,
            input="\n".join(json.dumps(request, ensure_ascii=False) for request in requests) + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
        return payload

    if result.returncode != 0:
        payload["error"] = (
            f"MCP server exited with code {result.returncode}: {result.stderr[-500:]}"
        )
        return payload
    try:
        responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        by_id = {response.get("id"): response for response in responses}
        initialize = by_id[1]["result"]
        tools = by_id[2]["result"]["tools"]
        info = by_id[3]["result"]["structuredContent"]
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "ue_kb_query", "ue_kb_info", "ue_kb_topics", "ue_kb_glossary",
        ]
        payload.update({
            "protocol_version": initialize["protocolVersion"],
            "server_version": initialize["serverInfo"]["version"],
            "tools": tool_names,
            "info_ready": bool(info.get("index_ready")),
            "tools_complete": tool_names == expected_tools,
            "ok": (
                initialize["protocolVersion"] == "2024-11-05"
                and tool_names == expected_tools
            ),
        })
        if args.mcp_smoke_query:
            query_result = by_id[4]["result"]
            hits = query_result.get("structuredContent") or []
            payload["query_ok"] = bool(
                not query_result.get("isError")
                and hits
                and all(key in hits[0] for key in ("source", "heading", "raw_score", "rank"))
            )
            payload["query"] = args.mcp_smoke_query
            payload["ok"] = payload["ok"] and payload["query_ok"]
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        payload["error"] = f"invalid MCP response: {exc}"
        return payload


def cmd_doctor(args: argparse.Namespace) -> int:
    package = {
        "version": __version__,
        "module_path": str(Path(ue_knowledge.__file__).resolve()),
        "corpus_path": str(config.source_dir(args.source).resolve()),
    }
    index = _doctor_index(args)
    mcp = _mcp_smoke(args) if args.mcp_smoke else {
        "checked": False,
        "ok": None,
        "protocol_version": None,
        "server_version": None,
        "tools": [],
        "info_ready": False,
        "query_ok": None,
    }
    corpus_status = index.get("corpus") or {}
    ok = bool(
        index.get("ready")
        and index.get("model_matches")
        and corpus_status.get("stale") is False
    )
    if args.mcp_smoke:
        ok = ok and bool(mcp.get("ok") and mcp.get("info_ready"))
        if args.mcp_smoke_query:
            ok = ok and bool(mcp.get("query_ok"))
    payload = {
        "schema_version": 1,
        "ok": ok,
        "package": package,
        "index": index,
        "mcp": mcp,
    }
    if args.json:
        _emit(payload, True)
    else:
        print(f"doctor: {'ok' if ok else 'failed'}")
        print(f"package : {package['version']} ({package['module_path']})")
        print(f"index   : {index.get('ready', False)}")
        if args.mcp_smoke:
            print(f"mcp     : {mcp.get('ok', False)}")
    return 0 if ok else 1


def _download_model_once(model_name: str) -> None:
    from sentence_transformers import SentenceTransformer

    SentenceTransformer(model_name)


def cmd_download_model(args: argparse.Namespace) -> int:
    model_name = args.model or config.MODEL_NAME
    print(f"[*] 下载模型: {model_name}（首次约 100MB）", file=sys.stderr)
    try:
        _download_model_once(model_name)
    except Exception as first_error:
        print(f"[!] 官方源下载失败: {first_error}", file=sys.stderr)
        if os.environ.get("HF_ENDPOINT") == HF_MIRROR:
            return _fail(first_error, args.json, "MODEL_UNAVAILABLE")
        mirror_environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        mirror_environment["HF_ENDPOINT"] = HF_MIRROR
        print(f"[*] 使用镜像重试: {HF_MIRROR}", file=sys.stderr)
        result = subprocess.run(
            [
                sys.executable, "-m", "ue_knowledge.cli", "download-model",
                "--model", model_name, "--json",
            ],
            env=mirror_environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        if result.returncode != 0:
            try:
                child_error = json.loads(result.stdout)
                return _fail(RuntimeError(child_error["message"]), args.json, "MODEL_UNAVAILABLE")
            except (json.JSONDecodeError, KeyError):
                return _fail(first_error, args.json, "MODEL_UNAVAILABLE")
    _emit({"model": model_name, "cached": True} if args.json else "[✓] 模型已缓存。", args.json)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve_loop

    serve_loop(
        sys.stdin,
        sys.stdout,
        chroma_dir=args.db,
        model_name=args.model,
        top_k=args.top_k,
    )
    return 0


def _force_utf8_streams() -> None:
    """Make output robust on non-UTF-8 consoles/pipes.

    On en-US Windows (cp1252) or other legacy code pages, printing Chinese
    messages/JSON to a pipe raises UnicodeEncodeError and the CLI dies with
    a traceback instead of returning a machine-readable payload. Reconfigure
    to UTF-8 with backslashreplace so output is always parseable.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
    parser = argparse.ArgumentParser(
        prog="ue-kb",
        description="UE Knowledge Base — offline Unreal Engine knowledge search",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build", help="build or sync the index")
    build.add_argument("--source", help="corpus directory")
    build.add_argument("--db", help="index root")
    build.add_argument("--model", default=config.MODEL_NAME)
    build.add_argument("--force", action="store_true")
    build.add_argument("--append", action="store_true", help="sync additions, edits and deletions")
    build.add_argument("--online", action="store_true")
    build.add_argument("--json", action="store_true")
    build.set_defaults(func=cmd_build)

    search = subcommands.add_parser("query", help="search the index")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--db")
    search.add_argument("--model", default=config.MODEL_NAME)
    search.add_argument("--profile", choices=("hybrid", "vector"), default="hybrid")
    search.add_argument("--online", action="store_true")
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=cmd_query)

    info = subcommands.add_parser("info", help="show manifest and index health")
    info.add_argument("--db")
    info.add_argument("--source")
    info.add_argument("--model", default=config.MODEL_NAME)
    info.add_argument("--json", action="store_true")
    info.set_defaults(func=cmd_info)

    doctor = subcommands.add_parser("doctor", help="diagnose package, index and MCP runtime identity")
    doctor.add_argument("--source", help="corpus directory")
    doctor.add_argument("--db", help="index root")
    doctor.add_argument("--model", default=config.MODEL_NAME)
    doctor.add_argument("--mcp-smoke", action="store_true", help="exercise the local MCP stdio handshake")
    doctor.add_argument("--mcp-smoke-query", help="also verify one MCP query in the smoke check")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    serve = subcommands.add_parser(
        "serve",
        help="MCP stdio server (loads the model once; agents keep it running)",
    )
    serve.add_argument("--db", help="index root (default: user data dir)")
    serve.add_argument("--model", default=config.MODEL_NAME)
    serve.add_argument("--top-k", type=int, default=5)
    serve.set_defaults(func=_cmd_serve)

    download = subcommands.add_parser("download-model", help="cache the embedding model")
    download.add_argument("--model", default=config.MODEL_NAME)
    download.add_argument("--json", action="store_true")
    download.set_defaults(func=cmd_download_model)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
