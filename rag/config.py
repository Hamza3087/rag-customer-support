from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Embeddings
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")  # or "openai"
    sentence_model_name: str = os.getenv("SENTENCE_MODEL", "all-MiniLM-L6-v2")
    openai_model_name: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # Vector DB
    chroma_persist_dir: str = os.getenv("CHROMA_DIR", ".chroma")
    collection_name: str = os.getenv("CHROMA_COLLECTION", "cloudsync_rag")

    # Retrieval
    top_k: int = int(os.getenv("TOP_K", "8"))


settings = Settings()

