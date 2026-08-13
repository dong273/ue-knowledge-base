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

> **How content edits are kept (important):** the corpus is a sanitized
> mirror of the maintainer's private Hermes skill library, and the publish
> script regenerates it wholesale. A content PR to `knowledge/` is welcome,
> but it will be overwritten by the next publish unless the change is also
> made in the source skill tree. Two options:
>
> 1. **Preferred for small fixes** (typos, wording, privacy fixes): PR the
>    corpus file directly, and open an issue referencing the PR so the
>    maintainer mirrors the fix into the Hermes source before the next
>    publish.
> 2. **For new topics/sections**: propose the content in an issue first, or
>    write it under `knowledge/` and say so in the PR — the maintainer will
>    fold it into the source tree and regenerate.

## Content guidelines

- **Language**: the corpus is English-first (79/86 docs), matching the
  default `bge-small-en-v1.5` embedder. New docs should be **English**;
  bilingual topics may add Chinese phrasing but keep code identifiers in
  English. Chinese queries are supported via the glossary, not via
  Chinese-only docs.
- No engine-source verbatim excerpts (Epic copyright) — describe concepts in
  your own words.
- One topic per document; use `##` / `###` headings for sections.
- **No personal paths, private project names, or machine-specific examples**
  (CI runs `scripts/check_privacy.py` on every PR). Use placeholders like
  `<ENGINE_ROOT>/` instead of real drive paths.

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
python scripts/check_privacy.py   # corpus must stay clean
```

## PR checklist

- [ ] No personal paths or secrets in the diff
- [ ] `pytest tests/` passes
- [ ] `python scripts/check_privacy.py` passes
- [ ] If content: heading structure is clean (good chunking)
