"""
tools/schema_tool.py
────────────────────
Mirrors the n8n "get_schema - Query / KPI / Export" nodes.

Exposes a single LangChain @tool that queries information_schema.columns to
let the LLM agent verify real column names before writing SQL.

Usage patterns the LLM can use:
  get_schema("workshops")               → columns for one table
  get_schema("workshops, payments")     → columns for multiple tables
  get_schema("all")                     → every table in the public schema
"""

import logging
import re
from typing import Any

import psycopg2
import psycopg2.extras
from langchain_core.tools import tool

import config

logger = logging.getLogger(__name__)

# Only allow safe characters in table name input to prevent injection
_SAFE_IDENTIFIER = re.compile(r"^[a-z0-9_,\s]+$", re.IGNORECASE)


def _get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(config.DB_URL)


@tool
def get_schema(table_name: str) -> list[dict[str, Any]]:
    """
    Look up the real column names and data types for one or more tables in the
    public schema.

    Use this whenever you are unsure whether a column exists, or after receiving
    a 'column does not exist' SQL error — call get_schema BEFORE retrying.

    Input options:
    - A single table name:          "workshops"
    - Comma-separated table names:  "workshops, payments"
    - The literal string "all":     returns every table and column in the schema
    """
    cleaned = table_name.strip().lower()

    # ── Safety: reject anything that looks like injection ────────────────────
    if not _SAFE_IDENTIFIER.match(cleaned):
        raise ValueError(
            f"Invalid table_name '{table_name}'. "
            "Use only letters, digits, underscores, commas, and spaces."
        )

    if cleaned == "all":
        sql = (
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "ORDER BY table_name, ordinal_position;"
        )
        params: tuple = ()
    else:
        # Parse comma-separated table names
        names = [n.strip() for n in cleaned.split(",") if n.strip()]
        # Use ANY(ARRAY[...]) for clean parameterisation
        sql = (
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name = ANY(%s) "
            "ORDER BY table_name, ordinal_position;"
        )
        params = (names,)

    try:
        with _get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                results = [dict(row) for row in rows]

        logger.info(
            "get_schema(%r) → %d columns returned.", table_name, len(results)
        )
        return results

    except psycopg2.Error as exc:
        logger.error("Schema lookup error: %s", exc)
        raise RuntimeError(f"Schema lookup failed: {exc.pgerror or str(exc)}") from exc
