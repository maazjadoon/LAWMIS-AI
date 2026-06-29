"""
sheets/google_sheets.py
───────────────────────
Mirrors the n8n "Google Sheets Append" node.

Appends a list of row-dicts to the configured Google Sheet.
Supports two authentication methods (configured in .env):
  1. Service Account JSON file  (GOOGLE_SERVICE_ACCOUNT_FILE)  — recommended
  2. OAuth2 credentials         (GOOGLE_OAUTH_CREDENTIALS_FILE) — personal use

The sheet ID and tab name are read from config.SHEETS_ID / config.SHEETS_TAB.

Retry behaviour: gspread has built-in exponential backoff for quota errors.
We add a simple 3-attempt retry at the row-append level to mirror n8n's
retryOnFail=true, maxTries=3, waitBetweenTries=2000ms settings.
"""

import logging
import time
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)

# Retry settings (mirrors n8n retryOnFail=true, maxTries=3, waitBetweenTries=2000ms)
_MAX_TRIES = 3
_RETRY_DELAY = 2.0  # seconds


def _get_gspread_client():
    """
    Authenticate and return an authorised gspread Client.
    Tries service account first, then OAuth2.
    """
    import gspread

    sa_file = config.GOOGLE_SERVICE_ACCOUNT_FILE
    oauth_creds_file = config.GOOGLE_OAUTH_CREDENTIALS_FILE
    oauth_token_file = config.GOOGLE_OAUTH_TOKEN_FILE

    if sa_file and Path(sa_file).exists():
        logger.debug("Authenticating with service account: %s", sa_file)
        return gspread.service_account(filename=sa_file)

    if oauth_creds_file and Path(oauth_creds_file).exists():
        logger.debug("Authenticating with OAuth2 credentials: %s", oauth_creds_file)
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = None

        if Path(oauth_token_file).exists():
            creds = Credentials.from_authorized_user_file(oauth_token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    oauth_creds_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the token for next time
            Path(oauth_token_file).write_text(creds.to_json())

        return gspread.authorize(creds)

    raise RuntimeError(
        "No Google authentication found. Set GOOGLE_SERVICE_ACCOUNT_FILE "
        "or GOOGLE_OAUTH_CREDENTIALS_FILE in your .env file."
    )


def append_rows(rows: list[dict[str, Any]]) -> None:
    """
    Append a list of row-dicts to the configured Google Sheet.

    Column headers are taken from the keys of the first row dict.
    If the sheet is empty, a header row is written first.

    Parameters
    ----------
    rows : List of dicts where keys are column names (already normalised by
           the export handler).

    Raises
    ------
    RuntimeError  If the sheet is not found or auth fails.
    Exception     Propagated from gspread after all retries are exhausted.
    """
    if not config.SHEETS_ID:
        raise RuntimeError(
            "SHEETS_ID is not configured. Set it in your .env file."
        )

    if not rows:
        logger.warning("append_rows called with empty list — nothing to append.")
        return

    # Build the 2-D array expected by gspread.append_rows
    headers = list(rows[0].keys())

    # Retry loop wraps the ENTIRE operation (open sheet + read + append)
    # so transient auth/network failures are all retried.
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_TRIES + 1):
        try:
            client = _get_gspread_client()
            spreadsheet = client.open_by_key(config.SHEETS_ID)
            worksheet = spreadsheet.worksheet(config.SHEETS_TAB)

            matrix: list[list] = []
            existing = worksheet.get_all_values()
            if not existing:
                matrix.append(headers)   # write header row if sheet is empty

            for row_dict in rows:
                matrix.append([str(row_dict.get(h, "")) for h in headers])

            worksheet.append_rows(
                matrix,
                value_input_option="USER_ENTERED",
                insert_data_option="INSERT_ROWS",
            )
            logger.info(
                "Appended %d data row(s) to sheet '%s' tab '%s'.",
                len(rows),
                config.SHEETS_ID,
                config.SHEETS_TAB,
            )
            return  # success

        except Exception as exc:
            last_exc = exc
            # Log full type + repr so empty .str() messages are never swallowed
            logger.warning(
                "Sheets append attempt %d/%d failed [%s]: %r",
                attempt, _MAX_TRIES,
                type(exc).__name__,
                exc,
            )
            if attempt < _MAX_TRIES:
                time.sleep(_RETRY_DELAY)

    # Build a descriptive error string from the last exception
    err_detail = repr(last_exc) if not str(last_exc).strip() else str(last_exc)
    raise RuntimeError(
        f"Google Sheets append failed after {_MAX_TRIES} attempts "
        f"[{type(last_exc).__name__}]: {err_detail}"
    ) from last_exc
