"""
sanitizer.py
────────────
Mirrors the n8n "Input Sanitizer & Logger" Code node.

Responsibilities:
  • Strip leading/trailing whitespace and collapse internal whitespace
  • Truncate messages that exceed MAX_LEN characters
  • Assign / propagate a session ID
  • Log every incoming message with timestamp + session context
  • Return a structured dict with chatInput, originalMessage, sessionId, isEmpty
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Maximum allowed message length (matches n8n node)
MAX_LEN: int = 4_000


def sanitize(raw_input: str, session_id: str | None = None) -> dict:
    """
    Sanitise a raw user message.

    Parameters
    ----------
    raw_input:  The raw string received from the chat interface.
    session_id: An existing session identifier. If None, a new UUID is generated.

    Returns
    -------
    dict with keys:
        chatInput       – cleaned, truncated message ready for the LLM
        originalMessage – the raw input unchanged
        sessionId       – stable session identifier
        isEmpty         – True when chatInput is empty after cleaning
    """
    # ── Normalise whitespace ─────────────────────────────────────────────────
    clean: str = " ".join(str(raw_input).split())   # collapse all whitespace

    # ── Truncate ─────────────────────────────────────────────────────────────
    if len(clean) > MAX_LEN:
        clean = clean[:MAX_LEN]

    # ── Session ID ───────────────────────────────────────────────────────────
    sid: str = session_id or str(uuid.uuid4())

    # ── Log ──────────────────────────────────────────────────────────────────
    ts: str = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    logger.info("[%s] session=%s len=%d", ts, sid, len(clean))

    return {
        "chatInput": clean,
        "originalMessage": raw_input,
        "sessionId": sid,
        "isEmpty": len(clean) == 0,
    }
