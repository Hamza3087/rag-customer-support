from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.data_loader import load_all
from rag.indexer import build_index
from rag.retrieval import HybridRetriever
from rag.generator import format_answer
from rag.evaluator import evaluate
from rag.vecdb import get_collection
from rag.embeddings import tokenize


def cmd_build_and_query(args):
    dataset_dir = Path(args.dataset_dir)
    product_docs, tickets = load_all(dataset_dir)

    if args.rebuild_index:
        count = build_index(product_docs + tickets)
        print(f"Rebuilt vector index with {count} chunks.")

    retriever = HybridRetriever()
    retriever.build_index(product_docs + tickets)

    # One-shot mode if text was provided
    if args.text:
        q = " ".join(args.text).strip()
        results = retriever.retrieve(q, top_k=args.top_k)
        answer, conf, citations = format_answer(q, results)
        if getattr(args, "json", False):
            print(json.dumps({
                "query": q,
                "answer": answer,
                "confidence": round(conf, 4),
                "citations": citations,
            }, ensure_ascii=False))
        else:
            print("\nAnswer:")
            print(answer)
            print(f"\nConfidence: {conf:.2f}")
            print("Citations:")
            for c in citations:
                print(f"- {c}")
        return

    # Interactive mode
    print("Index ready. Type your query (or 'exit' to quit).\n")
    while True:
        q = input("Query> ").strip()
        if not q or q.lower() in {"exit", "quit"}:
            break
        results = retriever.retrieve(q, top_k=args.top_k)
        answer, conf, citations = format_answer(q, results)
        if getattr(args, "json", False):
            print(json.dumps({
                "query": q,
                "answer": answer,
                "confidence": round(conf, 4),
                "citations": citations,
            }, ensure_ascii=False))
        else:
            print("\nAnswer:")
            print(answer)
            print(f"\nConfidence: {conf:.2f}")
            print("Citations:")
            for c in citations:
                print(f"- {c}")
            print()


def cmd_evaluate(args):
    dataset_dir = Path(args.dataset_dir)
    # Ensure vector index exists/rebuilt for consistency
    product_docs, tickets = load_all(dataset_dir)
    if args.rebuild_index:
        count = build_index(product_docs + tickets)
        if not getattr(args, "json", False):
            print(f"Rebuilt vector index with {count} chunks.")
    else:
        # Build if missing or stale; safe to rebuild in this small dataset
        count = build_index(product_docs + tickets)
    passed, total, notes = evaluate(dataset_dir)
    if getattr(args, "json", False):
        print(json.dumps({
            "passed": passed,
            "total": total,
            "notes": notes,
        }, ensure_ascii=False))
        return
    print(f"Passed {passed}/{total} test queries.")
    if notes:
        print("\nDetails for failures:")
        for n in notes:
            print("-" * 60)
            print(n)


def cmd_db(args):
    coll = get_collection()
    # Stats
    if args.action == "stats":
        print(json.dumps({"count": coll.count()}, ensure_ascii=False))
        return
    # List with optional filter
    if args.action == "list":
        where = json.loads(args.where) if args.where else None
        res = coll.get(where=where, limit=args.limit)
        out = []
        for i in range(len(res.get("ids", []))):
            meta = res["metadatas"][i]
            doc = res["documents"][i]
            out.append({
                "id": res["ids"][i],
                "metadata": meta,
                "text_preview": (doc[:200] + ("…" if len(doc) > 200 else "")) if doc else "",
            })
        print(json.dumps(out, ensure_ascii=False))
        return
    # Show a single id
    if args.action == "show":
        res = coll.get(ids=[args.id])
        if not res.get("ids"):
            print(json.dumps({"error": "not_found", "id": args.id}))
            return
        idx = 0
        print(json.dumps({
            "id": res["ids"][idx],
            "metadata": res["metadatas"][idx],
            "text": res["documents"][idx],
        }, ensure_ascii=False))
        return


def cmd_trace(args):
    # Build in-memory structures for retrieval tracing
    dataset_dir = Path(args.dataset_dir)
    product_docs, tickets = load_all(dataset_dir)
    retriever = HybridRetriever()
    retriever.build_index(product_docs + tickets)

    q = " ".join(args.text).strip()
    qv = retriever._extract_version(q)

    # Semantic candidates (ids -> score)
    sem = retriever._semantic_candidates(q, args.top_k, qv)
    sem_list = [{"id": cid, "semantic": sc} for cid, sc in sem[: max(4 * args.top_k, 32)]]

    # Keyword BM25 scores
    kw_scores = []
    if retriever._bm25 is not None:
        scores = retriever._bm25.get_scores(tokenize(q))
        top_kw = sorted(range(len(retriever.chunks)), key=lambda i: scores[i], reverse=True)[: max(4 * args.top_k, 32)]
        for i in top_kw:
            kw_scores.append({"id": retriever.chunks[i].chunk_id, "bm25": float(scores[i])})

    # Combined results
    combined = retriever.retrieve(q, top_k=args.top_k)
    combined_list = [{
        "id": r.chunk.chunk_id,
        "score": r.score,
        "doc_id": r.chunk.doc_id,
        "source": r.chunk.source,
        "version": r.chunk.version,
        "section": r.chunk.section,
        "title": r.chunk.title,
        "text_preview": (r.chunk.text[:200] + ("…" if len(r.chunk.text) > 200 else "")),
    } for r in combined]

    payload = {"query": q, "semantic": sem_list, "bm25": kw_scores, "combined": combined_list}
    print(json.dumps(payload, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="CloudSync RAG CLI")
    sub = ap.add_subparsers(required=True)

    ap_query = sub.add_parser("query", help="Build index and open query mode (one-shot or interactive)")
    ap_query.add_argument("text", nargs="*", help="Optional query text for one-shot mode; if omitted, opens interactive shell")
    ap_query.add_argument("--dataset-dir", default=".")
    ap_query.add_argument("--top-k", type=int, default=6)
    ap_query.add_argument("--rebuild-index", action="store_true", help="Rebuild the vector index before querying")
    ap_query.add_argument("--json", action="store_true", help="Output results as JSON")
    ap_query.set_defaults(func=cmd_build_and_query)

    ap_eval = sub.add_parser("eval", help="Run evaluation over test_queries.json")
    ap_eval.add_argument("--dataset-dir", default=".")
    ap_eval.add_argument("--rebuild-index", action="store_true", help="Rebuild the vector index before evaluation")
    ap_eval.add_argument("--json", action="store_true", help="Output evaluation summary as JSON")
    ap_eval.set_defaults(func=cmd_evaluate)

    ap_db = sub.add_parser("db", help="Inspect the Chroma vector database")
    ap_db.add_argument("action", choices=["stats", "list", "show"], help="Action to perform")
    ap_db.add_argument("--limit", type=int, default=5, help="Number of records for list")
    ap_db.add_argument("--where", help="Optional JSON filter for list, e.g. '{\"source\":\"doc\"}'")
    ap_db.add_argument("--id", help="Chunk ID for 'show'")
    ap_db.set_defaults(func=cmd_db)

    ap_trace = sub.add_parser("trace", help="Trace retrieval pipeline for a query")
    ap_trace.add_argument("text", nargs="+", help="Query text")
    ap_trace.add_argument("--dataset-dir", default=".")
    ap_trace.add_argument("--top-k", type=int, default=6)
    ap_trace.set_defaults(func=cmd_trace)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

