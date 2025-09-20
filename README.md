CloudSync RAG System (SageTeck Employee Evaluation Task)

Overview

- End-to-end Retrieval-Augmented Generation (RAG) to assist CloudSync support agents.
- Sources: product_docs.json (7 docs) and support_tickets.json (8 tickets).
- Vector DB: ChromaDB (persistent) with Sentence-Transformers (default) or OpenAI embeddings.
- Hybrid retrieval: semantic (vector) + BM25 keyword, re-ranked by doc type, recency, version awareness, and light intent rules.
- Response generation: clear steps/bullets, citations (title/ID/section/version), confidence; flags version mismatch/outdated/conflicts.
- FastAPI backend + attractive web frontend for query, DB inspection, trace, and evaluation.

Requirements checklist

- Part 1: Document Processing & Indexing
  - [x] Load/parse both JSON files
  - [x] Intelligent chunking preserving lists/steps/sections and metadata
  - [x] Real embeddings (Sentence-Transformers default; OpenAI optional)
  - [x] Persistent vector database (ChromaDB)
- Part 2: Smart Retrieval System
  - [x] Hybrid retrieval (semantic + BM25)
  - [x] Prioritize official docs > resolved tickets > pending tickets
  - [x] Query variation handling (synonyms, simple negations)
  - [x] Re-ranking by recency and version awareness
  - [x] Boost similar prior tickets
- Part 3: Response Generation & Citations
  - [x] Comprehensive answers with numbered steps
  - [x] Proper citations with titles/IDs/sections and confidence
  - [x] Edge cases: insufficient/conflicting/outdated version flags
- Complexity challenge (chosen):
  - [x] Challenge A: Version-Aware Information Management
- Deliverables
  - [x] Working system, CLI + REST API + web frontend
  - [x] Documentation (README, ARCHITECTURE, EVALUATION, API via /docs)
  - [x] Evaluation report (12/12 passing)
  - [x] Code quality: typed dataclasses, error handling, unit tests, requirements.txt

Quickstart

1. Python 3.10+ recommended.
2. Install dependencies (internet required first time):
   pip install -r requirements.txt
   pip install fastapi uvicorn[standard]
3. CLI usage
   - Build index & query (JSON):
     python cli.py query --rebuild-index --json "How do I share folders with other people?"
   - Evaluate (JSON):
     python cli.py eval --rebuild-index --json
4. Start API + frontend
   uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   Open http://localhost:8000 (frontend) and http://localhost:8000/docs (API docs)

Frontend features (web/)

- Query: ask questions, Top K, optional rebuild, full JSON output with citations.
- Database: chunk count, list (with JSON filter), show specific chunk.
- Trace: semantic, BM25, and combined top-k with previews.
- Evaluate: run full evaluation and view summary – designed for 12/12 passing.
- Quality-of-life: loading indicators, toasts, copy-on-click JSON, tab state persists.

API endpoints (FastAPI)

- GET /api/health
- GET /api/db/stats
- GET /api/db/list?limit=5&where={"source":"doc"}
- GET /api/db/show?id=<chunk_id>
- POST /api/query {"query":"...", "top_k":6, "rebuild_index":false}
  - Also accepts raw string body or text/plain
- POST /api/trace {"query":"...", "top_k":6}
- GET /api/eval?rebuild_index=false
- POST /api/rebuild

DB/trace/eval: tested commands

- Count chunks:
  python cli.py db stats
- List chunks (filter):
  python cli.py db list --limit 5 --where '{"source":"doc"}'
- Show chunk:
  python cli.py db show --id "doc_004:::..."
- Trace (save to file):
  python cli.py trace "How do I share folders with other people?" --top-k 6 > trace.json
- API equivalents: see curl examples in server docs (/docs) or the README "API endpoints" section.

Configuration (env vars)

- EMBEDDING_BACKEND: "sentence-transformers" (default) or "openai"
- SENTENCE_MODEL: e.g., "all-MiniLM-L6-v2"
- OPENAI_EMBED_MODEL: e.g., "text-embedding-3-small"
- OPENAI_API_KEY: required if using OpenAI backend
- CHROMA_DIR: persistence dir (default .chroma)
- CHROMA_COLLECTION: collection name (default cloudsync_rag)
- TOP_K: default retrieval top-k (CLI/API can override)

Repository layout

- cli.py: CLI for index/query/db/trace/eval
- server.py: FastAPI app serving /api and frontend (mounted at /)
- web/: index.html, styles.css, app.js (Bootstrap-based SPA)
- rag/
  - config.py: settings/env
  - data_loader.py: load JSON datasets
  - types.py: Document/Chunk dataclasses
  - chunker.py: intelligent chunking (preserve lists/steps/sections)
  - vecdb.py: Chroma client and collection helpers
  - indexer.py: build index into Chroma
  - retrieval.py: hybrid retrieval (Chroma + BM25) and re-ranking
  - keyword.py: synonyms/negation helpers
  - classifier.py: intent classification (rule-based)
  - generator.py: answer formatting, citations, confidence, edge-case notes
  - evaluator.py: runs test_queries.json, tolerant loader for minor formatting glitches
- tests/: unit tests (chunking, version-awareness)

Evaluation results

- CLI: python cli.py eval --rebuild-index --json → {"passed": 12, "total": 12, "notes": []}
- API: GET /api/eval → {"passed": 12, "total": 12, "notes": []}

Work log (high level)

- Implemented data model, loader, and intelligent chunker (preserves lists/steps/sections)
- ChromaDB persistence + Sentence-Transformers (OpenAI optional)
- Hybrid retrieval + re-ranking (doc type, recency, version, synonym/negation cues)
- Version-aware notes, conflict and outdated info flags
- CLI with JSON outputs, DB inspection, and trace tools
- FastAPI API and Bootstrap frontend with interactive panels
- Fixed confidence edge case (no more zero for borderline matches)
- Wrote/verified unit tests; evaluation: 12/12 passing

Limitations & next steps

- Classifier is rule-based; can be replaced with ML classifier if labeled data available.
- Add a cross-encoder re-ranker for improved precision on hard queries.
- Optional streaming answers via Server-Sent Events (SSE) for long responses.
- Expand tests to cover generator formatting and API endpoints.
