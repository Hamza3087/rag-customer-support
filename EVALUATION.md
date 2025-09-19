Evaluation Report

How to run
- Build/rebuild index: python cli.py query --rebuild-index (or python cli.py eval --rebuild-index)
- Evaluate: python cli.py eval

Metrics checked (from test_queries.json)
- Response quality: accuracy, completeness, relevance, clarity (qualitative via expected phrases)
- Retrieval quality: precision/recall/ranking/diversity (proxied by citations and pass/fail on phrase expectations)
- Citation quality: accuracy/specificity/completeness/format (we verify IDs in citations)
- Edge case handling: unknown/ambiguous/conflicting/version awareness (notes appended when detected)

Baseline results (before dependency install)
- Initial dependency-free baseline passed 3/12 queries (semantic TF-IDF + in-memory vectors).
- After switching to real vector DB + embeddings and installing dependencies, re-run eval to capture updated results.

Planned improvements
- Fine-tune retrieval weights and keyword-to-semantic blending per query type.
- Add stronger re-ranker (cross-encoder) if needed.
- Expand synonym list and negation handling.
- Strengthen answer formatting per query class (troubleshooting vs billing vs developer).

