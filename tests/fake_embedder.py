"""Deterministic fake embedder shared by all integration tests.

Bag-of-tokens embedder: tokens map to fixed dimensions, so texts sharing
tokens get similar vectors (like a real semantic embedder) and
query -> hit assertions are meaningful, not random.

English tokens are whitespace-split words; CJK runs are split per character
so Chinese queries ("技能 冷却") can match Chinese chunks ("技能冷却...")
without a real model — this keeps the full build/persist/reload/query loop
testable offline in CI.
"""

import hashlib
import math

import numpy as np

DIM = 64


def _tokens(text: str) -> list[str]:
    out = []
    for word in text.lower().split():
        if any("\u4e00" <= c <= "\u9fff" for c in word):
            out.extend(word)  # CJK: one token per character
        else:
            out.append(word)
    return out


class FakeEmbedder:
    def __init__(self):
        self.max_seq_length = 512
        self.revision = None

    def get_sentence_embedding_dimension(self) -> int:
        return DIM

    def encode(self, texts, **kwargs):
        out = []
        for t in texts:
            v = [0.0] * DIM
            for token in _tokens(t):
                idx = hashlib.md5(token.encode("utf-8")).digest()[0] % DIM
                v[idx] += 1.0
            norm = math.sqrt(sum(x * x for x in v))
            out.append([x / norm for x in v] if norm > 0 else v)
        return np.asarray(out, dtype=np.float32)
