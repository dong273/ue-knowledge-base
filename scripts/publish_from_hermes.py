#!/usr/bin/env python3
"""Publish Hermes UE skills -> public package corpus (sanitized).

Source of truth: ~/AppData/Local/hermes/skills/ue/<topic>/
Output:         <repo>/src/ue_knowledge/knowledge/<topic>/
                (package data — the corpus ships inside the wheel/sdist)

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

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SKILLS_SRC = Path.home() / "AppData/Local/hermes/skills/ue"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "src/ue_knowledge/knowledge"

# Topic where .agents/ mentions are subject matter, not internal reads
AGENTS_IS_CONTENT = {"ue-project-context"}

# Topics NEVER published (project-private). D1 decision 2026-08-12:
# ue-baihechubu-pipeline contains internal project pipeline info.
EXCLUDED_TOPICS = {"ue-baihechubu-pipeline"}

DROP_LINE_RE = [
    re.compile(r"^You are an? .*expert.*$", re.I),
    re.compile(r"^Ask the developer.*$", re.I),
    # Agent-prompt leftovers that add nothing to a search corpus (found in
    # several topic SKILL.md files: "Ask which area the user needs...").
    re.compile(r"^Ask which area.*$", re.I),
    re.compile(r"^Ask the user.*$", re.I),
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


def _rendered_files(source_root: Path, topics: set[str] | None = None):
    """Yield ``(relative, sanitized_text)`` without touching the repository."""
    if not source_root.is_dir():
        raise FileNotFoundError(source_root)
    for topic in sorted(path for path in source_root.iterdir() if path.is_dir()):
        if topic.name in EXCLUDED_TOPICS or (topics and topic.name not in topics):
            continue
        for src in sorted(topic.rglob("*.md")):
            rel = src.relative_to(source_root).as_posix()
            if src.name == "SKILL.md":
                rendered = sanitize_skill(
                    src.read_text(encoding="utf-8"),
                    keep_agents=topic.name in AGENTS_IS_CONTENT,
                )
            else:
                rendered = sanitize_reference(src.read_text(encoding="utf-8"))
            yield rel, rendered


def _write_rendered(files, output: Path) -> dict[str, int]:
    stats = {"skills": 0, "refs": 0}
    output.mkdir(parents=True, exist_ok=True)
    for rel, rendered in files:
        dst = output / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rendered, encoding="utf-8", newline="\n")
        stats["skills" if dst.name == "SKILL.md" else "refs"] += 1
    return stats


def _manifest_payload(files: list[tuple[str, str]]) -> dict:
    ordered = sorted(files, key=lambda item: item[0])
    return {
        "schema_version": 1,
        "files": [rel for rel, _ in ordered],
        "sha256": {rel: hashlib.sha256(text.encode("utf-8")).hexdigest() for rel, text in ordered},
    }


def _check(files: list[tuple[str, str]], output: Path, manifest: Path | None) -> int:
    expected = _manifest_payload(files)
    if manifest and manifest.is_file():
        try:
            recorded = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[FAIL] invalid publication manifest: {exc}", file=sys.stderr)
            return 1
        if recorded.get("files") != expected["files"] or recorded.get("sha256") != expected["sha256"]:
            print("[FAIL] Hermes render differs from publication manifest", file=sys.stderr)
            return 1
    actual_files = sorted(path.relative_to(output).as_posix() for path in output.rglob("*.md")) if output.is_dir() else []
    if actual_files != expected["files"]:
        print("[FAIL] Hermes render file set differs from public corpus", file=sys.stderr)
        return 1
    for rel, rendered in files:
        current = output / rel
        if not current.is_file() or current.read_text(encoding="utf-8") != rendered:
            print(f"[FAIL] Hermes render differs: {rel}", file=sys.stderr)
            return 1
    print(f"[ok] Hermes render matches {len(files)} public Markdown files")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publish sanitized Hermes UE skills")
    parser.add_argument("--topics", nargs="*", help="publish only named topics")
    parser.add_argument("--source", type=Path, default=SKILLS_SRC, help="Hermes UE skill root")
    parser.add_argument("--output", type=Path, default=OUT, help="public corpus output root")
    parser.add_argument("--manifest", type=Path, help="publication manifest to write or verify")
    parser.add_argument("--check", action="store_true", help="render in memory and verify output without writing")
    args = parser.parse_args(argv)
    topics = set(args.topics) if args.topics else None
    files = list(_rendered_files(args.source, topics))
    if args.check:
        return _check(files, args.output, args.manifest)
    stats = _write_rendered(files, args.output)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(_manifest_payload(files), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"published {stats['skills']} SKILL.md + {stats['refs']} references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
