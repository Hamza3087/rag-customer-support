from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from .classifier import classify_query
from .embeddings import tokenize
from .keyword import keyword_overlap_score
from .types import Chunk, Document
from .vecdb import get_collection
from .chunker import chunk_document


DOC_TYPE_BOOST = {
    "doc": 1.10,  # official docs
    "ticket_resolved": 1.05,
    "ticket_pending": 0.90,
}


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float


class HybridRetriever:
    """
    Hybrid retriever that queries ChromaDB for semantic similarity and combines
    results with BM25 keyword retrieval and custom re-ranking.
    """

    def __init__(self):
        self.collection = get_collection()
        # In-memory structures for keyword retrieval and metadata reconstruction
        self.chunks: List[Chunk] = []
        self._bm25: Optional[BM25Okapi] = None
        self._chunk_by_id: Dict[str, Chunk] = {}
        self.index_built = False

    def build_index(self, docs: List[Document]):
        # Also build in-memory chunk list for BM25 and citations
        all_chunks: List[Chunk] = []
        for d in docs:
            all_chunks.extend(chunk_document(d))
        self.chunks = all_chunks
        self._chunk_by_id = {c.chunk_id: c for c in self.chunks}
        # Build BM25 corpus
        tokenized_corpus = [tokenize(c.text) for c in self.chunks]
        self._bm25 = BM25Okapi(tokenized_corpus)
        self.index_built = True

    def _semantic_candidates(self, query: str, top_k: int, version: Optional[str]) -> List[Tuple[str, float]]:
        # If version present, get version-filtered first with higher n, else general
        results: List[Tuple[str, float]] = []
        n_big = max(4 * top_k, 32)
        if version:
            q1 = self.collection.query(
                query_texts=[query], n_results=n_big,
                where={"version": version}
            )
            results.extend(self._to_scores(q1))
        q2 = self.collection.query(query_texts=[query], n_results=n_big)
        results.extend(self._to_scores(q2))
        # Deduplicate keeping max score
        best: Dict[str, float] = {}
        for cid, sc in results:
            best[cid] = max(sc, best.get(cid, -1e9))
        # Sort by score desc
        return sorted(best.items(), key=lambda x: x[1], reverse=True)[: n_big]

    @staticmethod
    def _to_scores(qres) -> List[Tuple[str, float]]:
        ids = qres.get("ids", [[]])[0]
        dists = qres.get("distances", [[]])[0]
        # Convert distance to similarity (assuming cosine distance if provided)
        scores = []
        for cid, dist in zip(ids, dists):
            try:
                # Chroma returns distance; higher similarity -> lower distance
                sim = 1.0 - float(dist)
            except Exception:
                sim = 0.0
            scores.append((cid, sim))
        return scores

    def retrieve(self, query: str, top_k: int = 8) -> List[RetrievalResult]:
        assert self.index_built, "Call build_index() first"
        qv = self._extract_version(query)

        # Semantic candidates from Chroma
        semantic = self._semantic_candidates(query, top_k, qv)

        # Keyword candidates via BM25
        kw_scores_map: Dict[str, float] = {}
        if self._bm25 is not None:
            kw_scores = self._bm25.get_scores(tokenize(query))
            # Take top N keyword matches
            top_kw = sorted(range(len(self.chunks)), key=lambda i: kw_scores[i], reverse=True)[
                : max(4 * top_k, 32)
            ]
            for i in top_kw:
                kw_scores_map[self.chunks[i].chunk_id] = float(kw_scores[i])

        # Union candidate ids
        candidate_ids = {cid for cid, _ in semantic}
        candidate_ids.update(kw_scores_map.keys())

        # Combine with scoring heuristics
        results: List[RetrievalResult] = []
        sem_map = {cid: sc for cid, sc in semantic}
        for cid in candidate_ids:
            c = self._chunk_by_id.get(cid)
            if not c:
                # If chunk isn't in memory (shouldn't happen), skip
                continue
            sem = sem_map.get(cid, 0.0)
            kw = kw_scores_map.get(cid, 0.0)
            combined = self._combined_score(c, sem, kw, query)
            results.append(RetrievalResult(chunk=c, score=combined))

        # Sort and return top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _combined_score(self, c: Chunk, sem: float, kw: float, query: str) -> float:
        # Base combination with scale alignment for BM25 (which can be large)
        kw_norm = kw / (kw + 10.0) if kw > 0 else 0.0
        score = 0.65 * sem + 0.25 * kw_norm

        # Add lightweight keyword overlap (phrases/synonyms) for candidates
        kw_overlap = keyword_overlap_score(query, c.text)
        score += 0.10 * min(1.0, kw_overlap)

        # Doc type/status boost
        qtype = classify_query(query)
        if c.source == "doc":
            mult = DOC_TYPE_BOOST["doc"]
            # For troubleshooting/performance, docs are still useful but tickets may be more practical
            if qtype in ("developer", "security", "feature_usage", "product_setup", "comparison", "cancellation"):
                mult *= 1.08
            score *= mult
        else:  # ticket
            status = (c.extra.get("status") or "").lower()
            mult = DOC_TYPE_BOOST["ticket_resolved"] if status == "resolved" else DOC_TYPE_BOOST["ticket_pending"]
            if qtype in ("troubleshooting", "performance", "known_issue", "sharing", "technical_issue"):
                mult *= 1.08
            score *= mult

        # Prefer domain-specific doc types when matched
        dt = (c.doc_type or "").lower()
        if qtype == "developer" and "developer" in dt:
            score *= 1.10
        if qtype == "security" and "security" in dt:
            score *= 1.10
        if qtype == "feature_usage" and any(k in dt for k in ("advanced", "user_guide", "mobile")):
            score *= 1.05

        # Recency boost (up to +10%)
        score *= (1.0 + 0.10 * self._recency_factor(c.last_updated))

        # Version awareness: prefer exact matches; otherwise slight penalty
        qv = self._extract_version(query)
        if qv and c.version:
            score *= 1.15 if qv == c.version else 0.92

        return score

    @staticmethod
    def _recency_factor(dt: Optional[datetime]) -> float:
        if not dt:
            return 0.0
        delta = datetime.utcnow() - dt
        days = max(0.0, min(365.0, delta.days))
        return max(0.0, 1.0 - days / 365.0)

    @staticmethod
    def _extract_version(text: str) -> Optional[str]:
        import re
        m = re.search(r"v\d+\.\d+", text.lower())
        return m.group(0) if m else None

