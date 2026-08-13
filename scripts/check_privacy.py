#!/usr/bin/env python3
"""Scan the public corpus for privacy leaks and agent-prompt leftovers.

The corpus ships inside the published wheel, so anything personal in
knowledge/*.md reaches every user. This script is a hard CI gate:

  - private project names (add yours to PRIVATE_NAMES — the script is
    designed to fail loudly when the publish pipeline regenerates a topic
    that reintroduces them);
  - real user-profile / drive-letter paths (e.g. C:\\Users\\<name>, /home/...,
    E:/...);
  - the author's tooling paths (~/AppData/Local/hermes, hermes_tools);
  - agent-prompt leftovers ("Ask which area...", "You are an expert...");
  - internal project-context reads (.agents/), except in ue-project-context
    where the file is the subject matter.

Exit code 0 = clean, 1 = findings. Dependency-free (stdlib only).

Usage:
    python scripts/check_privacy.py [corpus-dir]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "src/ue_knowledge/knowledge"

# Private names that must never appear in the public corpus. Add new project
# names here BEFORE they can leak (this file is itself public, so use a
# non-secret placeholder only).
PRIVATE_NAMES = ("baihechubu", "百合初部")

# Topics where .agents/ mentions are subject matter, not internal reads.
AGENTS_IS_CONTENT = {"ue-project-context"}

# (label, regex) — matched per line; findings are reported with the line.
# Lines that only contain DOCUMENTED GENERIC examples are allowed to pass:
# "C:/uekb/.chroma_db" is the README's canonical ASCII-path example, and
# "~/Library/Application Support/..." is the documented macOS data dir.
GENERIC_EXAMPLES = ("C:/uekb", "~/Library/Application Support")

PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "private project name",
        re.compile("|".join(re.escape(name) for name in PRIVATE_NAMES), re.IGNORECASE),
    ),
    ("windows user profile path", re.compile(r"[A-Za-z]:[\\/]Users[\\/]")),
    ("drive-letter absolute path", re.compile(r"\b[A-Za-z]:[\\/]")),
    ("unix absolute path", re.compile(r"/(?:home|Users)/[^/]+")),
    (
        "author tooling path",
        re.compile(r"AppData[\\/]Local[\\/]hermes|hermes_tools|ue-rag-env"),
    ),
    ("agent persona line", re.compile(r"^\s*You are an? .*expert.*$", re.IGNORECASE)),
    ("agent prompt line", re.compile(r"^\s*Ask (?:which|the) .*$", re.IGNORECASE)),
    ("internal .agents read", re.compile(r"\.agents/")),
]


def scan(directory: Path) -> list[dict]:
    findings: list[dict] = []
    for path in sorted(directory.rglob("*.md")):
        relative = path.relative_to(directory).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            findings.append({"file": relative, "line": 0, "label": "unreadable", "text": str(exc)})
            continue
        for number, line in enumerate(lines, 1):
            if ".agents/" in line and relative.startswith("ue-project-context/"):
                continue
            if any(example in line for example in GENERIC_EXAMPLES):
                continue
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {"file": relative, "line": number, "label": label, "text": line.strip()[:200]}
                    )
    return findings


def main(argv=None) -> int:
    corpus = Path(argv[1]) if argv and len(argv) > 1 else CORPUS
    findings = scan(corpus)
    if not findings:
        print(f"privacy scan clean: {corpus}")
        return 0
    print(f"privacy scan found {len(findings)} issue(s) in {corpus}:")
    for item in findings:
        print(
            f"  {item['file']}:{item['line']} [{item['label']}] {item['text']}"
        )
    print(
        "\nFix the source of truth (Hermes skills), regenerate via "
        "scripts/publish_from_hermes.py, and re-run this scan."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
