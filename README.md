# UE Knowledge Base

[![PyPI version](https://img.shields.io/pypi/v/ue-knowledge-base.svg)](https://pypi.org/project/ue-knowledge-base/)
[![CI](https://github.com/dong273/ue-knowledge-base/actions/workflows/ci.yml/badge.svg)](https://github.com/dong273/ue-knowledge-base/actions)

Offline semantic search over Unreal Engine development knowledge — a curated
**Chinese-language knowledge corpus** (29 topics: GAS, animation, AI,
networking, UMG, Niagara, PCG, ...) plus a local RAG pipeline that indexes it
with `BAAI/bge-small-zh-v1.5` embeddings into ChromaDB.

**Zero API cost. Fully offline after a one-time model download.** Built for
Chinese-speaking UE developers, and ready to plug into any AI agent, IDE, or
CLI workflow.

```
knowledge/  (29 topics, ~84 markdown docs)
    │  ue-kb build          chunk + embed (BGE small, local)
    ▼
.chroma_db/  (vector index)
    │  ue-kb query "GAS cooldown"
    ▼
top-k semantic hits with source + heading
```

## Features

- 📚 **Curated corpus**: hand-written UE development docs in Chinese, covering
  Gameplay Ability System, character movement, animation, physics/collision,
  AI navigation, networking/replication, UMG/Slate, Niagara, Mass Entity,
  State Trees, PCG/procedural generation, materials/rendering, module build
  system, editor tools, and more.
- 🧠 **Local semantic search**: `BAAI/bge-small-zh-v1.5` (multilingual, ~100MB)
  + ChromaDB — no cloud APIs, no cost, works on a laptop CPU.
- 🖥️ **Simple CLI** (`ue-kb`): `build`, `query`, `info`, `download-model`,
  plus `--json` output for agent integration.
- 🔌 **Extensible**: index any extra UE docs with `--source`, or add engine
  source-indexing scripts under `scripts/`.

## Quick start

```bash
# 1. Install
pip install -e .                 # or: pip install ue-knowledge-base

# 2. Download the embedding model once (~100MB)
ue-kb download-model
#    No manual setup needed in China — falls back to hf-mirror automatically

# 3. Build the index
ue-kb build

# 4. Search
ue-kb query "GAS ability cooldown" --top-k 5
ue-kb query "角色移动 速度衰减" --json   # machine-readable for agents
```

### Install in mainland China without a proxy

GitHub / PyPI / HuggingFace are often slow or blocked from mainland China.
This path works **with zero proxy setup**:

```bash
# 1. Get the code (GitHub mirrors, pick either)
git clone --depth 1 https://gh-proxy.com/https://github.com/dong273/ue-knowledge-base.git
#   git clone --depth 1 https://ghfast.top/https://github.com/dong273/ue-knowledge-base.git

# 2. Install dependencies (Tsinghua PyPI mirror)
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. Download the model (mirror fallback is automatic)
ue-kb download-model
#    Falls back to hf-mirror.com automatically if the official source fails;
#    if it still fails, force it manually:
#    export HF_ENDPOINT=https://hf-mirror.com && ue-kb download-model

# 4. Build the index (fully local; offline from here on)
ue-kb build

# 5. Search
ue-kb query "GAS ability cooldown"
```

> Tip: `download-model` **automatically retries via the hf-mirror.com mirror**
> when the official HuggingFace source fails — no manual `HF_ENDPOINT` needed.

### Example

```text
$ ue-kb query "GAS 技能冷却"
🔍 UE 知识库检索：GAS 技能冷却

[1] ue-gameplay-abilities/references/gas-input-integration.md › 问题 (匹配度: 21.1%)
    UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时，容易陷入
    两个极端：- **全 GAS** → 所有输入走 GAS，但 WASD 轴输入不适合 GAS 的事件
    模型，且 CommitAbility 的 GC 延迟影响跳跃手感 ...
[2] ue-gameplay-abilities/references/gas-input-integration.md › Jump — GAS 即时技能 (匹配度: 14.2%)
    ...
```

## Python API

```python
from ue_knowledge.query import query

for hit in query("GAS cooldown", top_k=5):
    print(hit["source"], hit["heading"], hit["score"])
```

## Extending the corpus

1. Add a markdown file under `knowledge/<topic>/` (use `##`/`###` headings —
   the indexer chunks on heading boundaries).
2. `ue-kb build --force` to rebuild.

For indexing **Unreal Engine C++ header comments** or **Epic official docs**,
see `scripts/index_engine_source.py` and `scripts/crawl_epic_docs.py`
(they expect local engine/UE paths — the extracted index data is generated
locally and is not redistributed, out of respect for Epic's copyright).

## License

MIT. The knowledge documents are original writing; no engine source code or
verbatim Epic documentation is included.
