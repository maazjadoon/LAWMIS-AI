"""
agents/document_agent.py
────────────────────────
A simple LLM agent for answering questions about an uploaded document.

Unlike the DB agents, this agent does NOT use tools — the document text is
injected directly into the prompt. This keeps latency low and avoids
unnecessary tool-call overhead for document Q&A.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm_factory import build_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful document analyst. The user has provided you with the
extracted text content of a file (PDF or PowerPoint). Your job is to:
  • Answer questions about the document accurately
  • Summarise sections on request
  • Identify key facts, figures, dates, and themes
  • Flag if something asked is not present in the document

Always base your answers strictly on the provided document content.
If the answer is not in the document, say so clearly rather than guessing.\
"""

DocumentAgent = Any


def build_document_agent() -> DocumentAgent:
    """Build the document agent LLM (stateless — no tools needed)."""
    llm = build_llm(temperature=0.0)
    logger.info("Document agent ready.")
    return llm


def run_document_agent(llm: DocumentAgent, document_text: str, user_question: str) -> str:
    """
    Answer a question about a document using its extracted text.

    Parameters
    ----------
    llm            : LLM instance from build_document_agent().
    document_text  : Full extracted text of the document.
    user_question  : The user's question or request.

    Returns
    -------
    LLM answer string.
    """
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"DOCUMENT CONTENT:\n"
            f"{'─' * 60}\n"
            f"{document_text}\n"
            f"{'─' * 60}\n\n"
            f"USER REQUEST: {user_question}"
        )),
    ]

    response = llm.invoke(messages)
    return getattr(response, "content", str(response)).strip()
