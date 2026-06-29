"""
router.py
─────────
Mirrors the n8n "Intent Router" Switch node.

Pure keyword-matching — no LLM call needed for routing. Evaluates the cleaned
chatInput string (case-insensitive) against ordered keyword groups and returns
the first matching intent label.

Intent priority order  (same as n8n output ordering):
  1. export          – export / append to sheet / download
  2. update_delete   – update / delete / remove / insert
  3. kpi             – dashboard, analytics, statistics, pass rate, etc.
  4. pdf             – pdf / generate report / create report / …
  5. pptx            – pptx / powerpoint / slides / …
  6. query           – fallback (everything else)
"""

import re

# ── Keyword definitions ───────────────────────────────────────────────────────
# Each entry is (intent_label, [list_of_keyword_phrases]).
# The list is evaluated with OR logic — first match wins.
# Phrases can contain spaces (they are matched as substrings).

_INTENT_RULES: list[tuple[str, list[str]]] = [
    (
        "export",
        ["export", "append to sheet", "download"],
    ),
    (
        "update_delete",
        ["update", "delete", "remove", "insert"],
    ),
    (
        "document",
        [
            "read document",
            "read the document",
            "read file",
            "read the file",
            "read pdf",
            "read the pdf",
            "read pptx",
            "read the pptx",
            "analyze pdf",
            "analyze pptx",
            "analyse pdf",
            "analyse pptx",
            "summarize pdf",
            "summarise pdf",
            "summarize pptx",
            "summarise pptx",
            "pdf at",
            "pptx at",
            "file at",
            "analyze",
            "analyse",
            "open file",
            "load file",
            "upload",
            "summarize the",
            "summarise the",
            "extract from",
            "what does the file",
            "what is in the file",
        ],
    ),
    (
        "pdf",
        [
            "pdf",
            "pdf report",
            "generate pdf",
            "create pdf",
            "make pdf",
            "build pdf",
            "print pdf",
            "generate report",
            "create report",
            "make report",
            "build report",
            "print report",
        ],
    ),
    (
        "pptx",
        [
            "pptx",
            "powerpoint",
            "slide deck",
            "slides",
            "presentation",
            "convert kpi",
        ],
    ),
    (
        "kpi",
        [
            "dashboard",
            "kpi",
            "statistics",
            "overview",
            "analytics",
            "summary",
            "pass rate",
            "revenue",
            "emission tests",
            "total workshops",
            "active workshops",
            "pending applications",
            "total licenses",
            "expired licenses",
            "performance report",
            "growth trend",
            "top cities",
            "top districts",
            "monthly",
            "average inspection",
            "failure rate",
        ],
    ),
]

_FALLBACK_INTENT = "query"


def detect_intent(text: str) -> str:
    """
    Detect the user's intent from the sanitised chat input.

    Parameters
    ----------
    text : Cleaned chat input (output of sanitizer.sanitize()["chatInput"]).

    Returns
    -------
    One of: "export" | "update_delete" | "kpi" | "pdf" | "pptx" | "query"
    """
    lower_text = text.lower()

    for intent_label, keywords in _INTENT_RULES:
        for kw in keywords:
            # Use word-boundary-aware search for single words; substring for
            # multi-word phrases (e.g. "append to sheet").
            if " " in kw:
                if kw in lower_text:
                    return intent_label
            else:
                # \b ensures "export" doesn't match "exportable" etc.
                if re.search(rf"\b{re.escape(kw)}\b", lower_text):
                    return intent_label

    return _FALLBACK_INTENT
