# Windows Non-ASCII Project Paths

Do not assume that every UE build failure under a non-ASCII path is caused by the path.
First preserve the original UBT/UHT/compiler diagnostic and identify the failing tool or
argument boundary.

## Diagnostic method

- Re-run the same target with a clean build and record the first failure.
- Check quoting and encoding at each wrapper-script/process boundary.
- Reproduce from a short ASCII-only worktree only as a diagnostic comparison.
- If the ASCII path succeeds, narrow the failing tool before changing the project layout.

## Evidence boundary

An ASCII-path workaround is not proof that UE 5.7 globally rejects non-ASCII paths, and
a successful source build is not proof that packaging, external SDKs, or deployment use
the same path handling. Report the exact target, tool, path shape, and result separately.
