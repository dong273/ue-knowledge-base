# Contributing

Thanks for considering a contribution to **ue-knowledge-base**!

> **Maintainers:** `src/ue_knowledge/knowledge/` is regenerated from the
> local Hermes skill library by `scripts/publish_from_hermes.py` — see
> [docs/sync-guide.md](docs/sync-guide.md) before touching it.

## Ways to contribute

- **Content**: add or improve UE knowledge documents under
  `src/ue_knowledge/knowledge/`
  (any topic — GAS, animation, AI, networking, UMG, Niagara, PCG, ...).
  Each doc is plain Markdown; keep headings semantic (`##` per section) since
  the index chunks on heading boundaries.
- **Code**: improve the indexing/querying pipeline under `src/ue_knowledge/`.
- **Bugs & ideas**: open an issue with the templates provided.

## Content guidelines

- Write in **Chinese** (the corpus targets Chinese-speaking UE developers),
  but keep code identifiers in English.
- No engine-source verbatim excerpts (Epic copyright) — describe concepts in
  your own words.
- One topic per document; use `##` / `###` headings for sections.

## Development setup

```bash
pip install -e .
ue-kb download-model   # once; set HF_ENDPOINT=https://hf-mirror.com if needed
ue-kb build
ue-kb query "GAS cooldown"
```

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## PR checklist

- [ ] No personal paths or secrets in the diff
- [ ] `pytest tests/` passes
- [ ] If content: heading structure is clean (good chunking)
