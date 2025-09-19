from __future__ import annotations

import re
from typing import Iterable, List

from .types import Chunk, Document


LIST_PREFIX_RE = re.compile(r"^(\s*(\d+\.|-\s|\*\s|Step\s*\d+\s*:))\s+", re.IGNORECASE)
SECTION_HEADER_RE = re.compile(r"^\s*(\*\*[^*]+\*\*|[A-Z][A-Za-z ]+:)\s*$")


def _paragraphs(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts


def chunk_document(doc: Document, max_chars: int = 1200) -> List[Chunk]:
    chunks: List[Chunk] = []
    paras = _paragraphs(doc.content)

    buf: List[str] = []
    section = None

    def flush_buf():
        nonlocal buf, section
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        # Split overly long chunks
        if len(text) <= max_chars:
            chunks.append(_make_chunk(doc, text, section))
        else:
            pieces = _split_long(text, max_chars)
            for i, piece in enumerate(pieces, 1):
                chunks.append(_make_chunk(doc, piece, section if i == 1 else f"{section or 'section'} (cont. {i})"))
        buf = []

    for p in paras:
        if SECTION_HEADER_RE.match(p):
            # New section header
            flush_buf()
            section = _clean_section_title(p)
            continue

        if LIST_PREFIX_RE.match(p):
            # Keep sequential list items together until a non-list paragraph
            flush_buf()
            list_block = [p]
            # The paragraph list does not expose lookahead; we rely on list detection within a paragraph, which often contains multiple items
            # If a numbered list spans multiple paras, they'll each match and be flushed separately preserving order.
            chunks.append(_make_chunk(doc, "\n".join(list_block), section))
        else:
            # Aggregate normal paragraphs until size threshold
            if sum(len(x) for x in buf) + len(p) + 2 <= max_chars:
                buf.append(p)
            else:
                flush_buf()
                buf.append(p)

    flush_buf()
    # Attach simple sequential section labels for numbered chunks if none
    for i, c in enumerate(chunks, 1):
        if not c.section:
            c.section = f"part {i}"
    return chunks


def _split_long(text: str, max_chars: int) -> List[str]:
    # Prefer splitting on paragraph boundaries then sentences
    parts = [t.strip() for t in re.split(r"\n\n+", text) if t.strip()]
    res: List[str] = []
    cur = []
    cur_len = 0
    for part in parts:
        if cur_len + len(part) + 2 <= max_chars:
            cur.append(part)
            cur_len += len(part) + 2
        else:
            if cur:
                res.append("\n\n".join(cur))
                cur = []
                cur_len = 0
            if len(part) <= max_chars:
                res.append(part)
            else:
                # split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", part)
                buf = []
                bl = 0
                for s in sentences:
                    if bl + len(s) + 1 <= max_chars:
                        buf.append(s)
                        bl += len(s) + 1
                    else:
                        if buf:
                            res.append(" ".join(buf))
                            buf = []
                            bl = 0
                        if len(s) <= max_chars:
                            res.append(s)
                        else:
                            # hard cut
                            for i in range(0, len(s), max_chars):
                                res.append(s[i:i+max_chars])
                if buf:
                    res.append(" ".join(buf))
    if cur:
        res.append("\n\n".join(cur))
    return res


def _clean_section_title(p: str) -> str:
    p = p.strip()
    if p.startswith("**") and p.endswith("**"):
        p = p.strip("*")
    return p.rstrip(": ")


def _make_chunk(doc: Document, text: str, section: str | None) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.id}:::{abs(hash((doc.id, section or '', text[:64])))}",
        doc_id=doc.id,
        title=doc.title,
        source=doc.source,
        doc_type=doc.type,
        version=doc.version,
        last_updated=doc.last_updated,
        tags=list(doc.tags),
        text=text.strip(),
        section=section,
        extra=dict(doc.extra),
    )

