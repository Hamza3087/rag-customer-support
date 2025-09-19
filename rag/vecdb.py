from __future__ import annotations

from typing import Any, Dict, List, Optional

import chromadb
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import (
    OpenAIEmbeddingFunction,
    SentenceTransformerEmbeddingFunction,
)

from .config import settings


def _embedding_function():
    backend = settings.embedding_backend.lower()
    if backend == "openai":
        return OpenAIEmbeddingFunction(model_name=settings.openai_model_name)
    # default to sentence-transformers
    return SentenceTransformerEmbeddingFunction(model_name=settings.sentence_model_name)


def get_client() -> PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection(name: Optional[str] = None):
    client = get_client()
    ef = _embedding_function()
    return client.get_or_create_collection(
        name or settings.collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(name: Optional[str] = None):
    client = get_client()
    cname = name or settings.collection_name
    try:
        client.delete_collection(cname)
    except Exception:
        pass
    return get_collection(cname)

