"""
config.py
─────────
Central configuration module. Reads all settings from environment variables
(loaded from a .env file via python-dotenv). Import this module anywhere you
need a config value — never hard-code credentials in other files.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── LLM Provider ─────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

# Google Gemini
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Mistral
MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

# ── PostgreSQL ────────────────────────────────────────────────────────────────
DB_URL: str = os.getenv("DB_URL", "")

# ── Google Sheets ─────────────────────────────────────────────────────────────
SHEETS_ID: str = os.getenv("SHEETS_ID", "")
SHEETS_TAB: str = os.getenv("SHEETS_TAB", "details")

# Auth — service account takes priority over OAuth
GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
GOOGLE_OAUTH_CREDENTIALS_FILE: str = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE", "")
GOOGLE_OAUTH_TOKEN_FILE: str = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json")

# ── Exports directory (generated PPTX / PDF files) ──────────────────────────
EXPORTS_DIR: str = os.getenv(
    "EXPORTS_DIR",
    str(Path(__file__).parent / "exports"),  # default: <project>/exports/
)

# ── Interface ─────────────────────────────────────────────────────────────────
INTERFACE: str = os.getenv("INTERFACE", "cli").lower()   # "cli" | "api"
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ── Session Memory ────────────────────────────────────────────────────────────
SESSION_MEMORY: bool = os.getenv("SESSION_MEMORY", "false").lower() == "true"

# ── Validation helper ─────────────────────────────────────────────────────────

def validate() -> None:
    """
    Check that mandatory settings are present and log warnings for optional
    ones that are missing. Call this once at startup.
    """
    errors: list[str] = []

    if not DB_URL:
        errors.append("DB_URL is not set — PostgreSQL queries will fail.")

    if LLM_PROVIDER == "mistral" and not MISTRAL_API_KEY:
        errors.append("MISTRAL_API_KEY is not set but LLM_PROVIDER=mistral.")
    elif LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is not set but LLM_PROVIDER=gemini.")
    elif LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set but LLM_PROVIDER=openai.")

    if not SHEETS_ID:
        logger.warning("SHEETS_ID is not set — Google Sheets export will be disabled.")

    sheets_auth_available = bool(
        GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_OAUTH_CREDENTIALS_FILE
    )
    if SHEETS_ID and not sheets_auth_available:
        logger.warning(
            "SHEETS_ID is set but no Google auth file found. "
            "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_OAUTH_CREDENTIALS_FILE."
        )

    if errors:
        for msg in errors:
            logger.error("Config error: %s", msg)
        raise EnvironmentError(
            "Configuration errors found:\n" + "\n".join(f"  • {e}" for e in errors)
        )

    logger.info(
        "Config loaded — LLM=%s | Interface=%s | Memory=%s",
        LLM_PROVIDER.upper(),
        INTERFACE.upper(),
        SESSION_MEMORY,
    )
