"""
handlers/query_handler.py
─────────────────────────
Mirrors the n8n "Response Formatter" Code node.

Thin wrapper around the Query agent invocation that:
  1. Calls run_query_agent()
  2. Returns the output string
  3. Falls back to a canned error reply on exception

Keeping the invocation + error handling here (not in main.py) means the
orchestrator (main.py) stays clean and routing-only.
"""

import logging
from typing import Any

from agents.query_agent import run_query_agent
from handlers.static_replies import query_error_reply

logger = logging.getLogger(__name__)


def handle_query(agent: Any, chat_input: str) -> str:
    """
    Run the query agent and return a reply string.

    Parameters
    ----------
    agent      : Compiled LangGraph agent from build_query_agent().
    chat_input : Sanitised user message.

    Returns
    -------
    Natural-language answer or a user-friendly error message.
    """
    try:
        return run_query_agent(agent, chat_input)
    except Exception as exc:
        logger.error("Query handler caught error: %s", exc)
        return query_error_reply(exc)
