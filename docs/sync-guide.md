# Publishing Guide — keep `src/ue_knowledge/knowledge/` in sync with Hermes skills

`src/ue_knowledge/knowledge/` is a **sanitized public mirror** of the local
Hermes UE skill library. It ships inside the installed package (package
data), so it is part of the published artifact — the single source of truth
is:

```
~/AppData/Local/hermes/skills/ue/<topic>/
```

**Never hand-edit files under `src/ue_knowledge/knowledge/`.** The previous
manual pass corrupted the corpus (broken code fences, `.agents/` sentence
leftovers, eaten multi-line YAML descriptions). Everything must go through
`scripts/publish_from_hermes.py`.

## When to publish

- A local Hermes UE skill was created or updated.
- Topic count / document count changes (README numbers must be updated too).

## Steps

### 1. Regenerate

```bash
python scripts/publish_from_hermes.py
```

Exclusions handled by the script:

- `ue-baihechubu-pipeline` — project-private, never published (D1 decision
  2026-08-12). If it is ever added to the publish set, review content first.
- `ue-project-context` keeps `.agents/` mentions — it is the subject matter.

### 2. Gate checks (must all pass)

```bash
# Privacy: private names, personal paths, agent-prompt leftovers
python scripts/check_privacy.py                                                        # 0 findings
# Broken fences: single-backtick + language tag at line start
grep -rnE '^`(csharp|cpp|python|bash|json|text|py|c|h|sh)$' src/ue_knowledge/knowledge/ | wc -l   # 0
# Orphan single-backtick lines
grep -rn '^`$' src/ue_knowledge/knowledge/ | wc -l                                                 # 0
# Internal project-context read directives
grep -rn '\.agents/' src/ue_knowledge/knowledge/ | grep -v 'ue-project-context' | wc -l            # 0
# Agent persona lines
grep -rn "You are an expert" src/ue_knowledge/knowledge/ | wc -l                                   # 0
# Fence parity with the source skill tree (per file)
grep -c '^```' <knowledge file>  ==  grep -c '^```' <source SKILL.md/reference>
```

### 3. Verify the package gate (must all pass)

After any corpus change, the release gate must stay green (CI runs it):

```bash
python -m build                                   # build wheel + sdist
python scripts/verify_package.py dist/*.whl       # corpus in wheel == source corpus (hashes)
python -m pytest tests/                           # incl. 86-file corpus + generated chunk checks
```

### 4. Update README numbers

`README.md` + `README.zh-CN.md`:

- topic count (31) and document count (86) in the header/table/list
- searchable chunk count only from a real `ue-kb build` run (the count
  depends on the embedding tokenizer, so it must never be guessed)

### 5. Commit & push (behind the Clash 7897 proxy)

```bash
git add scripts/ src/ue_knowledge/knowledge/ README.md README.zh-CN.md
git commit -m "fix(publish): ..."
git push origin main
```

`git config http.proxy` is already set to `http://127.0.0.1:7897`. GitHub
API calls need a `Mozilla/5.0` User-Agent header or they 403.

### 6. Releasing a new package version

Follow `docs/releasing.md`: version bump → tag → build → verify → twine
upload → CI `smoke` job green. The PyPI release must NEVER lag the corpus
fixes (the 0.4.0 incident: fixes committed, never published).

## Local RAG index (not part of the repo)

The ChromaDB index at `~/AppData/Local/hermes/ue-knowledge/chroma_db/` is
built locally, never committed. The current commands are:

```bash
ue-kb build --db <ascii-path>   # or point the local Hermes skill at the CLI
```

## Indexing Epic official docs (local only, never redistributed)

`scripts/crawl_epic_docs.py` crawls selected UE 5.7 Epic documentation pages
into a **local markdown corpus**, then you index it with the standard
pipeline — the extracted text is generated locally and is **not** part of
the published package (Epic copyright):

```bash
# 1. Crawl (resume-friendly: HTML cached under .cache/epic-docs/)
python scripts/crawl_epic_docs.py --out epic-docs/

# 2. Index into a fresh or existing knowledge base (snapshot sync)
ue-kb build --source epic-docs/ --append

# 3. Search (epic-docs hits are marked source: epic-docs/...)
ue-kb query "module dependency graph"
```

Notes:

- Add more pages by appending slugs to `PAGES` in the script.
- Some Epic pages are Angular SPAs with no server-rendered content; the
  crawler skips those and reports them in the summary.
- The crawler never writes into the schema-v2 index directly — everything
  goes through `ue-kb build`, so atomic generation, rollback markers and the
  build lock all keep working.
- A rerun after a partial crawl reuses the cached HTML and only re-emits
  markdown; `--append` then adds/updates/removes chunks by chunk id.
