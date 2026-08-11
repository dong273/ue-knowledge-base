# UE Knowledge Base — a local semantic knowledge base for UE developers

[![PyPI version](https://img.shields.io/pypi/v/ue-knowledge-base.svg)](https://pypi.org/project/ue-knowledge-base/)
[![CI](https://github.com/dong273/ue-knowledge-base/actions/workflows/ci.yml/badge.svg)](https://github.com/dong273/ue-knowledge-base/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> A local semantic knowledge base for UE development: 83 original Chinese
> documents, indexed with BGE embeddings + ChromaDB. Download the ~100MB
> model once, then search fully offline on a laptop CPU — no API costs.

## Why this exists

| Problem | Status quo | This project |
|---|---|---|
| **UE knowledge is scattered** | Answers live in forums, blogs, videos and English docs; one question = a dozen sources | 29 topics, **83 structured original documents**, one search away |
| **LLMs hallucinate UE APIs** | Generic models blur the UE 5.4 vs 5.7 differences and hand you "looks right" code | Documents are distilled from **real project work**, with **copy-pasteable C++ patterns** checked against specific engine versions |
| **Cloud RAG costs money & leaks code** | Every query ships your game code to an API and bills you per token | **100% local, zero API cost** — code never leaves your machine |
| **English-only docs are a tax** | Official docs are English; translation loses context and terminology | **Native Chinese corpus + Chinese-first embeddings** — Chinese queries hit best |

Covers: Gameplay Ability System, character movement, animation, AI navigation,
networking/replication, UMG/Slate, Niagara, Mass Entity, State Trees, PCG,
materials/rendering, module build system, editor tools, and more
(full 29-topic list under `knowledge/`).

## Highlights

- 83 original Chinese docs, indexed into **1,424 searchable chunks** — content
  distilled from actual project work
- Real Chinese query → top-1 at **60.5% similarity** (see actual output below)
- No API key, no tokens, no server — `pip install` and go
- Embedding + retrieval happen locally; code never leaves your machine
- Every command supports `--json`; patterns for Hermes / Claude Code /
  OpenCode / any custom pipeline
- China-friendly: GitHub mirror clone + Tsinghua PyPI + automatic
  hf-mirror fallback — no proxy needed
- ~100MB model, laptop CPU, no GPU; index build ~1 min

## Quick start

```bash
pip install ue-knowledge-base   # install

ue-kb download-model            # one-time ~100MB model (auto-falls back to hf-mirror)
ue-kb build                     # build the index (~1 min, fully offline from here)
ue-kb query "GAS ability cooldown"
ue-kb query "角色移动 速度衰减" --json   # JSON output for agents
```

## Real query output

```text
$ ue-kb query "GAS 技能冷却"
🔍 UE 知识库检索：GAS 技能冷却

[1] ue-gameplay-abilities/references/gas-input-integration.md › 问题 (匹配度: 60.5%)
    ## 问题  UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时，
    容易陷入两个极端：- **全 GAS** → 所有输入走 GAS，但 WASD 轴输入不适合 GAS 的
    事件模型，且 `CommitAbility` 的 GC 延迟影响跳跃手感 - **全直调** → 绕过 GAS，
    失去标签阻断、冷却、属性驱动的 BUFF/DEBUFF...
[2] ue-gameplay-abilities/references/gas-input-integration.md › Jump — GAS 即时技能 (匹配度: 57.1%)
    ### Jump — GAS 即时技能
    `cpp void AMyCharacter::OnJumpStarted() {
        if (AbilitySystem)
            AbilitySystem->TryActivateAbilityByClass(UGA_Jump::StaticClass());
    } // GA_Jump.cpp ...
```

Hits include usable C++ patterns, not just related text.

## Install in mainland China (zero proxy)

```bash
# 1. Get the code (GitHub mirrors, pick either)
git clone --depth 1 https://gh-proxy.com/https://github.com/dong273/ue-knowledge-base.git
#   git clone --depth 1 https://ghfast.top/https://github.com/dong273/ue-knowledge-base.git

# 2. Install dependencies (Tsinghua PyPI mirror)
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. Download the model (mirror fallback is automatic)
ue-kb download-model

# 4. Build the index (fully local; offline from here on)
ue-kb build

# 5. Search
ue-kb query "GAS ability cooldown"
```

## CLI reference

| Command | Description | Example |
| --- | --- | --- |
| `ue-kb build` | Chunk + embed the corpus into ChromaDB | `ue-kb build --force` |
| `ue-kb build --append` | Incremental indexing — only new documents are processed; existing content stays untouched; no full rebuild for daily corpus updates | `ue-kb build --append` |
| `ue-kb query "..."` | Semantic search; top-k hits with source + heading | `ue-kb query "角色移动 速度衰减" --top-k 5` |
| `ue-kb info` | Index stats (document count, chroma dir) | `ue-kb info` |
| `ue-kb download-model` | One-time embedding model download | `ue-kb download-model` |
| `--json` | Machine-readable output (agents) | `ue-kb query "..." --json` |
| `--db <dir>` | Custom chroma dir (use ASCII path on Windows, see FAQ) | `ue-kb build --db C:/uekb/.chroma_db` |
| `--source <dir>` | Custom corpus dir | `ue-kb build --source my-docs/` |
| `--model <name>` | Custom sentence-transformers model | `ue-kb query "..." --model BAAI/bge-large-zh-v1.5` |
| `--force` | Rebuild even if an index exists | `ue-kb build --force` |
| `--online` | Allow model download if missing (default: offline) | `ue-kb build --online` |

## Python API

```python
from ue_knowledge.query import query

for hit in query("GAS cooldown", top_k=5):
    print(hit["source"], hit["heading"], hit["score"])   # source, heading, similarity
```

## Agent integration

`ue-kb` is built for AI agents: fully offline, zero cost per query, `--json`
on every command. Integration examples in
[docs/agent-integration.md](docs/agent-integration.md):

- **Hermes Agent** skill wrapper (expose the search as an agent tool)
- **Claude Code** slash command
- **OpenCode** command
- Plain **Python snippet** for any custom pipeline

## Extending the corpus

You can extend the corpus:

1. Add a markdown file under `knowledge/<topic>/` (`##`/`###` headings — the
   indexer chunks on heading boundaries);
2. `ue-kb build --append` — **no full rebuild needed**;
3. Or index any local `.md` directory: `ue-kb build --source my-docs/`.

For indexing **Unreal Engine C++ header comments** or **Epic official docs**,
see `scripts/index_engine_source.py` and `scripts/crawl_epic_docs.py`
(they expect local engine/UE paths — extracted index data is generated
locally and **not redistributed**, out of respect for Epic's copyright).

## FAQ

- **Windows: `Cannot open header file` when querying?** — hnswlib cannot open
  its index files under non-ASCII paths (Chinese usernames/folders). The CLI
  rejects such paths up front: use a pure-ASCII index directory, e.g.
  `ue-kb build --db C:/uekb/.chroma_db`. The corpus itself may stay anywhere.
- **Slow model download in mainland China?** — `ue-kb download-model`
  automatically retries via `hf-mirror.com` when the official source fails;
  no proxy or manual `HF_ENDPOINT` needed.
- **`Index ready` but queries say the index is missing?** — the index
  directory was moved/deleted, or a `chromadb` upgrade changed the format.
  Rebuild with `ue-kb build --force` (`chromadb>=0.5,<1.0` is pinned to avoid
  the 1.x Rust backend that cannot reload its own HNSW index).
- **Two harmless telemetry lines on stderr?** — a `posthog`/chromadb 0.6.x
  version quirk; pinned `posthog<4` suppresses it. No functional impact.

## License

MIT. The knowledge documents are original writing; no engine source code or
verbatim Epic documentation is included.
