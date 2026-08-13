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
