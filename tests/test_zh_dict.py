"""zh_dict spoken-Chinese expansion behavior and dataset integrity."""

import json
import sys
from importlib.resources import files
from pathlib import Path

from ue_knowledge.retrieval import expand_query, zh_dict

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import check_zh_dict  # noqa: E402


def test_zh_dict_dataset_is_sane():
    data = dict(zh_dict())
    assert len(data) >= 80  # spoken phrases from the natural-Zh failure set
    for phrase, concepts in data.items():
        assert isinstance(phrase, str) and phrase.strip()
        assert isinstance(concepts, tuple) and concepts
        for concept in concepts:
            assert isinstance(concept, str) and concept.strip()


def test_expand_query_adds_spoken_concepts():
    expanded = expand_query("角色从斜坡上滑下去的时候速度要怎么控制")
    for concept in ("slope", "walkable", "velocity", "movement"):
        assert concept in expanded


def test_expand_query_caps_at_12_terms():
    # A query hitting many phrases must not dilute the embedding.
    expanded = expand_query(
        "技能放一半被打断了，这个技能的冷却时间怎么算，玩家死了重新生成"
    )
    normalized_tail = expanded.split()
    assert len(normalized_tail) <= 40  # 12 expansion terms + query words


def test_expand_query_english_unchanged():
    # expand_query normalizes (lowercase) but must not add concepts.
    assert expand_query("GAS ability cooldown") == "gas ability cooldown"


def test_overlapping_phrases_match_longest():
    # "卡顿" must win over the shorter "卡" at the same position.
    expanded = expand_query("游戏玩着玩着开始卡顿，怎么定位问题")
    assert "hitch" in expanded


def test_check_zh_dict_script_passes():
    corpus = REPO_ROOT / "src" / "ue_knowledge" / "knowledge"
    assert check_zh_dict.main([str(corpus)]) == 0
