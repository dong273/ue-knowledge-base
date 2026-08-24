from scripts.evaluate_retrieval import failed_passages


def test_failed_passages_reports_passage_misses_even_when_topic_matches():
    missed = {
        "text": "query",
        "expected": [{"source": "topic/SKILL.md", "heading": "Target"}],
        "recall_at_3": True,
        "passage_recall_at_3": False,
    }
    matched = {
        "text": "other",
        "expected": [{"source": "topic/SKILL.md", "heading": "Other"}],
        "recall_at_3": True,
        "passage_recall_at_3": True,
    }

    assert failed_passages([missed, matched]) == [missed]
