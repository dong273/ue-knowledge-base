"""Validate zh_dict.json: every concept must actually occur in the corpus.

Grounded vocabulary is what makes the expansion useful — a concept that
never appears in the corpus can never help retrieval. Run in CI (privacy /
quality jobs) so ungrounded entries fail the build.
"""

from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path

from ue_knowledge.retrieval import normalize


def load_corpus(root: Path) -> str:
    normalized = []
    for path in sorted(root.rglob("*.md")):
        normalized.append(normalize(path.read_text(encoding="utf-8")))
    return " ".join(normalized)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]) if argv else Path("src/ue_knowledge/knowledge")
    dict_path = files("ue_knowledge").joinpath("zh_dict.json")
    data = json.loads(dict_path.read_text(encoding="utf-8"))
    corpus = load_corpus(root)

    problems: list[str] = []
    seen_phrases: set[str] = set()
    concept_count = 0
    for phrase, concepts in data.items():
        if not isinstance(phrase, str) or not phrase.strip():
            problems.append(f"词条名非法: {phrase!r}")
        elif phrase in seen_phrases:
            problems.append(f"重复词条: {phrase}")
        else:
            seen_phrases.add(phrase)
        if not isinstance(concepts, list) or not concepts:
            problems.append(f"{phrase}: 概念列表为空")
            continue
        for concept in concepts:
            if not isinstance(concept, str) or not concept.strip():
                problems.append(f"{phrase}: 概念 {concept!r} 非法")
                continue
            concept_count += 1
            if normalize(concept) not in corpus:
                problems.append(f"{phrase}: 概念 {concept!r} 未在语料中出现")

    print(f"zh_dict: {len(data)} 词条, {concept_count} 个概念(含跨词条复用)")
    if problems:
        print("校验失败:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("[ok] 所有概念均已由语料词表支撑")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
