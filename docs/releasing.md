# Release Checklist

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

## Publish

```bash
git tag v0.5.0                             # match pyproject version
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
   bundled corpus (86 markdown files ≈ 1.2 MB source; expect a wheel well
   above 100 KB — a ~15 KB wheel means the corpus is missing again).
4. Add a GitHub release from the tag with the quality report
   (`quality-report.json` artifact from CI) attached.

## Rollback note

- If a published version is broken, do NOT delete the PyPI file (yanked
  versions are better than missing ones): use the PyPI "yank" feature, then
  publish the fixed version. GitHub releases can be deleted freely.
