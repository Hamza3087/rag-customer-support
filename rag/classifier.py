from __future__ import annotations

from typing import Literal

QueryType = Literal[
    "product_setup",
    "troubleshooting",
    "billing",
    "advanced_features",
    "performance",
    "feature_usage",
    "developer",
    "security",
    "sharing",
    "known_issue",
    "comparison",
    "cancellation",
    "technical_issue",
    "other",
]


def classify_query(q: str) -> QueryType:
    s = q.lower()
    if any(k in s for k in ["sign up", "create account", "signup", "register"]):
        return "product_setup"
    # Performance before troubleshooting when both appear
    if any(k in s for k in ["slow", "performance", "lag", "bandwidth", "throttling"]):
        return "performance"
    if any(k in s for k in ["not syncing", "aren't syncing", "troubleshoot", "fix", "isn't syncing"]):
        return "troubleshooting"
    if any(k in s for k in ["billing", "charged", "subscription", "refund", "downgrade", "cancel"]):
        if "cancel" in s:
            return "cancellation"
        return "billing"
    if any(k in s for k in ["advanced", "version history", "selective sync", "sharing"]):
        return "advanced_features"
    if any(k in s for k in ["how do i", "how can i", "where do i", "feature", "previous versions", "version"]):
        return "feature_usage"
    if any(k in s for k in ["api", "sdk", "developer", "oauth", "webhook"]):
        return "developer"
    if any(k in s for k in ["secure", "security", "encryption", "two-factor", "2fa", "privacy"]):
        return "security"
    # Known issue before sharing to capture problematic shared-folder scenarios
    if any(k in s for k in ["known issue", "bug", "can't see", "not visible", "investigating"]):
        return "known_issue"
    if any(k in s for k in ["crash", "crashing", "mobile app", "app crashes"]):
        return "technical_issue"
    if any(k in s for k in ["share ", "shared folder", "permission"]):
        return "sharing"
    if any(k in s for k in ["difference", "compare", "free vs", "free and pro"]):
        return "comparison"
    return "other"

