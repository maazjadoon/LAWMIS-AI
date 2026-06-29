"""
main.py
───────
Entry-point for the LAWMIS LangChain Assistant.

Wires together every module in the correct order and exposes two interfaces:

  CLI mode  (INTERFACE=cli)
    • Interactive REPL loop in the terminal
    • Type a message, get a reply, repeat
    • Type "exit" or "quit" to stop

  API mode  (INTERFACE=api)
    • FastAPI application with a single POST /chat endpoint
    • Request body:  {"message": "...", "session_id": "optional-uuid"}
    • Response body: {"reply": "..."}
    • Run with:  uvicorn main:app --host 0.0.0.0 --port 8000

Full flow (mirrors the n8n workflow exactly):
  Chat Input
    → Sanitizer          (clean, truncate, log)
    → Empty check        (return canned reply if blank)
    → Intent Router      (keyword → export / kpi / update_delete / pdf / pptx / query)
    → Branch handler     (call appropriate agent or return stub reply)
    → Final reply        (string returned to the user / HTTP response)
"""

import logging
import sys

import config

# ── Validate environment before importing anything that needs credentials ──────
# This will raise EnvironmentError early if required vars are missing.
config.validate()

logger = logging.getLogger(__name__)

# ── Import application modules ─────────────────────────────────────────────────
from sanitizer import sanitize
from router import detect_intent
from agents.query_agent import build_query_agent
from agents.kpi_agent import build_kpi_agent
from agents.export_agent import build_export_agent
from agents.document_agent import build_document_agent
from handlers.query_handler import handle_query
from handlers.kpi_handler import handle_kpi
from handlers.export_handler import handle_export
from handlers.pptx_handler import handle_pptx
from handlers.pdf_handler import handle_pdf
from handlers.document_handler import handle_document
from handlers.static_replies import (
    empty_input_reply,
    unsupported_action_reply,
)

# ── Build agents once at startup (expensive: model + tool wiring) ──────────────
logger.info("Initialising agents…")
_query_executor = build_query_agent()
_kpi_executor = build_kpi_agent()
_export_executor = build_export_agent()
_document_llm = build_document_agent()
logger.info("All agents ready.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Core dispatch function
# ═══════════════════════════════════════════════════════════════════════════════

def process_message(raw_input: str, session_id: str | None = None) -> str:
    """
    Process a single user message through the full pipeline.

    This is the canonical function called by both CLI and API interfaces.

    Parameters
    ----------
    raw_input  : The raw string typed / sent by the user.
    session_id : Optional existing session UUID. A new one is created if None.

    Returns
    -------
    A reply string ready to display to the user.
    """
    # ── Step 1: Sanitize ───────────────────────────────────────────────────────
    sanitized = sanitize(raw_input, session_id)
    chat_input: str = sanitized["chatInput"]
    sid: str = sanitized["sessionId"]

    logger.debug("session=%s intent_input=%r", sid, chat_input[:80])

    # ── Step 2: Empty-input guard ─────────────────────────────────────────────
    if sanitized["isEmpty"]:
        logger.info("session=%s → empty input", sid)
        return empty_input_reply()

    # ── Step 3: Detect intent ─────────────────────────────────────────────────
    intent = detect_intent(chat_input)
    logger.info("session=%s intent=%s", sid, intent)

    # ── Step 4: Route to the correct handler ──────────────────────────────────
    match intent:
        case "export":
            return handle_export(_export_executor, chat_input)

        case "update_delete":
            return unsupported_action_reply()

        case "kpi":
            return handle_kpi(_kpi_executor, chat_input)

        case "pdf":
            return handle_pdf(_export_executor, chat_input)

        case "pptx":
            return handle_pptx(_export_executor, chat_input)

        case "document":
            return handle_document(_document_llm, chat_input)

        case "query" | _:
            return handle_query(_query_executor, chat_input)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI interface
# ═══════════════════════════════════════════════════════════════════════════════

def run_cli() -> None:
    """
    Interactive terminal REPL.
    Type a message and press Enter to get a response.
    Type 'exit' or 'quit' to stop.
    """
    print("\n" + "=" * 60)
    print("  LAWMIS Assistant  (CLI mode)")
    print("  Ask about workshops, licenses, payments, KPIs,")
    print("  or export data to Google Sheets.")
    print("  Type 'exit' to quit.")
    print("=" * 60 + "\n")

    session_id: str | None = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        reply = process_message(user_input, session_id)
        print(f"\nAssistant:\n{reply}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  FastAPI interface
# ═══════════════════════════════════════════════════════════════════════════════

def _build_fastapi_app():
    """
    Build and return the FastAPI application.
    Only called when INTERFACE=api to avoid importing FastAPI in CLI mode.
    """
    from fastapi import FastAPI, HTTPException, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from pathlib import Path
    import shutil

    app = FastAPI(
        title="LAWMIS Assistant API",
        description=(
            "Natural-language interface for the LAWMIS workshop licensing system. "
            "Ask about workshops, licenses, payments, KPIs, or export data to Sheets."
        ),
        version="1.0.0",
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static exports directory to serve PDF/PPTX reports
    app.mount("/exports", StaticFiles(directory=config.EXPORTS_DIR), name="exports")

    class ChatRequest(BaseModel):
        message: str
        session_id: str | None = None

    class ChatResponse(BaseModel):
        reply: str

    @app.post("/chat", response_model=ChatResponse, summary="Send a chat message")
    async def chat(request: ChatRequest) -> ChatResponse:
        """
        Send a natural-language message and receive a reply.

        - **message**: The user's question or command
        - **session_id**: Optional session UUID for conversation tracking
        """
        if not request.message.strip():
            return ChatResponse(reply=empty_input_reply())

        try:
            reply = process_message(request.message, request.session_id)
            return ChatResponse(reply=reply)
        except Exception as exc:
            logger.error("Unhandled error in /chat: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/upload", summary="Upload a PDF or PPTX document")
    async def upload_file(file: UploadFile = File(...)):
        """
        Upload a document (.pdf or .pptx) to query it.
        Saves it to EXPORTS_DIR and returns the full server file path.
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="Empty filename provided.")

        ext = Path(file.filename).suffix.lower()
        if ext not in {".pdf", ".pptx"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Only .pdf and .pptx are supported."
            )

        try:
            exports_dir = Path(config.EXPORTS_DIR)
            exports_dir.mkdir(parents=True, exist_ok=True)

            dest_path = exports_dir / f"uploaded_{file.filename}"
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info("File uploaded: %s", dest_path)
            return {
                "status": "success",
                "filename": file.filename,
                "filepath": str(dest_path.resolve()).replace("\\", "/"),
            }
        except Exception as exc:
            logger.error("File upload failed: %s", exc)
            raise HTTPException(status_code=500, detail=f"File save failed: {exc}")

    @app.get("/health", summary="Health check")
    async def health():
        """Returns 200 OK when the service is running."""
        return {"status": "ok", "interface": "api"}

    return app


# ═══════════════════════════════════════════════════════════════════════════════
#  Start-up
# ═══════════════════════════════════════════════════════════════════════════════

if config.INTERFACE == "api":
    # `app` must be a module-level variable so uvicorn can discover it:
    #   uvicorn main:app --reload
    app = _build_fastapi_app()

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(
            "main:app",
            host=config.API_HOST,
            port=config.API_PORT,
            reload=False,
        )

else:
    # Default: CLI mode
    if __name__ == "__main__":
        run_cli()
