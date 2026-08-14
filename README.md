# UE Knowledge Base — a local semantic knowledge base for UE developers

[![PyPI version](https://img.shields.io/pypi/v/ue-knowledge-base.svg?v=0.6.0)](https://pypi.org/project/ue-knowledge-base/)
[![CI](https://github.com/dong273/ue-knowledge-base/actions/workflows/ci.yml/badge.svg)](https://github.com/dong273/ue-knowledge-base/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> A local semantic knowledge base for UE development: 86 original documents
> (79 English, 7 bilingual), indexed with BGE + BM25 hybrid retrieval. Download
> the ~100MB model once, then search fully offline on a laptop CPU — no API costs.

## Why this exists

| Problem | Status quo | This project |
|---|---|---|
| **UE knowledge is scattered** | Answers live in forums, blogs, videos and English docs; one question = a dozen sources | 31 topics, **86 structured original documents**, one search away |
| **LLMs hallucinate UE APIs** | Generic models blur the UE 5.4 vs 5.7 differences and hand you "looks right" code | Documents are distilled from **real project work**, with **copy-pasteable C++ patterns** checked against specific engine versions |
| **Cloud RAG costs money & leaks code** | Every query ships your game code to an API and bills you per token | **100% local, zero API cost** — code never leaves your machine |
| **Docs lose fidelity in translation** | Translated or re-summarized docs blur UE terminology and drift from actual engine behavior | **Original English corpus** — written in the engine's own language, nothing lost in translation; bilingual topics keep Chinese queries working |

Covers: Gameplay Ability System, character movement, animation, AI navigation,
networking/replication, UMG/Slate, Niagara, Mass Entity, State Trees, PCG,
materials/rendering, module build system, editor tools, and more
(full 31-topic list ships inside the package — see `ue_knowledge/knowledge/`).

## Highlights

- 86 original docs (79 English, 7 bilingual), split into Markdown-aware chunks
  of at most 384 embedding tokens; the release verifier generates and checks
  the exact chunk count instead of keeping a stale number in this README
- Chinese terminology expansion + spoken-Chinese phrase dictionary
  (`zh_dict.json`, every concept grounded in the corpus vocabulary) +
  vector/BM25 RRF fusion. The held-out gate (62 queries, 2 per topic)
  reached **100% Chinese / 100% English Recall@3** on the release machine;
  an independent set of **31 natural spoken-Chinese queries** (no
  glossary-alias wording) scores **90.3% Recall@3** — up from 25.8% before
  the phrase dictionary. The same harness reports the tuning split so
  alias-shaped queries cannot inflate the numbers (see
  `scripts/evaluate_retrieval.py`)
- No API key, no tokens, no server — `pip install` and go
- Embedding + retrieval happen locally; code never leaves your machine
- Every command supports `--json`; patterns for Hermes / Claude Code /
  OpenCode / any custom pipeline; `ue-kb serve` is an MCP server that keeps
  the model loaded for fast agent query loops
- China-friendly: GitHub mirror clone + Tsinghua PyPI + automatic
  hf-mirror fallback — no proxy needed
- ~100MB model, laptop CPU, no GPU; index build ~1 min; cold CLI query
  ~12s (model load), warm in-process query <0.1s

## Quick start

```bash
pip install ue-knowledge-base   # install

ue-kb download-model            # one-time ~100MB model (auto-falls back to hf-mirror)
ue-kb build                     # build the index (~1 min, fully offline from here)
ue-kb query "GAS ability cooldown"
ue-kb query "Niagara particle collision" --json   # JSON output for agents
ue-kb query "GAS cooldown" --profile vector       # 0.4-compatible vector fallback
```

## Query output

```text
$ ue-kb query "GAS ability cooldown"
🔍 UE 知识库检索：GAS ability cooldown

[1] ue-gameplay-abilities/references/ue5.7-api-migration.md › Cooldown GE Tag Workaround (匹配度: 100.0%)
    Since GrantedTags is removed from the GE constructor, cooldown tags must be
    set via DynamicGrantedTags at spec-application time...
[2] ue-gameplay-abilities/SKILL.md › GAS Architecture Overview (匹配度: 99.0%)
    GAS has three pillars that live on UAbilitySystemComponent (ASC): abilities,
    effects, and attributes...
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
| `ue-kb build --append` | Snapshot sync: add new chunks, replace edits and remove stale chunks | `ue-kb build --append` |
| `ue-kb query "..."` | Hybrid search by default; top-k hits with source + heading | `ue-kb query "角色移动 速度衰减" --top-k 5` |
| `ue-kb query --profile vector` | Fall back to 0.4-style vector-only ranking | `ue-kb query "GAS" --profile vector` |
| `ue-kb info` | Manifest, generation, staleness and model-match status | `ue-kb info --json` |
| `ue-kb download-model` | One-time embedding model download | `ue-kb download-model` |
| `ue-kb serve` | MCP stdio server: load the model once, answer queries in process (fast agent loops) | `ue-kb serve` |
| `ue-kb serve` tools | MCP tools: `ue_kb_query` (search), `ue_kb_info` (index status), `ue_kb_topics` (topic list), `ue_kb_glossary` (terminology table) + `resources/list` | via any MCP client |
| `--json` | Machine-readable output (agents) | `ue-kb query "..." --json` |
| `--db <dir>` | Custom chroma dir (default: user data dir, see FAQ) | `ue-kb build --db C:/uekb/.chroma_db` |
| `--source <dir>` | Custom corpus dir (default: bundled corpus) | `ue-kb build --source my-docs/` |
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
- **MCP server** (`ue-kb serve`) — the model loads once per session, so
  query loops skip the ~12s cold start entirely
- Plain **Python snippet** for any custom pipeline

## Extending the corpus

The bundled corpus is part of the installed package, but you can extend it
without touching the package:

1. Add or edit markdown files under any local directory (headings inside code
   fences are ignored by the token-aware chunker);
2. `ue-kb build --append --source my-docs/` — synchronizes additions, edits,
   and deletions through a new atomic index generation;
3. Or index any local `.md` directory: `ue-kb build --source my-docs/`.

> Source contributors: the shipped corpus lives at
> `src/ue_knowledge/knowledge/` and is regenerated by
> `scripts/publish_from_hermes.py` (see `docs/sync-guide.md`) — never edit
> it by hand.

For indexing **Unreal Engine C++ header comments** or **Epic official docs**,
see `scripts/index_engine_source.py` and `scripts/crawl_epic_docs.py`
(they expect local engine/UE paths — extracted index data is generated
locally and **not redistributed**, out of respect for Epic's copyright).

## Roadmap

- **v0.5.0 (released)** — publish-ready: corpus shipped in the wheel, atomic
  index generations + build lock, Windows CI, `raw_score`/`rank` semantics,
  MCP `ue-kb serve`, privacy gates, release checklist
- **v0.6.0 (current)** — retrieval quality: spoken-Chinese phrase dictionary
  (`zh_dict.json`, natural-Chinese Recall@3 25.8% → 90.3%), MCP tool set
  (`ue_kb_info` / `ue_kb_topics` / `ue_kb_glossary` + `resources/list` +
  query cache), resume-friendly Epic docs crawler (markdown corpus output,
  no direct ChromaDB writes)
- **next candidates** — passage-level recall gate (labeled held-out set),
  scheduled eval runs in CI, more bilingual topics, UE 5.7 feature coverage

## FAQ

- **Where does the index live?** — The vector store defaults to your user
  data directory (Windows: `%LOCALAPPDATA%\ue-knowledge-base\chroma_db`;
  macOS: `~/Library/Application Support/ue-knowledge-base/chroma_db`;
  Linux: `$XDG_DATA_HOME/ue-knowledge-base/chroma_db`), so a `pip install`
  never tries to write into `site-packages`. Override with
  `ue-kb build --db <dir>` or the `UE_KB_CHROMA_DIR` env var.
- **Windows: `Cannot open header file` when querying?** — hnswlib cannot open
  its index files under non-ASCII paths (Chinese usernames/folders). The CLI
  rejects such paths up front: use a pure-ASCII index directory, e.g.
  `ue-kb build --db C:/uekb/.chroma_db`. The corpus itself may stay anywhere.
- **Slow model download in mainland China?** — `ue-kb download-model`
  automatically retries via `hf-mirror.com` when the official source fails;
  no proxy or manual `HF_ENDPOINT` needed.
- **`Index ready` but queries say the index is missing?** — the index
  directory was moved/deleted, or it is a pre-0.5 schema. Rebuild with
  `ue-kb build --force`; failed rebuilds leave the old active generation intact
  (`chromadb>=0.5,<1.0` is pinned to avoid
  the 1.x Rust backend that cannot reload its own HNSW index).
- **Telemetry noise on stderr?** — chromadb 0.6.x product telemetry is
  disabled at the settings level (`anonymized_telemetry=False`), so no
  posthog lines are printed regardless of the installed posthog version.

## License

MIT. The knowledge documents are original writing; no engine source code or
verbatim Epic documentation is included.
