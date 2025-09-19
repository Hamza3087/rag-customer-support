from __future__ import annotations

from typing import List

from .chunker import chunk_document
from .types import Document
from .vecdb import reset_collection


def build_index(docs: List[Document]) -> int:
    """Build (or rebuild) the Chroma index from documents. Returns count of chunks added."""
    coll = reset_collection()

    # Chunk all docs
    all_chunks = []
    for d in docs:
        all_chunks.extend(chunk_document(d))

    # Prepare payloads
    ids = [c.chunk_id for c in all_chunks]
    documents = [c.text for c in all_chunks]
    def _sanitize(meta: dict) -> dict:
        clean = {}
        for k, v in meta.items():
            if v is None:
                clean[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                # Fallback: stringify
                clean[k] = str(v)
        return clean

    metadatas = [
        _sanitize(
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "title": c.title or "",
                "source": c.source or "doc",  # 'doc' or 'ticket'
                "doc_type": c.doc_type or "",
                "version": c.version or "",
                "last_updated": (c.last_updated.isoformat() if c.last_updated else ""),
                "tags": ",".join(c.tags or []),
                "section": c.section or "",
                **{k: ("" if v is None else v) for k, v in (c.extra or {}).items()},
            }
        )
        for c in all_chunks
    ]

    # Add to collection (embeddings computed by collection's embedding function)
    # Chroma recommends batching for large corpora; this is small, so single add is OK.
    coll.add(ids=ids, documents=documents, metadatas=metadatas)

    return len(all_chunks)

