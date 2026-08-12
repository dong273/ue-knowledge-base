#!/usr/bin/env python3
"""Publish Hermes UE skills -> public knowledge/ corpus (sanitized).

Source of truth: ~/AppData/Local/hermes/skills/ue/<topic>/
Output:         <repo>/knowledge/<topic>/

Why this exists: the previous publish pass was done by hand and corrupted the
corpus (code fences ``` -> `, leftover ".agents/" sentence fragments, and
multi-line YAML descriptions eaten). This script regenerates the ENTIRE
corpus deterministically from the local Hermes skills. Never hand-edit
knowledge/*.md again — always re-run this script.

Sanitization rules (line-based, NO markdown re-parsing — code fences are
left byte-identical):

  Frontmatter (SKILL.md only):
    - `name:`       -> `title:`
    - `description:` kept, quoted value unquoted, wording tweaked:
        "Use this skill when working with X"   -> "Covers X"
        "Use this skill when working on X"     -> "Covers working on X"
        "Use this skill when implementing X"   -> "Covers implementing X"
        "Use this skill when X"                -> "Covers X"
      multi-line `description: >-` blocks are folded to one line (the
      previous pass ate them entirely — bug fix)
    - `metadata.hermes.tags` promoted to top-level `tags: [...]`
    - everything else (version/author/license/platforms/metadata) dropped

  Body (SKILL.md + references/*.md):
    - drop "You are an expert ..." lines
    - drop "Ask the developer ..." lines
    - drop lines referencing `.agents/` (internal project-context reads)
      EXCEPT in topic `ue-project-context`, where `.agents/ue-project-context.md`
      is the subject matter and must be kept
    - code fences untouched; CRLF normalized to LF

Usage:
    python scripts/publish_from_hermes.py            # full regenerate
    python scripts/publish_from_hermes.py --all      # deprecated alias (same)
    python scripts/publish_from_hermes.py --topics ue-knowledge-rag ue-project-context  # selected only
"""

import re
import sys
from pathlib import Path

SKILLS_SRC = Path.home() / "AppData/Local/hermes/skills/ue"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "knowledge"

# Topic where .agents/ mentions are subject matter, not internal reads
AGENTS_IS_CONTENT = {"ue-project-context"}

DROP_LINE_RE = [
    re.compile(r"^You are an? .*expert.*$", re.I),
    re.compile(r"^Ask the developer.*$", re.I),
]

DESC_TWEAKS = [
    ("Use this skill when working with ", "Covers "),
    ("Use this skill when working on ", "Covers working on "),
    ("Use this skill when implementing ", "Covers implementing "),
    ("Use this skill when ", "Covers "),
]


def tweak_description(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    for old, new in DESC_TWEAKS:
        if value.startswith(old):
            return new + value[len(old):]
    return value


def parse_frontmatter(lines: list[str]) -> tuple[dict, list[str]]:
    """Parse frontmatter block -> (fields, remaining body lines)."""
    fields: dict = {"title": None, "description": None, "tags": None}
    if not lines or lines[0].strip() != "---":
        return fields, lines
    body_start = 1
    i = 1
    in_meta = False
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            body_start = i + 1
            break
        stripped = line.strip()
        if stripped == "metadata:":
            in_meta = True
            i += 1
            continue
        if not line.startswith((" ", "\t")):
            in_meta = False
        if in_meta:
            m = re.match(r"^\s+tags:\s*(\[.*\])$", line)
            if m and fields["tags"] is None:
                fields["tags"] = m.group(1)
            i += 1
            continue
        if stripped.startswith("name:"):
            fields["title"] = stripped[len("name:"):].strip()
        elif stripped == "description: >-":
            # fold multi-line block until next top-level key
            block = []
            i += 1
            while i < len(lines) and lines[i].startswith((" ", "\t")):
                block.append(lines[i].strip())
                i += 1
            fields["description"] = " ".join(block)
            continue
        elif stripped.startswith("description:"):
            fields["description"] = stripped[len("description:"):].strip()
        i += 1
    return fields, lines[body_start:]


def sanitize_body(lines: list[str], keep_agents: bool) -> list[str]:
    out = []
    for line in lines:
        if any(p.match(line) for p in DROP_LINE_RE):
            continue
        if not keep_agents and ".agents/" in line:
            continue
        out.append(line)
    return out


def sanitize_skill(text: str, keep_agents: bool = False) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    fields, body = parse_frontmatter(lines)
    out = ["---"]
    if fields["title"]:
        out.append(f"title: {fields['title']}")
    if fields["description"]:
        out.append(f"description: {tweak_description(fields['description'])}")
    if fields["tags"]:
        out.append(f"tags: {fields['tags']}")
    out.append("---")
    out.extend(sanitize_body(body, keep_agents=keep_agents))
    return "\n".join(out).rstrip("\n") + "\n"


def sanitize_reference(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    return "\n".join(sanitize_body(lines, keep_agents=False)).rstrip("\n") + "\n"


def main() -> None:
    topics = None
    if "--topics" in sys.argv:
        topics = set(sys.argv[sys.argv.index("--topics") + 1:])

    stats = {"skills": 0, "refs": 0, "skipped": 0}
    for topic in sorted(p for p in SKILLS_SRC.iterdir() if p.is_dir()):
        if topics and topic.name not in topics:
            continue
        for src in sorted(topic.rglob("*.md")):
            rel = src.relative_to(SKILLS_SRC)
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.name == "SKILL.md":
                dst.write_text(sanitize_skill(src.read_text(encoding="utf-8"),
                                              keep_agents=topic.name in AGENTS_IS_CONTENT),
                               encoding="utf-8", newline="\n")
                stats["skills"] += 1
            else:
                dst.write_text(sanitize_reference(src.read_text(encoding="utf-8")),
                               encoding="utf-8", newline="\n")
                stats["refs"] += 1
    print(f"published {stats['skills']} SKILL.md + {stats['refs']} references "
          f"({stats['skipped']} skipped)")


if __name__ == "__main__":
    main()
