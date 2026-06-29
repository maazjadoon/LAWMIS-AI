"""
handlers/export_handler.py
──────────────────────────
Mirrors the n8n "Split Records & Normalize" Code node + the Google Sheets
append + success/error reply nodes combined.

Pipeline:
  1. Call the Export agent → get raw JSON array string
  2. Parse and validate the JSON (with aggressive stripping of markdown fences
     and leading/trailing prose — same logic as the n8n extractor function)
  3. Normalise column names (snake_case → Title Case with friendly aliases)
  4. Append rows to Google Sheets via sheets.google_sheets
  5. Return a success or error reply string

All Google Sheets logic is delegated to sheets/google_sheets.py so this
module stays focussed on data transformation.
"""

import json
import logging
import re
from typing import Any


from agents.export_agent import run_export_agent
from handlers.static_replies import (
    export_agent_error_reply,
    export_success_reply,
    sheets_error_reply,
)

logger = logging.getLogger(__name__)

# ── Friendly column-name aliases (mirrors n8n keyMap) ────────────────────────
_KEY_MAP: dict[str, str] = {
    "workshop_owner_name": "Owner Name",
    "workshop_phone": "Phone",
    "workshop_name": "Workshop Name",
    "workshop_id": "Workshop ID",
    "workshop_code": "Code",
    "workshop_status": "Status",
    "city": "City",
    "license_status": "License Status",
    "valid_until": "Valid Until",
    "payment_status": "Payment Status",
    "fee_amount": "Fee Amount",
    "full_name": "Full Name",
    "cnic_number": "CNIC",
    "phone_primary": "Phone",
    "profile_status": "Profile Status",
    "test_result": "Test Result",
    "certificate_no": "Certificate No",
    "test_date": "Test Date",
    "inspection_result": "Inspection Result",
    "total_score": "Total Score",
    "inspection_date": "Inspection Date",
    "created_at": "Created At",
    "workshop_email": "Email",
    "district": "District",
    "province": "Province",
}


def _snake_to_title(key: str) -> str:
    """Convert snake_case to Title Case: 'number_of_bays' → 'Number Of Bays'."""
    return key.replace("_", " ").title()


def _extract_json(raw: Any) -> list[dict]:
    """
    Parse raw agent output into a list of dicts.

    Handles:
      • Already-parsed list or dict
      • Strings with ```json fences
      • Strings with leading prose before the first '[' or '{'
      • Strings with trailing prose after the last ']' or '}'
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]

    s = str(raw).strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    s = re.sub(r"^\s*```(?:json|javascript|js)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    s = s.strip()

    # Find the first JSON-start character
    starts = [i for i in (s.find("["), s.find("{")) if i != -1]
    if starts:
        s = s[min(starts):]

    # Trim trailing prose after the last ] or }
    last = max(s.rfind("]"), s.rfind("}"))
    if last != -1 and last < len(s) - 1:
        s = s[: last + 1]

    return json.loads(s)


def _normalize_records(data_list: list[dict]) -> list[dict]:
    """
    Apply the friendly alias map to each record's keys, falling back to
    Title Case for unmapped keys. Returns a new list of normalised dicts.
    """
    normalised: list[dict] = []
    for record in data_list:
        if not isinstance(record, dict):
            continue
        new_record = {
            _KEY_MAP.get(k, _snake_to_title(k)): v for k, v in record.items()
        }
        normalised.append(new_record)
    return normalised


def handle_export(agent: Any, chat_input: str) -> str:
    """
    Full export pipeline: agent → parse → normalise → Google Sheets → reply.

    Parameters
    ----------
    agent      : Compiled LangGraph agent from build_export_agent().
    chat_input : Sanitised user message.

    Returns
    -------
    A user-facing reply string (success count or error message).
    """
    # ── Step 1: Run the export agent ─────────────────────────────────────────
    try:
        raw_output = run_export_agent(agent, chat_input)
    except Exception as exc:
        logger.error("Export agent failed: %s", exc)
        return export_agent_error_reply(exc)

    # ── Step 2: Parse JSON ────────────────────────────────────────────────────
    try:
        data_list = _extract_json(raw_output)
    except (json.JSONDecodeError, ValueError) as exc:
        preview = str(raw_output)[:300]
        msg = (
            f"Export failed: agent did not return parseable JSON. "
            f"Parse error: {exc}. Raw output started with: {preview}"
        )
        logger.error(msg)
        return export_agent_error_reply(msg)

    if not isinstance(data_list, list):
        data_list = [data_list]

    # ── Step 3: Normalise column names ────────────────────────────────────────
    rows = _normalize_records(data_list)

    if not rows:
        return export_agent_error_reply(
            "Export produced zero usable records after parsing — nothing to append."
        )

    # ── Step 4: Append to Google Sheets ──────────────────────────────────────
    try:
        from sheets.google_sheets import append_rows
        append_rows(rows)
    except Exception as exc:
        logger.error("Google Sheets append failed: %s", exc)
        return sheets_error_reply(exc)

    # ── Step 5: Return success reply ──────────────────────────────────────────
    logger.info("Export complete — %d rows appended.", len(rows))
    return export_success_reply(len(rows))
