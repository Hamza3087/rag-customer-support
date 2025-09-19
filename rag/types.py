from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        # Fallbacks for common formats
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None


@dataclass
class Document:
    id: str
    title: str
    type: str
    version: Optional[str]
    last_updated: Optional[datetime]
    tags: List[str] = field(default_factory=list)
    content: str = ""
    source: str = "doc"  # 'doc' or 'ticket'
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source: str  # 'doc' or 'ticket'
    doc_type: str
    version: Optional[str]
    last_updated: Optional[datetime]
    tags: List[str]
    text: str
    section: Optional[str] = None
    score: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def citation(self) -> str:
        parts = [self.title, f"({self.doc_id})"]
        if self.section:
            parts.append(f"section: {self.section}")
        if self.version:
            parts.append(f"version: {self.version}")
        return " | ".join(parts)

