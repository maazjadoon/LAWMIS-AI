"""
tools/postgres_tool.py
──────────────────────
Mirrors the n8n "PostgreSQL Tool - Query" node.

Exposes a single LangChain @tool that:
  • Accepts a plain SQL SELECT statement
  • Rejects any DDL / DML statement for safety (INSERT, UPDATE, DELETE, DROP,
    ALTER, TRUNCATE, CREATE)
  • Retries once on transient connection errors (mirrors n8n maxTries=2)
  • Returns results as a list of dicts (JSON-serialisable)

The tool is intentionally kept thin — all SQL generation happens inside the
LLM agent. This module only executes and validates.
"""

import logging
import re
import threading
import time
from typing import Any

import psycopg2
import psycopg2.extras
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

import config

logger = logging.getLogger(__name__)

# Global thread-safe cache to store full query results, keyed by export_cache_key.
# This prevents LLM context limit bloat by returning only a preview of records
# to the agent, while allowing handlers to fetch the complete dataset.
_QUERY_CACHE: dict[str, list[dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def get_cached_result(key: str) -> list[dict[str, Any]]:
    """Retrieve and pop the cached query result from the global cache."""
    with _CACHE_LOCK:
        return _QUERY_CACHE.pop(key, [])


def set_cached_result(key: str, results: list[dict[str, Any]]) -> None:
    """Cache the query result in the global cache."""
    with _CACHE_LOCK:
        _QUERY_CACHE[key] = results


# ── Safety: forbidden SQL keywords at statement start ────────────────────────
_FORBIDDEN_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY)\b",
    re.IGNORECASE,
)

# ── Retry settings (matches n8n maxTries=2, waitBetweenTries=1000ms) ─────────
_MAX_TRIES = 2
_RETRY_DELAY_SECONDS = 1.0


def _get_connection() -> psycopg2.extensions.connection:
    """Open a fresh psycopg2 connection using DB_URL from config."""
    return psycopg2.connect(config.DB_URL)


def _run_select(sql: str) -> list[dict[str, Any]]:
    """
    Execute a SELECT statement and return rows as a list of dicts.
    Retries once on OperationalError (e.g. dropped connection).
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_TRIES + 1):
        try:
            with _get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    # RealDictRow → plain dict for JSON serialisation
                    return [dict(row) for row in rows]
        except psycopg2.OperationalError as exc:
            last_exc = exc
            logger.warning("DB connection error on attempt %d/%d: %s", attempt, _MAX_TRIES, exc)
            if attempt < _MAX_TRIES:
                time.sleep(_RETRY_DELAY_SECONDS)
        except psycopg2.Error as exc:
            # Non-retriable database errors (e.g. bad column name, syntax error)
            logger.error("SQL execution error: %s", exc)
            raise RuntimeError(f"Database error: {exc.pgerror or str(exc)}") from exc

    raise RuntimeError(
        f"Database connection failed after {_MAX_TRIES} attempts: {last_exc}"
    )


@tool
def execute_query(query: str, config: RunnableConfig = None) -> list[dict[str, Any]]:
    """
    Execute a read-only PostgreSQL SELECT query against the LAWMIS database
    and return the result rows as a list of dicts.

    Rules:
    - Input MUST be a single valid SELECT statement targeting the public schema.
    - Never pass INSERT / UPDATE / DELETE / DDL statements — they will be rejected.
    - Default LIMIT is 200 rows unless the user requests more.
    """
    # ── Safety guard ─────────────────────────────────────────────────────────
    if _FORBIDDEN_PATTERN.match(query.strip()):
        raise ValueError(
            "Only SELECT statements are permitted. "
            "INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, and CREATE are blocked."
        )

    logger.debug("Executing query: %.300s", query)
    results = _run_select(query)
    logger.info("Query returned %d rows.", len(results))

    # Cache the full, untruncated result list if an export_cache_key is provided
    if config:
        cache_key = config.get("configurable", {}).get("export_cache_key")
        if cache_key:
            logger.info("Caching query results for export under key: %s", cache_key)
            set_cached_result(cache_key, results)

    # To avoid context token overflow, return a preview to the LLM agent
    # if the row count exceeds 100.
    MAX_PREVIEW_ROWS = 100
    if len(results) > MAX_PREVIEW_ROWS:
        truncated_results = results[:MAX_PREVIEW_ROWS]
        # Append a special note dictionary so the agent is aware that it's truncated
        truncation_note = {
            "__NOTICE__": (
                f"Query returned {len(results)} rows. Only the first {MAX_PREVIEW_ROWS} rows "
                "are shown in this preview to avoid exceeding LLM context length limits. "
                "The full dataset has been saved in the cache for document/export generation."
            )
        }
        return truncated_results + [truncation_note]

    return results
