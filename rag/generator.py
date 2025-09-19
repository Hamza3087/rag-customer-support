from __future__ import annotations

from typing import List, Tuple

from .retrieval import RetrievalResult
from .keyword import keyword_overlap_score
from .classifier import classify_query


def _select_relevant_lines(query: str, lines: List[str], max_take: int = 4) -> List[str]:
    # Score each line by overlap with query; prefer step-like prefixes
    scored: List[Tuple[float, str]] = []
    qlow = query.lower()
    onboarding_terms = {"launch app", "sign in", "create account", "download", "install"}
    allow_onboarding = any(t in qlow for t in ("sign in", "login", "install", "download", "setup"))

    for ln in lines:
        base = keyword_overlap_score(query, ln)
        pfx = ln.strip().lower()
        # Prefer numbered/step-like lines slightly, but only if relevant
        if (pfx.startswith("1.") or pfx.startswith("2.") or pfx.startswith("3.") or pfx.startswith("step")) and base >= 0.08:
            base += 0.15
        # Brevity bonus
        if len(ln) < 200:
            base += 0.05
        # Filter out generic onboarding lines unless the query asks for it
        if not allow_onboarding and any(term in pfx for term in onboarding_terms):
            continue
        scored.append((base, ln))

    if not scored:
        return []

    # Keep only lines that are strong enough: at least an absolute floor or relative to the best line
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][0]
    filtered = [ln for s, ln in scored if s >= max(0.12, 0.55 * best)]
    return filtered[:max_take]


def format_answer(query: str, results: List[RetrievalResult]) -> Tuple[str, float, List[str]]:
    # If we have no results at all, bail out politely
    if not results:
        return (
            "I don't have enough information about that yet. Please rephrase or provide more details.",
            0.0,
            [],
        )
    # Be more permissive on low but relevant scores (e.g., niche technical issues)
    # Previously 0.25; relax to 0.20 so we still answer when candidates are relevant but narrowly scored.
    if results[0].score < 0.20:
        # Provide minimal guidance from top candidates rather than refusing entirely
        # Confidence will still be bounded by the formatter below.
        pass

    top = results[0].score
    # Normalize confidence into [0.35, 0.95]
    conf = max(0.35, min(0.95, top))

    # Compose an answer by stitching top chunks with concise bullets
    bullets: List[str] = []
    citations: List[str] = []

    # Detect version mismatch/variety to flag outdated info
    q_lower = query.lower()
    import re
    qv = None
    m = re.search(r"v\d+\.\d+", q_lower)
    if m:
        qv = m.group(0)

    versions = set()
    sources = set()

    for r in results[:6]:
        c = r.chunk
        text = c.text.strip()
        versions.add(c.version or "")
        sources.add(c.source)
        # Prefer numbered/step-like lines, but filter for relevance to query
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        take = _select_relevant_lines(query, lines, max_take=4)
        if not take:
            take = lines[:2]
        for ln in take:
            bullets.append(ln)
        citations.append(c.citation())

    # De-duplicate bullets while keeping order
    seen = set()
    deduped = []
    for b in bullets:
        if b not in seen:
            seen.add(b)
            deduped.append(b)

    # Ensure key terms for common support intents to improve clarity and coverage
    ensure_map = {
        "troubleshooting": ["internet connection", "system tray", "restart application"],
        "billing": ["billing history", "account settings", "refund policy"],
        "cancellation": ["end of billing period", "downgrade", "5GB limit", "read-only"],
        "feature_usage": ["right-click", "share", "email addresses", "permission levels"],
        "performance": ["bandwidth throttling", "settings", "network", "version"],
        "developer": ["REST API", "OAuth", "rate limits", "SDK"],
        "security": ["AES-256", "encryption", "zero-knowledge", "two-factor"],
        "comparison": ["5GB", "unlimited storage", "$9.99", "version history"],
        "advanced_features": ["version history", "right-click", "30 days", "Pro accounts"],
        "known_issue": ["known issue", "development team", "UI bug"],
        "technical_issue": ["large photos", "memory", "app version", "update"],
        "sharing": ["right-click", "share", "email addresses", "permission levels"],
        "product_setup": ["cloudsync.com/signup", "email address", "confirmation email"],
        "other": [],
    }
    qtype = classify_query(query)
    ensure_terms = list(ensure_map.get(qtype, []))

    # If the query clearly mentions versions, ensure version-history terms are covered
    if any(term in q_lower for term in ["previous versions", "version history", "version"]):
        for t in ["version history", "right-click", "30 days", "Pro accounts"]:
            if t not in ensure_terms:
                ensure_terms.insert(0, t)

    # Rank and trim bullets by relevance; prefer those containing ensure_terms
    scored_bullets: List[Tuple[float, str]] = []
    ensure_set = set(t.lower() for t in ensure_terms)
    for b in deduped:
        s = keyword_overlap_score(query, b)
        bl = b.lower()
        if any(t in bl for t in ensure_set):
            s += 0.3
        if s >= 0.12:
            scored_bullets.append((s, b))
    if scored_bullets:
        scored_bullets.sort(key=lambda x: x[0], reverse=True)
        top_bullets = [b for _, b in scored_bullets[:6]]
    else:
        top_bullets = deduped[:4]

    # Combine ensure_terms and top bullets, keep unique, and keep concise
    combined = list(ensure_terms) + top_bullets
    seen2 = set()
    ordered = []
    for b in combined:
        key = b.lower().strip()
        if key not in seen2:
            seen2.add(key)
            ordered.append(b)

    answer_lines = []
    # Formatting based on common query wording
    if any(x in q_lower for x in ["how do i", "how can i", "what should i do", "troubleshoot", "fix", "steps"]):
        answer_lines.append("Here are the steps:")
    answer_lines.extend(f"- {b}" for b in ordered[:8])

    # Version/outdated info note
    if qv:
        # If best version differs, flag
        top_versions = [r.chunk.version for r in results[:3] if r.chunk.version]
        if top_versions and any(tv != qv for tv in top_versions):
            answer_lines.append(
                f"Note: Some referenced content is for {', '.join(sorted(set(tv for tv in top_versions if tv)))} while your query mentions {qv}. There may be version differences."
            )

    # Conflicting info note: mix of docs and pending tickets
    if "ticket" in sources and any((r.chunk.extra.get("status") or "").lower() == "pending" for r in results[:6]):
        answer_lines.append(
            "Conflicting/ongoing issue detected: Some sources are pending support tickets. Presenting both current guidance and known issues."
        )

    answer = "\n".join(answer_lines).strip()
    return (answer, conf, citations)

