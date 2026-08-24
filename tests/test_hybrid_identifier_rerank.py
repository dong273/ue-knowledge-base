"""Regression tests for exact UE identifier grounding in hybrid fusion."""

from ue_knowledge.query import _rerank_exact_identifiers


def test_exact_identifiers_break_close_rrf_collision():
    fused = [
        ("semantic-distractor", (1 / 61) + (1 / 67)),
        ("lexical-target", 1 / 61),
    ]
    hits = {
        "semantic-distractor": {
            "heading": "Common setup",
            "text": "A client can ask its GameMode about the current rules.",
        },
        "lexical-target": {
            "heading": "Authority and presence",
            "text": "GameMode exists only on authority; remote clients read GameState.",
        },
    }

    reranked = _rerank_exact_identifiers(
        fused,
        hits,
        "远程客户端应该读取 GameMode 还是 GameState",
    )

    assert reranked[0][0] == "lexical-target"
    assert reranked[0][1] > reranked[1][1]


def test_lowercase_natural_language_keeps_rrf_order():
    fused = [("first", 0.03), ("second", 0.02)]
    hits = {
        "first": {"heading": "First", "text": "ordinary text"},
        "second": {"heading": "Second", "text": "ordinary text"},
    }

    assert _rerank_exact_identifiers(fused, hits, "ordinary natural language") == fused
