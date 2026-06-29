"""
handlers/document_handler.py
────────────────────────────
Handles the "document" intent: reads a local PDF or PPTX file that the user
points to in their message, then answers their question about it.

Pipeline:
  1. Extract a file path from the user's message using regex
  2. Read the file using tools/document_tool.py
  3. Run agents/document_agent.py with the extracted text + user question
  4. Return the answer

Supported path formats the user can type:
  "read D:/reports/file.pdf and summarise"
  "analyze the file at C:\\Users\\mohaz\\slides.pptx"
  "open D:\\docs\\report.pdf"
  "read C:/Downloads/presentation.pptx please"
"""

import logging
import re
from typing import Any

from agents.document_agent import run_document_agent
from tools.document_tool import extract_document_text

logger = logging.getLogger(__name__)

def _extract_path(text: str) -> str | None:
    """
    Find the first Windows file path in the user's message.
    Supports paths with spaces, quotes, and .pdf/.pptx extensions.
    """
    # 1. Quoted path: e.g. "D:/Folder/file.pdf"
    quoted_match = re.search(r'["\']([A-Za-z]:[/\\][^"\']+?\.(?:pdf|pptx))["\']', text, re.IGNORECASE)
    if quoted_match:
        return quoted_match.group(1).replace("\\", "/")

    # 2. Unquoted path ending with .pdf or .pptx (supports spaces inside path)
    unquoted_match = re.search(r'([A-Za-z]:[/\\][^"\']+?\.(?:pdf|pptx))', text, re.IGNORECASE)
    if unquoted_match:
        return unquoted_match.group(1).replace("\\", "/")

    # 3. UNC path: e.g. \\server\share\file.pdf
    unc_match = re.search(r'(\\\\[^"\']+?\.(?:pdf|pptx))', text, re.IGNORECASE)
    if unc_match:
        return unc_match.group(1).replace("\\", "/")

    # 4. Fallback path (no spaces)
    fallback_match = re.search(r'([A-Za-z]:[/\\][^\s"\'\)]+)', text)
    if fallback_match:
        return fallback_match.group(1).replace("\\", "/")

    return None


def handle_document(llm: Any, chat_input: str) -> str:
    """
    Full document Q&A pipeline.

    Parameters
    ----------
    llm        : LLM from build_document_agent() (simple chat model, no tools).
    chat_input : Sanitised user message.

    Returns
    -------
    LLM answer about the document, or a user-friendly error message.
    """
    # ── Step 1: Find the file path ─────────────────────────────────────────
    file_path = _extract_path(chat_input)

    if not file_path:
        return (
            "I couldn't find a file path in your message. "
            "Please include the full path to the file, for example:\n"
            '  "read D:/reports/annual_report.pdf"\n'
            '  "analyze C:/Users/mohaz/Downloads/slides.pptx"'
        )

    # ── Step 2: Extract text from the file ────────────────────────────────
    try:
        document_text = extract_document_text(file_path)
    except FileNotFoundError:
        return (
            f"I couldn't find the file at `{file_path}`. "
            "Please check the path and try again."
        )
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        logger.error("Document read error: %s", exc)
        return f"I had trouble reading the file ({exc}). Please check it's a valid PDF or PPTX."

    if not document_text.strip():
        return (
            f"The file at `{file_path}` appears to be empty or contains no readable text. "
            "Try a different file."
        )

    # ── Step 3: Answer the user's question ────────────────────────────────
    logger.info("Document loaded (%d chars). Running Q&A…", len(document_text))
    try:
        answer = run_document_agent(llm, document_text, chat_input)
        ext = file_path.rsplit(".", 1)[-1].upper()
        return f"📄 **From your {ext} file** (`{file_path.split('/')[-1]}`):\n\n{answer}"
    except Exception as exc:
        logger.error("Document agent error: %s", exc)
        return f"I read the file but ran into a problem answering your question ({exc})."
