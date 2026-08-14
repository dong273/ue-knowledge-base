# Agent Integration Guide

`ue-kb` was built to be consumed by AI agents. Every command supports
`--json`, output is deterministic, and the index is fully local — no API
keys, no network, no per-query cost.

## The universal pattern

```bash
ue-kb query "<your question>" --top-k 5 --json
```

Returns structured JSON:

```json
[
  {
    "source": "ue-gameplay-abilities/references/gas-input-integration.md",
    "heading": "问题",
    "score": 1.0,
    "raw_score": 0.0328,
    "rank": 1,
    "text": "## 问题  UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时..."
  }
]
```

### Reading the scores

- `score` is **display-relative**: it is normalized so the top hit of the
  current query is always 1.0. Never use it to compare across queries or to
  decide "is there any coverage".
- `raw_score` is the **RRF fusion value**, comparable across queries. Use it
  for confidence and coverage decisions. Calibrated ranges for the current
  pipeline (RRF k=60, 30 vector + 30 BM25 candidates):
  - `raw_score ≥ 0.025` — ranked high in **both** lists; strong grounding.
  - `0.015 ≤ raw_score < 0.025` — strong in one list; usable grounding.
  - `raw_score < 0.012` — single-list tail; weak.
  - **All hits `raw_score < 0.012` → the knowledge base likely has no
    coverage**; answer from general UE knowledge and say so.
- `rank` is the 1-based position in the returned list.

## MCP server (recommended for agent loops)

Each `ue-kb query` spawns a process and loads the ~100MB embedding model
(cold CLI query ≈ 12s on the release machine vs 0.07s warm). For anything
that queries repeatedly, run `ue-kb serve` and let the agent call it as an
MCP tool — the model loads once per session:

```bash
ue-kb serve                 # MCP stdio server; expose as an MCP client tool
```

- Exposes tools: `ue_kb_query(query, top_k?, profile?)` returning the
  same hit structure as `ue-kb query --json` (including `raw_score`);
  `ue_kb_info` (index status / chunk count / model match, call before
  querying to learn whether an index exists); `ue_kb_topics` (topic list);
  `ue_kb_glossary(topic?)` (terminology table). Also implements MCP
  `resources/list` (one resource per topic) and a query cache (repeated
  identical queries skip re-embedding).
- Configure it in Claude Code (`claude mcp add`) / Hermes (`hermes mcp add`)
  / any MCP-capable client; no API key, fully local.
- The server is a plain JSON-RPC-over-stdio process: anything that can spawn
  a subprocess and read stdout can speak the protocol directly.

Agent-side workflow:

1. User asks a UE development question.
2. Agent runs `ue-kb query "<question>" --top-k 5 --json`.
3. Agent uses the top hits (`source` / `heading` / `text`) as grounding
   context, using `raw_score` as the confidence signal (see ranges above).
4. Agent cites `source › heading` in its answer.

Recommendations:

- `--top-k 3–5` is the sweet spot; more adds noise.
- Query in English for best results — the corpus is 81/86 English and the
  default `bge-small-en-v1.5` embedder is English-first. Chinese queries
  still work on bilingual topics; rebuild with `--model BAAI/bge-small-zh-v1.5`
  for Chinese-first retrieval.
- Prefer `--json` over the human format; the human format is for terminals.
- If the index does not exist yet: `ue-kb build` (one-time, ~1 min on CPU).

## Hermes

Drop this into a skill (e.g. `ue-knowledge-rag/SKILL.md`) to give any Hermes
agent a semantic search tool:

```markdown
---
name: ue-knowledge-rag
description: "Semantic search over the UE knowledge base. Use when the user asks UE development questions (GAS, movement, AI, networking, UMG, Niagara, ...)."
---

# UE Knowledge RAG

Query the local UE knowledge base for grounded answers.

## When to use
- Any UE development question: GAS, character movement, AI, replication,
  UMG/Slate, Niagara, State Trees, PCG, materials, build system, editor tools.

## Procedure

1. Run: `ue-kb query "<question>" --top-k 5 --json`
2. If it errors with "索引不存在", run `ue-kb build` first, then retry.
3. Ground the answer in the top hits; cite `source › heading`.
4. If every hit has `raw_score < 0.012`, say the knowledge base has no
   coverage and answer from general UE knowledge.

## Pitfalls
- Index dir must be ASCII (hnswlib): pass `--db C:/uekb/.chroma_db` if the
  default path is under a Chinese username.
- Offline by default: a missing model reports clearly — run
  `ue-kb download-model` once (auto-falls back to hf-mirror).
```

## Claude Code

Add a slash command `.claude/commands/ue-kb.md`:

````markdown
---
description: Semantic search the UE knowledge base
argument-hint: <question>
---

Search the local UE knowledge base for: $ARGUMENTS

Run:
```bash
ue-kb query "$ARGUMENTS" --top-k 5 --json
```
Use the JSON hits as grounding. Cite `source › heading`. If "索引不存在",
run `ue-kb build` and retry. If "Model 未找到", run `ue-kb download-model`.
````

Then in any conversation:

```
/ue-kb GAS 技能冷却如何接入 Enhanced Input
```

## OpenCode

Add to `opencode.json`:

```json
{
  "commands": {
    "ue-kb": {
      "description": "Semantic search the UE knowledge base",
      "args": "<question>",
      "command": "ue-kb query \"$1\" --top-k 5 --json"
    }
  }
}
```

Usage: `/ue-kb 角色移动速度衰减问题`

## Raw scripts / other agents

Any tool that can run a subprocess and read stdout can use `ue-kb`:

```python
import json
import subprocess


def ue_kb_search(question: str, top_k: int = 5) -> list[dict]:
    out = subprocess.run(
        ["ue-kb", "query", question, "--top-k", str(top_k), "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)
```

## Building blocks (all commands)

| Command | Purpose | JSON |
|---|---|---|
| `ue-kb build [--append]` | build / incrementally update the index | summary |
| `ue-kb query <q> --top-k N` | semantic search | hits |
| `ue-kb info` | index stats (count, description) | plain text |
| `ue-kb download-model` | one-time model fetch (mirror fallback) | plain text |

## Troubleshooting (quick)

| Symptom | Fix |
|---|---|
| `索引不存在` | `ue-kb build` first |
| `Model 未找到` | `ue-kb download-model` once |
| `Cannot open header file` / non-ASCII path error | use an ASCII `--db` dir |
| Corrupt index errors (hnsw/segment) | `ue-kb build --force` |
