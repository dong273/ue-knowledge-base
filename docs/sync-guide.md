# Publishing Guide — keep `knowledge/` in sync with Hermes skills

`knowledge/` is a **sanitized public mirror** of the local Hermes UE skill
library. The single source of truth is:

```
~/AppData/Local/hermes/skills/ue/<topic>/
```

**Never hand-edit files under `knowledge/`.** The previous manual pass
corrupted the corpus (broken code fences, `.agents/` sentence leftovers,
eaten multi-line YAML descriptions). Everything must go through
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
# Broken fences: single-backtick + language tag at line start
grep -rnE '^`(csharp|cpp|python|bash|json|text|py|c|h|sh)$' knowledge/ | wc -l   # 0
# Orphan single-backtick lines
grep -rn '^`$' knowledge/ | wc -l                                                 # 0
# Internal project-context read directives
grep -rn '\.agents/' knowledge/ | grep -v 'ue-project-context' | wc -l            # 0
# Agent persona lines
grep -rn "You are an expert" knowledge/ | wc -l                                   # 0
# Fence parity with the source skill tree (per file)
grep -c '^```' <knowledge file>  ==  grep -c '^```' <source SKILL.md/reference>
```

### 3. Update README numbers

`README.md` + `README.zh-CN.md`:

- topic count (31) and document count (86) in the header/table/list
- searchable chunk count only after a local `build_ue_knowledge.py` run —
  never guess it

### 4. Commit & push (behind the Clash 7897 proxy)

```bash
git add scripts/ knowledge/ README.md README.zh-CN.md
git commit -m "fix(publish): ..."
git push origin main
```

`git config http.proxy` is already set to `http://127.0.0.1:7897`. GitHub
API calls need a `Mozilla/5.0` User-Agent header or they 403.

## Local RAG index (not part of the repo)

The ChromaDB index at `~/AppData/Local/hermes/ue-knowledge/chroma_db/` is
built locally, never committed:

```bash
cd ~/ue-rag-env && PYTHONPATH="" TRANSFORMERS_OFFLINE=1 ./Scripts/python build_ue_knowledge.py
```
