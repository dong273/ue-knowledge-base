# Release Checklist

The current formal release remains `0.6.3`. The `0.7.0` worktree is a
release-blocked candidate until the complete 90-document provenance audit and
the UE 5.7 evidence gate pass. Do not tag, push, upload, or publish a 0.7
artifact from a working index with pending provenance.

> Why this exists: 0.4.0 was published to PyPI without the bundled corpus
> (the wheel was ~15 KB and could not build an index), and the fix lived in
> unreleased commits while the repo moved on to 0.5.0. This checklist makes a
> release a single auditable pass instead of an afterthought. The CI `smoke`
> job automates the verification half; the steps below are the parts that
> need the maintainer's credentials.

## Before you start

- [ ] `git status` clean (except `.hermes/`), `git log` shows the version bump
      commit for the release number you are about to tag.
- [ ] `pyproject.toml` `version`, `src/ue_knowledge/__init__.py` `__version__`,
      and the planned Git tag all agree. The repo has no other version strings
      (verified by `grep -rn '"0\.' --include=*.py --include=*.toml --include=*.yml src .github`).
- [ ] `ue-kb download-model` has been run on the release machine (or CI will
      download it during the `quality`/`smoke` jobs).
- [ ] README numbers (topic count, document count) match the corpus:
      `python scripts/verify_package.py` reports the chunk count — update the
      READMEs if the count changed.

## Local gates (must all pass)

```bash
python -m pip install -e . pytest build
python scripts/verify_package.py           # needs dist/ built first:
python -m build                            # wheel + sdist
python scripts/verify_package.py dist/*.whl dist/*.tar.gz
python -m pytest tests/ -v
ue-kb build --force                        # real corpus, real model
ue-kb query "GAS ability cooldown" --top-k 5
ue-kb info --json                          # stale must be false
```

For a v0.7 candidate, also run the fail-closed gate with the sanitized UE
validation manifest:

```bash
python scripts/check_ue57_evidence.py \
  validation/artifacts/ue57/ue57-validation-evidence.json \
  --fixture-registry validation/fixture-registry.json \
  --claim-ledger validation/corpus-audit.json
python scripts/release_gate.py \
  --source src/ue_knowledge/knowledge \
  --evidence-manifest validation/artifacts/ue57/ue57-validation-evidence.json \
  --claim-ledger validation/corpus-audit.json
```

`release_gate.py` must exit 0. A result containing pending entries, missing
`validation_ids`, or evidence errors is an intentional release stop. The
local working build may use `--allow-pending`, but that is not a release
result.

The retrieval and abstention regression datasets are separate release gates:

```bash
python scripts/evaluate_retrieval.py --db <quality-index> --output quality-report.json
python scripts/evaluate_coverage.py --db <quality-index> --output coverage-report.json
python scripts/measure_mcp.py --db <public-index> \
  --baseline tests/data/mcp-baseline-v0.6.3.json \
  --max-regression 0.20 --output mcp-timing.json
```

The coverage report must keep existing bilingual recall, place the Fresh PIE
negative-evidence chapter in the top three, and keep unsupported-query false
positives at or below 10%. The MCP report records server startup, first query,
and hot query separately; use the resident server for agent loops. Sub-
millisecond hot-query timings also use a small absolute jitter tolerance. The
baseline comparison is intended for the same machine; CI records timing but
does not compare GitHub runners with a developer workstation.

## Publish

```bash
git tag v0.7.0                             # only after every v0.7 gate is green
git push origin main --tags

# PyPI (requires an API token; use a token scoped to the project, not a password)
python -m pip install --upgrade build twine
rm -rf dist && python -m build
python scripts/verify_package.py dist/*.whl dist/*.tar.gz
python -m twine upload dist/*.whl dist/*.tar.gz
```

## Post-publish verification (the part 0.4.0 skipped)

1. Wait for the `smoke` job on the release commit to be green (fresh venv,
   install from wheel, real `ue-kb build` + `ue-kb query`).
2. Fresh-machine check in a clean venv:

```bash
python -m venv /tmp/fresh && /tmp/fresh/bin/pip install ue-knowledge-base
/tmp/fresh/bin/ue-kb download-model
/tmp/fresh/bin/ue-kb build
/tmp/fresh/bin/ue-kb query "Niagara particle collision" --top-k 5
```

3. Confirm PyPI shows the new version and a wheel size consistent with the
   bundled corpus (90 markdown files; expect a wheel well
   above 100 KB — a ~15 KB wheel means the corpus is missing again).
4. Add a GitHub release from the tag with the quality report
   (`quality-report.json` artifact from CI) attached.

## Rollback note

- If a published version is broken, do NOT delete the PyPI file (yanked
  versions are better than missing ones): use the PyPI "yank" feature, then
  publish the fixed version. GitHub releases can be deleted freely.
