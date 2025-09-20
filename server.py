from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from rag.data_loader import load_all
from rag.indexer import build_index
from rag.retrieval import HybridRetriever
from rag.generator import format_answer
from rag.evaluator import evaluate
from rag.vecdb import get_collection
from rag.embeddings import tokenize

# --------- App setup ---------
app = FastAPI(title="CloudSync RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend from ./web without shadowing /api routes
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    # Mount static assets at /static
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(web_dir / "index.html"))

# --------- Global state ---------
DATASET_DIR = Path(".")
_docs_loaded = False
_product_docs = []
_tickets = []
_retriever: Optional[HybridRetriever] = None
_lock = threading.Lock()


def _ensure_loaded_and_built(rebuild_index: bool = False):
    global _docs_loaded, _product_docs, _tickets, _retriever
    with _lock:
        if not _docs_loaded:
            _product_docs, _tickets = load_all(DATASET_DIR)
            _docs_loaded = True
        if rebuild_index or _retriever is None:
            # Rebuild Chroma index and in-memory BM25
            build_index(_product_docs + _tickets)
            _retriever = HybridRetriever()
            _retriever.build_index(_product_docs + _tickets)


# --------- Models (lightweight dicts used directly) ---------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/db/stats")
async def db_stats():
    _ensure_loaded_and_built(False)
    coll = get_collection()
    return {"count": coll.count()}


@app.get("/api/db/list")
async def db_list(limit: int = Query(5, ge=1, le=200), where: Optional[str] = None):
    _ensure_loaded_and_built(False)
    coll = get_collection()
    try:
        where_obj = json.loads(where) if where else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'where' parameter")
    res = coll.get(where=where_obj, limit=limit)
    out = []
    ids = res.get("ids", [])
    metadatas = res.get("metadatas", [])
    docs = res.get("documents", [])
    for i in range(len(ids)):
        meta = metadatas[i] if i < len(metadatas) else {}
        doc = docs[i] if i < len(docs) else ""
        out.append({
            "id": ids[i],
            "metadata": meta,
            "text_preview": (doc[:200] + ("…" if doc and len(doc) > 200 else "")) if doc else "",
        })
    return out


@app.get("/api/db/show")
async def db_show(id: str = Query(..., description="Chunk ID")):
    _ensure_loaded_and_built(False)
    coll = get_collection()
    res = coll.get(ids=[id])
    if not res.get("ids"):
        raise HTTPException(status_code=404, detail="not_found")
    return {
        "id": res["ids"][0],
        "metadata": res["metadatas"][0],
        "text": res["documents"][0],
    }


@app.post("/api/query")
async def api_query(payload: Any = Body(None)):
    # Accept either a JSON object {"query": ...} or a raw string body
    q: str = ""
    top_k: int = 6
    rebuild: bool = False
    if isinstance(payload, dict):
        q = str(payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 6)
        rebuild = bool(payload.get("rebuild_index") or False)
    elif isinstance(payload, str):
        q = payload.strip()
    else:
        q = ""
    if not q:
        raise HTTPException(status_code=400, detail="query is required (send raw text or JSON {\"query\": \"...\"})")
    _ensure_loaded_and_built(rebuild)
    assert _retriever is not None
    results = _retriever.retrieve(q, top_k=top_k)
    answer, conf, citations = format_answer(q, results)
    return {
        "query": q,
        "answer": answer,
        "confidence": round(conf, 4),
        "citations": citations,
    }

# Convenience GET variant for simple testing in browser/curl
@app.get("/api/query")
async def api_query_get(q: str = Query(..., description="Query text"), top_k: int = Query(6, ge=1, le=20), rebuild_index: bool = Query(False)):
    _ensure_loaded_and_built(rebuild_index)
    assert _retriever is not None
    results = _retriever.retrieve(q, top_k=top_k)
    answer, conf, citations = format_answer(q, results)
    return {
        "query": q,
        "answer": answer,
        "confidence": round(conf, 4),
        "citations": citations,
    }


@app.post("/api/trace")
async def api_trace(payload: Any = Body(None)):
    # Accept {"query": ...} or raw text
    q: str = ""
    top_k: int = 6
    if isinstance(payload, dict):
        q = str(payload.get("query") or "").strip()
        top_k = int(payload.get("top_k") or 6)
    elif isinstance(payload, str):
        q = payload.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required (send raw text or JSON {\"query\": \"...\"})")
    _ensure_loaded_and_built(False)
    assert _retriever is not None

    qv = _retriever._extract_version(q)

    # Semantic candidates
    sem = _retriever._semantic_candidates(q, top_k, qv)
    sem_list = [{"id": cid, "semantic": sc} for cid, sc in sem[: max(4 * top_k, 32)]]

    # Keyword BM25
    kw_scores = []
    if _retriever._bm25 is not None:
        scores = _retriever._bm25.get_scores(tokenize(q))
        top_kw = sorted(range(len(_retriever.chunks)), key=lambda i: scores[i], reverse=True)[: max(4 * top_k, 32)]
        for i in top_kw:
            kw_scores.append({"id": _retriever.chunks[i].chunk_id, "bm25": float(scores[i])})

    # Combined results
    combined = _retriever.retrieve(q, top_k=top_k)
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

    return {"query": q, "semantic": sem_list, "bm25": kw_scores, "combined": combined_list}


@app.get("/api/eval")
async def api_eval(rebuild_index: bool = Query(False)):
    try:
        _ensure_loaded_and_built(rebuild_index)
        passed, total, notes = evaluate(DATASET_DIR)
        return {"passed": passed, "total": total, "notes": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "evaluation_failed", "message": str(e)})


# Convenience endpoint to trigger index rebuild explicitly
@app.post("/api/rebuild")
async def api_rebuild():
    _ensure_loaded_and_built(True)
    coll = get_collection()
    return {"status": "ok", "count": coll.count()}


# Startup: load and build once so first request is fast
@app.on_event("startup")
async def startup_event():
    try:
        _ensure_loaded_and_built(False)
    except Exception:
        # Start without blocking if embeddings/chroma are not installed; API will error clearly on first call
        pass


# If run directly: uvicorn server:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

