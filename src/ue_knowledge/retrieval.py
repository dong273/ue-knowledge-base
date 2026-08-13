"""Query normalization, UE terminology expansion, BM25 and RRF fusion."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

_WORD_RE = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]", re.IGNORECASE)
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", text)
    value = _CAMEL_RE.sub(" ", value)
    value = value.replace("::", " ").replace("_", " ").replace("/", " ")
    return " ".join(value.lower().split())


def terms(text: str) -> list[str]:
    return _WORD_RE.findall(normalize(text))


@lru_cache(maxsize=1)
def glossary() -> tuple[dict, ...]:
    path = files("ue_knowledge").joinpath("glossary.json")
    return tuple(json.loads(path.read_text(encoding="utf-8")))


def expand_query(text: str) -> str:
    """Longest-match Chinese aliases and add canonical UE terminology."""
    normalized = normalize(text)
    additions: list[str] = []
    occupied: list[tuple[int, int]] = []
    aliases: list[tuple[str, dict]] = []
    for entry in glossary():
        for alias in entry.get("aliases", []):
            aliases.append((normalize(alias), entry))
    aliases.sort(key=lambda item: len(item[0]), reverse=True)

    for alias, entry in aliases:
        start = 0
        while alias and (found := normalized.find(alias, start)) >= 0:
            interval = (found, found + len(alias))
            start = interval[1]
            if any(not (interval[1] <= left or interval[0] >= right) for left, right in occupied):
                continue
            occupied.append(interval)
            additions.extend([entry["canonical"], *entry.get("identifiers", [])])
            break
    return " ".join([normalized, *additions]).strip()


def _topic(source: str) -> str:
    topic = source.replace("\\", "/").split("/", 1)[0]
    entry = next((item for item in glossary() if item.get("topic") == topic), None)
    if entry is None:
        return topic.removeprefix("ue-")
    return " ".join(
        [topic.removeprefix("ue-"), entry["canonical"], *entry.get("aliases", []), *entry.get("identifiers", [])]
    )


def build_bm25(documents: list[dict], destination: Path) -> dict:
    """Persist a compact weighted-field BM25 index."""
    postings: dict[str, list[list[float]]] = defaultdict(list)
    records: list[dict[str, str]] = []
    lengths: list[float] = []
    for index, document in enumerate(documents):
        weighted: Counter[str] = Counter()
        weighted.update({term: count * 3 for term, count in Counter(terms(document["heading"])).items()})
        weighted.update({term: count * 2 for term, count in Counter(terms(_topic(document["source"]))).items()})
        weighted.update(Counter(terms(document["text"])))
        length = float(sum(weighted.values())) or 1.0
        lengths.append(length)
        records.append(
            {"id": document["id"], "source": document["source"], "heading": document["heading"]}
        )
        for term, frequency in weighted.items():
            postings[term].append([index, float(frequency)])
    artifact = {
        "version": 1,
        "field_weights": {"heading": 3, "topic": 2, "body": 1},
        "documents": records,
        "average_length": sum(lengths) / len(lengths) if lengths else 0.0,
        "lengths": lengths,
        "postings": postings,
    }
    destination.write_text(
        json.dumps(artifact, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return artifact


@lru_cache(maxsize=4)
def _load_bm25(path: str, modified_ns: int) -> dict:
    del modified_ns
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bm25_search(path: Path, query_text: str, limit: int = 30) -> list[tuple[str, float]]:
    stat = path.stat()
    index = _load_bm25(str(path), stat.st_mtime_ns)
    query_terms = Counter(terms(query_text))
    document_count = len(index["documents"])
    average_length = index["average_length"] or 1.0
    scores: dict[int, float] = defaultdict(float)
    k1, b = 1.5, 0.75
    for term, query_frequency in query_terms.items():
        posting = index["postings"].get(term, [])
        document_frequency = len(posting)
        if not document_frequency:
            continue
        inverse_frequency = math.log(
            1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        for document_index, frequency in posting:
            document_index = int(document_index)
            length = index["lengths"][document_index]
            denominator = frequency + k1 * (1.0 - b + b * length / average_length)
            scores[document_index] += query_frequency * inverse_frequency * frequency * (k1 + 1.0) / denominator
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [(index["documents"][position]["id"], score) for position, score in ranked]


def rrf(vector_ids: list[str], lexical_ids: list[str], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in (vector_ids, lexical_ids):
        for rank, document_id in enumerate(ranking, 1):
            scores[document_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
