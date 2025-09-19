from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class SimpleTfidfEmbedding:
    """
    Lightweight TF-IDF vectorizer + cosine similarity without external deps.
    Provides embedding-like vectors for semantic-ish similarity.
    """

    def __init__(self, max_features: int = 4096):
        self.max_features = max_features
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[int, float] = {}
        self.fitted = False

    def fit(self, texts: Iterable[str]) -> "SimpleTfidfEmbedding":
        df: Counter[str] = Counter()
        docs_tokens: List[List[str]] = []
        for text in texts:
            toks = list(dict.fromkeys(tokenize(text)))  # unique per doc
            docs_tokens.append(toks)
            df.update(toks)
        # Limit vocab to most frequent
        most_common = [w for w, _ in df.most_common(self.max_features)]
        self.vocab = {w: i for i, w in enumerate(most_common)}
        n_docs = max(1, len(docs_tokens))
        self.idf = {self.vocab[w]: math.log((n_docs + 1) / (df[w] + 1)) + 1.0 for w in most_common}
        self.fitted = True
        return self

    def transform(self, texts: Iterable[str]) -> List[List[float]]:
        assert self.fitted, "Call fit() before transform()"
        vecs: List[List[float]] = []
        for text in texts:
            toks = tokenize(text)
            tf = Counter(toks)
            vec = [0.0] * len(self.vocab)
            for w, c in tf.items():
                j = self.vocab.get(w)
                if j is None:
                    continue
                vec[j] = (1.0 + math.log(c)) * self.idf.get(j, 1.0)
            self._l2_normalize(vec)
            vecs.append(vec)
        return vecs

    def transform_one(self, text: str) -> List[float]:
        return self.transform([text])[0]

    @staticmethod
    def _l2_normalize(v: List[float]) -> None:
        s = math.sqrt(sum(x * x for x in v))
        if s > 0:
            for i in range(len(v)):
                v[i] /= s


def cosine(u: List[float], v: List[float]) -> float:
    # Assumes both are same length and l2-normalized (approximately)
    return sum(a * b for a, b in zip(u, v))

