"""Static integrity gates for the manually reviewed golden-query set."""

import json
from pathlib import Path


def test_golden_queries_cover_31_topics_and_124_unique_queries():
    path = Path(__file__).parent / "data" / "golden_queries.json"
    topics = json.loads(path.read_text(encoding="utf-8"))
    queries = [
        {**query, "topic": topic["topic"]}
        for topic in topics
        for query in topic["queries"]
    ]

    assert len(topics) == 31
    assert len(queries) == 124
    assert len({query["text"] for query in queries}) == 124
    for topic in topics:
        assert {
            (query["language"], query["split"])
            for query in topic["queries"]
        } == {
            ("en", "tune"), ("en", "heldout"),
            ("zh", "tune"), ("zh", "heldout"),
        }


def test_passage_expected_covers_heldout_queries_with_specific_sections():
    """Passage labels: one per held-out query, all pointing at real sections
    (no "前言" fallbacks) inside the query's own topic."""
    path = Path(__file__).parent / "data" / "passage_expected.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    assert len(entries) == 62

    golden = Path(__file__).parent / "data" / "golden_queries.json"
    topics = json.loads(golden.read_text(encoding="utf-8"))
    heldout_texts = {
        query["text"]
        for topic in topics
        for query in topic["queries"]
        if query["split"] == "heldout"
    }
    assert {entry["query"] for entry in entries} == heldout_texts

    for entry in entries:
        assert entry["expected"], entry["query"]
        expected = entry["expected"][0]
        assert expected["heading"].strip() != "前言", entry["query"]
        assert expected["source"].replace("\\", "/").startswith(entry["topic"] + "/")
        assert expected["heading"].strip(), entry["query"]
