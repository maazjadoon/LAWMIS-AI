"""
handlers/static_replies.py
──────────────────────────
All pre-written, canned reply strings.

Mirrors the following n8n Code nodes:
  • "Empty Input Reply"
  • "Unsupported Action"
  • "KPI Error Reply"
  • "Query Error Reply"
  • "Export Error Reply"
  • "Sheets Error Reply"
  • "Export Success Reply"
  • (implicit) PDF stub
  • (implicit) PPTX stub

Keeping every hard-coded string in one place makes them easy to edit
without touching agent or handler logic.
"""


def empty_input_reply() -> str:
    """Returned when the user sends a blank message."""
    return (
        "I didn't catch a message there — could you type your question again? "
        'For example: "show me all active workshops in Lahore", '
        '"export licensed workshops to sheet", or "show KPI dashboard".'
    )


def unsupported_action_reply() -> str:
    """Returned for update / delete / remove / insert intents."""
    return (
        "I'm currently set up for read-only queries, KPI dashboards, and Google "
        "Sheets exports. Update and delete operations aren't enabled in this chat "
        "interface for safety. If you need to change data, please use the LAWMIS "
        "admin panel directly."
    )


def pdf_stub_reply() -> str:
    """Returned when the user asks for a PDF report (not yet implemented)."""
    return (
        "📄 PDF report generation is coming soon! "
        "For now, try exporting data to Google Sheets or asking for a KPI dashboard. "
        'For example: "export all active workshops to sheet" or "show KPI dashboard".'
    )


def pptx_stub_reply() -> str:
    """Returned when the user asks for a PowerPoint presentation (not yet implemented)."""
    return (
        "📊 PowerPoint / PPTX generation is coming soon! "
        "For now, you can view the KPI dashboard directly in chat or export data "
        'to Google Sheets. For example: "show KPI dashboard" or '
        '"export licensed workshops to sheet".'
    )


def query_error_reply(error: str | Exception) -> str:
    """Returned when the Query agent raises an exception."""
    err_msg = str(error)
    return (
        f"Sorry, I ran into a problem looking that up ({err_msg}). "
        "Could you try rephrasing your question?"
    )


def kpi_error_reply(error: str | Exception) -> str:
    """Returned when the KPI agent raises an exception."""
    err_msg = str(error)
    return (
        f"I couldn't load the KPI dashboard ({err_msg}). "
        "Try asking again or narrow the request — for example: "
        '"show workshop KPIs" or "give me emission test statistics".'
    )


def export_agent_error_reply(error: str | Exception) -> str:
    """Returned when the Export agent raises an exception."""
    err_msg = str(error)
    return (
        f"I couldn't complete that export — the data agent ran into an issue "
        f"({err_msg}). Try rephrasing the request or narrowing the result set."
    )


def sheets_error_reply(error: str | Exception) -> str:
    """Returned when Google Sheets append fails after the agent succeeds."""
    err_msg = str(error)
    return (
        f"I fetched the data but couldn't write it to the Google Sheet ({err_msg}). "
        "Please check that the sheet is accessible and try again."
    )


def export_success_reply(count: int) -> str:
    """Returned after a successful Google Sheets append."""
    record_word = "record" if count == 1 else "records"
    return (
        f"Done — {count} {record_word} appended to the Google Sheet "
        '"N8N DB EXPORT" (tab: details).'
    )
