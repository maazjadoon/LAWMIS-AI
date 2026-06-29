"""
agents/export_agent.py
──────────────────────
Mirrors the n8n "AI Agent - Export" node.

Uses LangGraph's create_react_agent (LangChain 1.x compatible).
LangGraph uses native tool-calling — no ReAct string parsing needed.

Responsible for:
  • Querying LAWMIS data for export
  • Returning ONLY a raw JSON array — no prose, no markdown, no code fences

Max iterations: 4  (matches n8n maxIterations=4)
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from agents.llm_factory import build_llm
from tools import execute_query, get_schema

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
CRITICAL OUTPUT REQUIREMENTS

Your final answer MUST be a raw JSON array.

Example:
[
  {
    "workshop_id": 1,
    "workshop_name": "ABC Workshop"
  }
]

STRICTLY FORBIDDEN in your final answer:
- Explanations
- Summaries
- Markdown
- Code blocks or ```json fences
- CSV
- Instructions or preamble text
- Any text before the opening [
- Any text after the closing ]

If data exists: Return JSON array only.
If no rows exist: Return []
Never return anything except a JSON array.

FAST-TRACK EXPORT RULE:
If you successfully call execute_query, DO NOT copy or output the database records in your final AI response. Instead, simply stop and return the exact text 'EXPORT_SUCCESS'. The backend will retrieve the full data from the query cache.

SCHEMA SAFETY RULE
You may ONLY use tables and columns returned by get_schema.
ENUM CASING RULE: The database contains case-sensitive enum types. When writing WHERE filters on these columns, you MUST use the exact Title Case:
- status_enum (workshop_status, license_status, profile_status): 'Pending', 'Under Review', 'Approved', 'Rejected', 'Suspended', 'Expired'
- payment_status_enum (payment_status): 'Pending', 'Paid', 'Failed', 'Refunded'
- test_result_enum (test_result): 'Pass', 'Fail', 'Conditional Pass'
- fuel_type_enum (fuel_type): 'Petrol', 'Diesel', 'CNG', 'Hybrid', 'Electric'
- transmission_enum (transmission): 'Manual', 'Automatic', 'CVT', 'AMT'
Using lowercase (like 'approved', 'paid', 'pass') will cause PostgreSQL to throw an error!
ENUM NO-CAST RULE: NEVER use explicit type casting (::text, ::varchar) when comparing enum columns.
  CORRECT:   WHERE payment_status = 'Failed'
  INCORRECT: WHERE payment_status = 'Failed'::text  <- this breaks the enum operator!
SELECT DISTINCT ORDER BY RULE: When using SELECT DISTINCT, every column in the ORDER BY clause MUST also appear in the SELECT list.
Never invent tables, views, columns, or relationships.
If information is unavailable, return only available fields.
Do not guess.

OWNER DATA RULE
Do not assume an owners table exists.
Before using owner, owners, owner_details, or workshop_owners — verify via get_schema.
If absent, use only workshop_owner_name from the workshops table.

Steps to follow:
1. Check schema if needed (call get_schema)
2. Verify every table and column exists before querying
3. Run execute_query with a SELECT statement
4. Return the rows as a raw JSON array — nothing else.\
"""

ExportAgent = Any


def build_export_agent() -> ExportAgent:
    """
    Build and return the Export agent graph.
    Called once at startup and reused for all export-intent requests.
    """
    llm = build_llm(temperature=0.0)
    tools = [execute_query, get_schema]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=_SYSTEM_PROMPT),
    )

    logger.info("Export agent ready.")
    return agent


def run_export_agent(agent: ExportAgent, chat_input: str) -> str:
    """
    Invoke the export agent and return the raw JSON array string.

    Parameters
    ----------
    agent      : The compiled graph returned by build_export_agent().
    chat_input : Sanitised user message.

    Returns
    -------
    A string that should parse as a JSON array.
    The export handler is responsible for further parsing and validation.
    """
    import json
    import uuid
    import datetime
    from decimal import Decimal
    from tools.postgres_tool import get_cached_result

    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    cache_key = str(uuid.uuid4())

    result = agent.invoke(
        {"messages": [("user", f"User request: {chat_input}")]},
        config={
            "recursion_limit": 16,  # 4 agent steps × ~4 graph nodes each
            "configurable": {"export_cache_key": cache_key}
        },
    )
    
    # Check messages in reverse for the last successful execute_query ToolMessage.
    # If found, return the full cached query results instead of the truncated preview from msg.content.
    from langchain_core.messages import ToolMessage
    for msg in reversed(result.get("messages", [])):
        if msg.type == "tool" or isinstance(msg, ToolMessage):
            if getattr(msg, "name", "") == "execute_query":
                cached_results = get_cached_result(cache_key)
                logger.info(
                    "Intercepted execute_query ToolMessage. Returning full cached dataset (%d rows).",
                    len(cached_results)
                )
                return json.dumps(cached_results, default=json_serial)

    final_message = result["messages"][-1]
    return getattr(final_message, "content", str(final_message)).strip() or "[]"
