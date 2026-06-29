"""
agents/llm_factory.py
─────────────────────
Single place that constructs the LLM client.  All agent files call
`build_llm()` so switching providers (Gemini ↔ OpenAI) only requires
changing LLM_PROVIDER in .env — no code changes needed.
"""

import logging

from langchain_core.language_models import BaseChatModel

import config

logger = logging.getLogger(__name__)


def build_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Instantiate and return the configured LLM.

    Parameters
    ----------
    temperature : Sampling temperature. Default 0.0 for deterministic SQL /
                  analytics answers.
    """
    provider = config.LLM_PROVIDER

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI  # type: ignore

        logger.info("Using LLM: Mistral AI (%s)", config.MISTRAL_MODEL)
        return ChatMistralAI(
            model=config.MISTRAL_MODEL,
            mistral_api_key=config.MISTRAL_API_KEY,
            temperature=temperature,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        logger.info("Using LLM: Google Gemini (%s)", config.GEMINI_MODEL)
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=temperature,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore

        logger.info("Using LLM: OpenAI (%s)", config.OPENAI_MODEL)
        return ChatOpenAI(
            model=config.OPENAI_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            "Set LLM_PROVIDER to 'mistral', 'gemini', or 'openai' in your .env file."
        )
