"""ue-kb command-line interface: build / query / info / download-model."""

import argparse
import json
import os
import subprocess
import sys

from . import __version__, config
from .build import build_index
from .query import format_results, query

# HuggingFace 国内镜像。官方源下载失败时自动切换重试（无需手动 export）。
HF_MIRROR = "https://hf-mirror.com"


def _model_unavailable_hint(exc: Exception) -> str:
    return (
        "Model 未找到或无法加载。首次使用请先运行:\n"
        "    ue-kb download-model\n"
        "（网络受限时会自动切换到 hf-mirror 镜像，无需代理）\n"
        f"原始错误: {exc}"
    )


def cmd_build(args: argparse.Namespace) -> int:
    try:
        summary = build_index(
            source_dir=config.source_dir(args.source),
            chroma_dir=config.chroma_dir(args.db),
            model_name=args.model,
            force=args.force,
            offline=not args.online,
        )
    except FileNotFoundError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[!] {_model_unavailable_hint(e)}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    try:
        results = query(
            args.query,
            top_k=args.top_k,
            chroma_dir=config.chroma_dir(args.db),
            model_name=args.model,
            offline=not args.online,
        )
    except Exception as e:
        print(f"[!] {_model_unavailable_hint(e)}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_results(results, args.query))
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    import chromadb

    chroma = config.chroma_dir(args.db)
    try:
        client = chromadb.PersistentClient(path=str(chroma))
        collection = client.get_collection(config.COLLECTION_NAME)
    except Exception as e:
        print(f"[!] 索引不存在: {chroma}（先运行 ue-kb build）\n{e}", file=sys.stderr)
        return 1
    meta = collection.metadata or {}
    print(f"collection : {collection.name}")
    print(f"documents  : {collection.count()}")
    print(f"description: {meta.get('description', '')}")
    print(f"chroma_dir : {chroma}")
    return 0


def _download_model_once(model_name: str) -> None:
    """Load the embedding model, downloading it if needed (raises on failure)."""
    from sentence_transformers import SentenceTransformer

    SentenceTransformer(model_name)


def cmd_download_model(args: argparse.Namespace) -> int:
    model_name = args.model or config.MODEL_NAME
    print(f"[*] 下载模型: {model_name}（首次约 100MB，之后完全离线）")
    try:
        _download_model_once(model_name)
    except Exception as e:
        print(f"[!] 官方源下载失败: {e}", file=sys.stderr)
        if os.environ.get("HF_ENDPOINT") != HF_MIRROR:
            print(f"[*] 自动切换到国内镜像重试（无需代理）: {HF_MIRROR}")
            os.environ["HF_ENDPOINT"] = HF_MIRROR
            # huggingface_hub 在进程启动时读取 HF_ENDPOINT；改环境变量后
            # 需重启进程才生效，这里用子进程以新环境变量重新下载。
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "ue_knowledge.cli", "download-model",
                     "--model", model_name],
                    env=os.environ,
                )
                if r.returncode == 0:
                    return 0
            except Exception as e2:
                print(f"[!] 镜像重试异常: {e2}", file=sys.stderr)
        print("[!] 镜像源下载也失败，请检查网络后重试。", file=sys.stderr)
        return 1
    print("[✓] 模型已缓存。现在可以运行: ue-kb build && ue-kb query")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ue-kb",
        description="UE Knowledge Base — offline semantic search over Unreal Engine dev docs",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="build the vector index from knowledge/")
    p_build.add_argument("--source", help="corpus dir (default: repo knowledge/)")
    p_build.add_argument("--db", help="chroma dir (default: repo .chroma_db/)")
    p_build.add_argument("--model", default=config.MODEL_NAME, help="embedding model")
    p_build.add_argument("--force", action="store_true", help="rebuild even if index exists")
    p_build.add_argument("--online", action="store_true", help="allow model download if missing")
    p_build.set_defaults(func=cmd_build)

    p_query = sub.add_parser("query", help="semantic search")
    p_query.add_argument("query", help="search text (e.g. \"GAS cooldown\")")
    p_query.add_argument("--top-k", type=int, default=5)
    p_query.add_argument("--db", help="chroma dir")
    p_query.add_argument("--model", default=config.MODEL_NAME, help="embedding model")
    p_query.add_argument("--online", action="store_true", help="allow model download if missing")
    p_query.add_argument("--json", action="store_true", help="raw JSON output")
    p_query.set_defaults(func=cmd_query)

    p_info = sub.add_parser("info", help="show index stats")
    p_info.add_argument("--db", help="chroma dir")
    p_info.set_defaults(func=cmd_info)

    p_dl = sub.add_parser("download-model", help="download the embedding model once")
    p_dl.add_argument("--model", default=config.MODEL_NAME)
    p_dl.set_defaults(func=cmd_download_model)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
