"""ue-kb command-line interface with stable JSON contracts."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

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
        mirror_environment = os.environ.copy()
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


def main(argv: list[str] | None = None) -> int:
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

    download = subcommands.add_parser("download-model", help="cache the embedding model")
    download.add_argument("--model", default=config.MODEL_NAME)
    download.add_argument("--json", action="store_true")
    download.set_defaults(func=cmd_download_model)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
