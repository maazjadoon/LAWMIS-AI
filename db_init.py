"""
db_init.py
──────────
Auto-initialises the LAWMIS database schema if the tables don't exist yet.

Called once at application startup (from main.py before the FastAPI app starts).
Safe to run on every restart — all statements use IF NOT EXISTS.
Works on:
  - Local Docker  (init.sql already handled by Postgres entrypoint, but this is harmless)
  - Railway       (no entrypoint hook — this is the only way to initialise the schema)
  - Any hosted PostgreSQL (Supabase, Neon, Render, etc.)
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def init_db(db_url: str) -> None:
    """
    Run db/init.sql against the connected database if the 'workshops' table
    does not exist yet. No-ops if schema is already present.
    """
    if not db_url:
        logger.warning("db_init: DB_URL is empty — skipping schema initialisation.")
        return

    sql_path = Path(__file__).parent / "db" / "init.sql"
    if not sql_path.exists():
        logger.warning("db_init: %s not found — skipping schema initialisation.", sql_path)
        return

    try:
        import psycopg2

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Check if schema already exists
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='workshops');"
                )
                already_exists = cur.fetchone()[0]

            if already_exists:
                logger.info("db_init: Schema already present — skipping.")
                return

            # Schema not found — run init.sql
            logger.info("db_init: Running schema initialisation from %s …", sql_path)
            sql = sql_path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            logger.info("db_init: Schema initialised successfully.")

    except Exception as exc:  # noqa: BLE001
        logger.error("db_init: Failed to initialise schema: %s", exc)
        # Don't crash the app — the error will surface naturally when queries run
