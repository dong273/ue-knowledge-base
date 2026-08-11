# UE Knowledge Base

Offline semantic search over Unreal Engine development knowledge — a curated
**Chinese-language knowledge corpus** (30 topics: GAS, animation, AI,
networking, UMG, Niagara, PCG, ...) plus a local RAG pipeline that indexes it
with `BAAI/bge-small-zh-v1.5` embeddings into ChromaDB.

**Zero API cost. Fully offline after a one-time model download.** Built for
Chinese-speaking UE developers, and ready to plug into any AI agent, IDE, or
CLI workflow.

```
knowledge/  (30 topics, ~84 markdown docs)
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
#    In China:  export HF_ENDPOINT=https://hf-mirror.com  then retry

# 3. Build the index
ue-kb build

# 4. Search
ue-kb query "GAS ability cooldown" --top-k 5
ue-kb query "角色移动 速度衰减" --json   # machine-readable for agents
```

### Example

```text
$ ue-kb query "GAS cooldown"
🔍 UE 知识库检索：GAS cooldown

[1] ue-gameplay-abilities/SKILL.md › GameplayEffect 冷却配置 (匹配度: 86.3%)
    Cooldown tags 通过 GameplayTag 管理冷却状态：在 GameplayEffect 中设置
    CooldownGameplayEffectClass ... 
[2] ue-gameplay-abilities/references/gas-input-integration.md › 冷却与输入 (匹配度: 82.1%)
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
