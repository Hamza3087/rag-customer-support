Evaluation Report

How to run (CLI)

- Build & evaluate (JSON):
  python cli.py eval --rebuild-index --json
- Quick re-run without rebuild:
  python cli.py eval --json

How to run (API)

- Ensure server is running: uvicorn server:app --reload
- Call: GET http://localhost:8000/api/eval
  Optional: ?rebuild_index=true

What is measured (from test_queries.json)

- Response quality: accuracy, completeness, relevance, clarity (via expected phrases)
- Retrieval quality: proxies via correct citations and passing phrase checks
- Citation quality: title/ID/section/version formatting and correctness
- Edge case handling: insufficient/conflicting/outdated/version flags

Results

- Current: {"passed": 12, "total": 12, "notes": []}
- Verified via CLI and API

Challenge implemented

- Challenge A: Version-Aware Information Management
  - Version token extraction and matching (e.g., v2.0 vs v2.1)
  - Boosting for exact match, gentle downweight for mismatches
  - Explicit warnings in answers when mixing versions or referencing outdated info
  - Supports migration scenarios (e.g., user on v2.0 asking about features in v2.1)

Evidence & commands

- Sample query (JSON answer):
  python cli.py query --json "How do I share folders with other people?"

- Database inspection:
  python cli.py db stats
 
- Retrieval trace (semantic/BM25/combined):
  python cli.py trace "How do I share folders with other people?" --top-k 6 > trace.json
