Architecture

Data flow
1. Load JSON datasets (product_docs.json, support_tickets.json) via rag/data_loader.py
2. Chunk documents preserving steps/sections via rag/chunker.py into rag/types.Chunk
3. Index chunks in Chroma (rag/indexer.py) with embedding function (Sentence-Transformers or OpenAI). Store metadata (id, title, source, doc_type, version, last_updated, tags, section, status, etc.)
4. Hybrid retrieval (rag/retrieval.py):
   - Semantic: Chroma query(query_texts)
   - Keyword: BM25 over tokenized chunk texts
   - Combine using weighted score with boosts (doc type priority, recency, version awareness)
5. Answer generation (rag/generator.py): selects top lines, formats bullets/steps, adds citations and confidence; flags version mismatch/outdated/conflicts.
6. Evaluation (rag/evaluator.py): runs test_queries.json, checks expected phrases and citations.

Key design decisions
- Vector DB: ChromaDB for a lightweight, local, persistent vector store with built-in embedding function hooks.
- Embeddings: Default to sentence-transformers (all-MiniLM-L6-v2) for offline, no-API-key usage. Optional OpenAI for higher quality if key provided.
- Chunking: Preserve lists/step sequences and sections using simple regex heuristics; split long chunks by paragraph/sentence.
- Hybrid retrieval: Semantic + BM25 to cover both semantic similarity and exact term coverage; re-ranking with practical heuristics.
- Version-awareness: Extract version tokens (e.g., v2.0), prefer exact-match; flag mismatches.
- Conflict/outdated handling: Identify pending tickets vs docs and mixed versions.

Extensibility
- Swap embedding models by env vars without code changes.
- Add cross-encoder re-ranker (e.g., sentence-transformers/ms-marco-MiniLM-L-6-v2) for improved ranking.
- Add API layer (FastAPI) exposing /query endpoint returning answer, confidence, citations.
- Add feedback loop to learn from accepted answers (store in new collection and boost similar cases).

