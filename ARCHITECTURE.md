Architecture

System components

- Datasets: product_docs.json, support_tickets.json
- Data loader (rag/data_loader.py): normalizes docs into typed objects
- Chunker (rag/chunker.py): preserves numbered steps, lists, and sections; attaches metadata
- Embeddings (rag/embeddings.py): Sentence-Transformers (default) or OpenAI
- Vector DB (rag/vecdb.py): ChromaDB persistent collection with cosine metric
- Indexer (rag/indexer.py): builds/refreshes collection with sanitized metadata
- Retrieval (rag/retrieval.py): hybrid semantic + BM25 with re-ranking
- Generator (rag/generator.py): formats answers, citations, and confidence; handles edge cases
- Evaluator (rag/evaluator.py): tolerant test runner over test_queries.json
- API (server.py): FastAPI exposing /api/\* for query, db, trace, eval; serves frontend
- Frontend (web/): Bootstrap SPA for interactive use

Data flow

1. Load datasets via data_loader → Document objects
2. Chunk via chunker → Chunk objects with metadata (id, title, doc_id, source=doc|ticket, doc_type, section, tags, version, last_updated, status, etc.)
3. Compute embeddings & upsert into Chroma (indexer) → persistent store (.chroma)
4. Retrieve via HybridRetriever:
   - Semantic: Chroma similarity search
   - Keyword: BM25 on tokenized text (rag/embeddings.tokenize)
   - Score fusion + boosts: doc type priority (docs > resolved tickets > pending), recency boost, version match boost; synonym/negation cues
5. Generate response: merge relevant bullets/steps, add citations (Title (doc_id) | section: .. | version: ..), compute confidence, and attach warnings for insufficient/conflicting/outdated
6. Deliver via CLI or FastAPI; frontend renders JSON in panels

Design decisions & trade-offs

- ChromaDB chosen for simplicity (no external service) and persistence; suits evaluation scale yet production-ready with clear upgrade path (e.g., pgvector, Pinecone).
- Sentence-Transformers (all-MiniLM-L6-v2) chosen as default for offline use; optional OpenAI embeddings for higher recall.
- Rule-based classifier: sufficient for this task, simple and transparent; can be replaced by ML later.
- Scoring: practical heuristics (priorities, recency, version) rather than complex learned re-ranker to meet time constraints.

Complexity challenge (implemented)

- Challenge A: Version-Aware Information Management
  - Extract version tokens from queries
  - Boost chunks with matching version; gently downweight mismatches
  - Annotate answers when potential mismatches exist (outdated/upgrade notes)
  - Supports migration scenarios by merging relevant info from multiple versions

API & frontend integration

- Endpoints: /api/health, /api/query (POST/GET), /api/trace (POST), /api/db/\*, /api/eval (GET), /api/rebuild (POST)
- Frontend tabs: Query, Database (stats/list/show), Trace (semantic/BM25/combined), Evaluate
- Static assets under /static; index.html served at /

