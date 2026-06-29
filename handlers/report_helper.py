"""
handlers/report_helper.py
─────────────────────────
Helper utilities to normalize, filter, and structure raw JSON query results
for PDF and PowerPoint document export tables.
"""

from typing import Any

# Core fields we want to show, in order of preference.
# Limiting to a maximum of 6 columns keeps the PDF and PPTX tables legible.
_PREFERRED_COLS = [
    # Identity
    "workshop_name", "full_name", "workshop_code", "license_number", 
    # Location
    "city", "district",
    # Status / Outcomes
    "workshop_status", "license_status", "payment_status", "test_result", "inspection_result",
    # Metrics
    "fee_amount", "total_score",
    # Dates
    "payment_date", "valid_until", "test_date", "inspection_date", "created_at"
]

# Field aliases for cleaner headers
_FIELD_ALIASES = {
    "workshop_name": "Workshop Name",
    "full_name": "Applicant Name",
    "workshop_code": "Code",
    "license_number": "License No",
    "workshop_status": "Status",
    "license_status": "License Status",
    "payment_status": "Payment Status",
    "test_result": "Test Result",
    "inspection_result": "Inspection",
    "fee_amount": "Fee (PKR)",
    "total_score": "Score",
    "city": "City",
    "district": "District",
    "payment_date": "Date",
    "valid_until": "Valid Until",
    "test_date": "Test Date",
    "inspection_date": "Inspection Date",
    "created_at": "Created",
    "father_name": "Father's Name",
    "workshop_owner_name": "Owner Name",
    "owner_profile_full_name": "Owner Name",
    "system_username": "Username",
    "total_uploaded_documents": "Docs",
    "license_category": "Category",
    "payment_mode": "Pay Mode",
    "rta_inspection_total_score": "RTA Score",
    "total_emission_tests": "Tests",
    "total_vehicles_tested": "Vehicles",
    "notes": "Latest Activity",
}


def _snake_to_title(key: str) -> str:
    """Fallback: Convert snake_case key to clean Title Case."""
    return key.replace("_", " ").title()


def determine_export_title(records: list[dict]) -> str:
    """Guess a clean dataset description based on the fields present."""
    if not records:
        return "Data Export"

    keys = records[0].keys()
    if any(k in keys for k in ["license_number", "license_id"]):
        return "Licenses Report"
    elif any(k in keys for k in ["fee_amount", "challan_no", "psid_number"]):
        return "Payments & Financials"
    elif any(k in keys for k in ["test_result", "co_pct", "co2_pct"]):
        return "Emission Tests Log"
    elif any(k in keys for k in ["inspection_result", "total_score"]):
        return "RTA Inspections Log"
    elif any(k in keys for k in ["workshop_name", "workshop_code"]):
        return "Workshops Register"
    return "Custom Search Export"


def normalize_data_for_export(records: list[dict]) -> tuple[list[str], list[list[str]]]:
    """
    Filter all keys in records to include only core display columns (max 6),
    normalize column headers, and format values as clean strings.

    Returns
    -------
    Tuple: (headers_list, rows_list)
    """
    if not records:
        return [], []

    # Get all keys present in the first record
    keys = list(records[0].keys())

    # If the database returns 15 or fewer columns (i.e. a specific lookup query),
    # preserve all of them so we do not strip explicitly requested fields.
    if len(keys) <= 15:
        display_cols = keys
    else:
        # Otherwise (e.g. SELECT *), pick the best 8 columns from our preferred list.
        # If preferred columns are present and represent a substantial part of the result,
        # use them; otherwise, default to the query's direct SELECT order.
        preferred_in_keys = [col for col in keys if col in _PREFERRED_COLS]
        if len(preferred_in_keys) >= 4:
            display_cols = preferred_in_keys[:8]
        else:
            display_cols = keys[:8]

    # Generate headers using aliases or fallback Title Case conversion
    headers = [_FIELD_ALIASES.get(col, _snake_to_title(col)) for col in display_cols]

    # Format values in rows as strings
    rows = []
    for r in records:
        row = []
        for col in display_cols:
            val = r.get(col, "")
            # Clean up boolean or None strings
            if val is None:
                val = "—"
            elif isinstance(val, bool):
                val = "Yes" if val else "No"
            row.append(str(val))
        rows.append(row)

    return headers, rows


def is_kpi_request(chat_input: str) -> bool:
    """
    Check if the user is asking for the global KPI dashboard vs a specific dataset query.
    """
    text = chat_input.lower()
    
    # If the user asks for workshops of X, active Y, etc., it's a dynamic dataset query
    query_keywords = ["of", "in", "where", "active", "expired", "pending", "rejected", "satisfactory", "conditional", "fail"]
    has_query_kw = any(kw in text for kw in query_keywords)

    # If it contains "kpi" or "dashboard" or "overview" and has no query keywords, it's a KPI dashboard
    if any(k in text for k in ["kpi", "dashboard", "overview", "statistics", "analytics"]) and not has_query_kw:
        return True

    # Default to true only if no database entities are mentioned in the prompt
    entities = ["workshop", "license", "payment", "fee", "inspection", "test", "vehicle", "applicant", "profile", "user"]
    has_entity = any(e in text for e in entities)
    if not has_entity:
        return True

    return False


def clean_prompt_for_export(prompt: str) -> str:
    """
    Remove file format commands (e.g. 'convert to pdf', 'convert them into pptx')
    to prevent prompt contamination from confusing the export agent.
    """
    import re
    cleaned = prompt
    patterns = [
        r"\b(?:and\s+)?convert\s+(?:them\s+)?into\s+(?:pdf|pptx|powerpoint|slides|sheet|google\s+sheet)\b",
        r"\b(?:and\s+)?convert\s+(?:them\s+)?to\s+(?:pdf|pptx|powerpoint|slides|sheet|google\s+sheet)\b",
        r"\b(?:and\s+)?generate\s+(?:a\s+)?(?:pdf|pptx|powerpoint|slides|report|sheet)\b",
        r"\b(?:and\s+)?export\s+(?:them\s+)?to\s+(?:pdf|pptx|powerpoint|slides|sheet|google\s+sheet)\b",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Strip any trailing 'and', 'then', commas or whitespace
    cleaned = re.sub(r"\b(?:and|then|to|into)\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


