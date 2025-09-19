from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from .types import Document, parse_date


def load_product_docs(path: Path) -> List[Document]:
    data = json.loads(path.read_text(encoding="utf-8"))
    docs = []
    for d in data.get("product_docs", []):
        docs.append(
            Document(
                id=d.get("id"),
                title=d.get("title", ""),
                type=d.get("type", ""),
                version=d.get("version"),
                last_updated=parse_date(d.get("last_updated")),
                tags=d.get("tags", []) or [],
                content=d.get("content", ""),
                source="doc",
                extra={}
            )
        )
    return docs


def load_support_tickets(path: Path) -> List[Document]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tickets = []
    for t in data.get("support_tickets", []):
        # Map ticket fields into Document schema
        tickets.append(
            Document(
                id=t.get("id"),
                title=t.get("title", ""),
                type=t.get("category", "ticket"),
                version=t.get("user_version"),
                last_updated=parse_date(t.get("resolved_date") or t.get("created_date")),
                tags=t.get("tags", []) or [],
                content=t.get("content", ""),
                source="ticket",
                extra={
                    "status": t.get("status"),
                    "priority": t.get("priority"),
                    "created_date": t.get("created_date"),
                    "resolved_date": t.get("resolved_date"),
                },
            )
        )
    return tickets


def load_all(dataset_dir: Path = Path(".")) -> Tuple[List[Document], List[Document]]:
    product_docs = load_product_docs(dataset_dir / "product_docs.json")
    tickets = load_support_tickets(dataset_dir / "support_tickets.json")
    return product_docs, tickets

