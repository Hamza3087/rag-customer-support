CloudSync RAG System (SageTeck Employee Evaluation Task)

Overview
- Retrieval-Augmented Generation (RAG) pipeline to assist CloudSync support agents.
- Sources: product_docs.json and support_tickets.json.
- Vector DB: ChromaDB with Sentence-Transformers or OpenAI embeddings.
- Hybrid retrieval: semantic (vector) + BM25 keyword; re-ranking by doc type, recency, and version awareness.
- Response generation: clear steps/bullets, citations with titles/IDs/sections, confidence estimate; flags version/outdated/conflicts.

Quickstart
1) Python 3.10+ recommended.
2) Install dependencies (requires internet):
   pip install -r requirements.txt
3) Choose embeddings (default is sentence-transformers):
   - Sentence-Transformers (default): no env needed.
   - OpenAI embeddings: set EMBEDDING_BACKEND=openai and OPENAI_API_KEY; optional OPENAI_EMBED_MODEL.
4) Build index and query:
   python cli.py query --rebuild-index
5) Evaluate on test queries:
   python cli.py eval --rebuild-index

Configuration (env vars)
- EMBEDDING_BACKEND: "sentence-transformers" (default) or "openai"
- SENTENCE_MODEL: e.g., "all-MiniLM-L6-v2"
- OPENAI_EMBED_MODEL: e.g., "text-embedding-3-small"
- CHROMA_DIR: directory for Chroma persistence (default .chroma)
- CHROMA_COLLECTION: collection name (default cloudsync_rag)
- TOP_K: default top-k for retrieval (CLI overrides)

Repository layout
- cli.py: CLI for index/query/eval
- rag/
  - config.py: settings/env
  - data_loader.py: load JSON datasets
  - types.py: Document/Chunk dataclasses
  - chunker.py: intelligent chunking (preserve lists/steps/sections)
  - vecdb.py: Chroma client and collection helpers
  - indexer.py: build index into Chroma
  - retrieval.py: hybrid retrieval (Chroma + BM25) and re-ranking
  - keyword.py: synonym expansion and keyword overlap utilities
  - classifier.py: simple rule-based query classification
  - generator.py: answer formatting, citations, confidence, edge-case notes
  - evaluator.py: runs test_queries.json with tolerant loader

Notes on test_queries.json
- The provided file has a small formatting glitch near the first query (missing comma before "notes").
- evaluator.py includes tolerant loading to avoid modifying original file. If preferred, fix the JSON manually.

Work log (high level)
- Implemented data model, loaders, chunker with section/list preservation.
- Added ChromaDB vector index and Sentence-Transformer/OpenAI embeddings.
- Implemented BM25 keyword retrieval and hybrid re-ranking (doc type, recency, version).
- Added version-aware notes and conflict detection in generator.
- Built CLI and evaluation harness with robust test_queries loader.

Limitations & Next steps
- Rule-based classifier can be upgraded to ML-based (scikit-learn) with labeled queries.
- Advanced re-ranker (cross-encoder) could further improve ranking.
- Add API server endpoint (FastAPI) if needed.
- Expand unit tests.

