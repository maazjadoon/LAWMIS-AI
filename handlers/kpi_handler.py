"""
handlers/kpi_handler.py
───────────────────────
Mirrors the n8n "KPI Dashboard Formatter" Code node.

Calls the KPI agent and returns the dashboard string, falling back to a
canned error reply on exception. The emoji formatting lives entirely inside
the KPI agent's system prompt — this handler just extracts and passes it.
"""

import logging
from typing import Any

from agents.kpi_agent import run_kpi_agent
from handlers.static_replies import kpi_error_reply

logger = logging.getLogger(__name__)


def handle_kpi(agent: Any, chat_input: str) -> str:
    """
    Run the KPI agent and return a formatted dashboard reply.

    Parameters
    ----------
    agent      : Compiled LangGraph agent from build_kpi_agent().
    chat_input : Sanitised user message.

    Returns
    -------
    Emoji-formatted KPI dashboard string or a user-friendly error message.
    """
    try:
        return run_kpi_agent(agent, chat_input)
    except Exception as exc:
        logger.error("KPI handler caught error: %s", exc)
        return kpi_error_reply(exc)
