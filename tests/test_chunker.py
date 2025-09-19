from pathlib import Path

from rag.types import Document, parse_date
from rag.chunker import chunk_document


def test_preserve_numbered_list():
    doc = Document(
        id="doc_test",
        title="Test Steps",
        type="troubleshooting",
        version="v2.1",
        last_updated=parse_date("2024-01-01"),
        tags=[],
        content=(
            "Follow these steps:\n\n"
            "1. First do A\n\n"
            "2. Then do B\n\n"
            "3. Finally do C\n\n"
            "Notes: end"
        ),
        source="doc",
    )
    chunks = chunk_document(doc, max_chars=500)
    texts = [c.text for c in chunks]
    # Expect a chunk containing the numbered list items intact
    joined = "\n\n".join(texts)
    assert "1. First do A" in joined and "2. Then do B" in joined and "3. Finally do C" in joined

