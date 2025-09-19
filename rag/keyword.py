from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple

from .embeddings import tokenize
from .types import Chunk


SYNONYMS = {
    "login": ["sign-in", "sign in", "log in", "signin"],
    "sync": ["synchronization", "synchronise", "synchronize"],
    "folder": ["directory"],
    "2fa": ["two-factor", "two factor", "multi-factor", "mfa"],
}

NEGATIONS = {"not", "no", "isn't", "cannot", "can't", "won't", "don't", "doesn't"}


def expand_query_terms(query: str) -> List[str]:
    tokens = tokenize(query)
    expanded = set(tokens)
    for t in list(tokens):
        for k, syns in SYNONYMS.items():
            if t == k or t in syns:
                expanded.add(k)
                expanded.update(syns)
    return list(expanded)


def keyword_overlap_score(query: str, text: str) -> float:
    q_terms = expand_query_terms(query)
    q_set = set(q_terms)
    t_set = set(tokenize(text))
    if not q_set or not t_set:
        return 0.0
    inter = q_set & t_set
    # Boost for multi-word phrase appearances
    phrase_boost = 0.0
    for q in ("sign in", "system tray", "version history", "rate limits"):
        if q in text.lower():
            phrase_boost += 0.2
    # Negation handling: if query includes negation, keep score but don't penalize
    return (len(inter) / (len(q_set) ** 0.5)) + phrase_boost


def batch_keyword_scores(query: str, chunks: List[Chunk]) -> List[float]:
    return [keyword_overlap_score(query, c.text) for c in chunks]

