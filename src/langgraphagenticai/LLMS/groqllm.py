import os

import streamlit as st
from langchain_groq import ChatGroq

# Groq's free limits are per model, so when one model is rate-limited another usually still has room.
# (Only models that support tool calling; Groq retired the Llama 3.1 models.)
DEFAULT_FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def _split(value: str) -> list:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def builtin_key_pool() -> list:
    """The app's own keys: GROQ_API_KEY first, then any extra GROQ_API_KEYS (comma-separated)."""
    keys = []
    for key in [os.environ.get("GROQ_API_KEY", "")] + _split(os.environ.get("GROQ_API_KEYS", "")):
        if key and key not in keys:
            keys.append(key)
    return keys


def fallback_models(primary: str) -> list:
    configured = _split(os.environ.get("GROQ_FALLBACK_MODELS", "")) or DEFAULT_FALLBACK_MODELS
    return [m for m in dict.fromkeys(configured) if m != primary]


def candidate_chain(api_key: str, model: str) -> list:
    """
    (key, model) pairs to try, in order. A visitor's own key is used on its own; the app's built-in
    key is followed by the other built-in keys. Then the same keys with the fallback model(s).
    """
    pool = builtin_key_pool()
    keys = pool if api_key and api_key in pool else [api_key]
    chain = [(k, model) for k in keys]
    for fallback in fallback_models(model):
        chain += [(k, fallback) for k in keys]
    return chain


def _retryable_errors() -> tuple:
    """Errors where trying another key/model can help: rate limits, bad/revoked keys, a model Groq
    has retired (404), Groq outages."""
    import groq
    return (groq.RateLimitError, groq.AuthenticationError, groq.NotFoundError, groq.InternalServerError,
            groq.APITimeoutError, groq.APIConnectionError)


def build_llm(api_key: str, model: str):
    """
    One model, or a chain that moves on to the next key/model the moment one fails with a
    retryable error. Earlier links retry once (fail fast); the last one retries patiently and
    honours Groq's "try again in Xs" wait (Deep Research bursts often need that).
    """
    chain = candidate_chain(api_key, model)
    llms = [
        ChatGroq(api_key=key, model=name, streaming=True, max_retries=6 if i == len(chain) - 1 else 1)
        for i, (key, name) in enumerate(chain)
    ]
    if len(llms) == 1:
        return llms[0]
    return llms[0].with_fallbacks(llms[1:], exceptions_to_handle=_retryable_errors())


class GroqLLM:
    def __init__(self, user_contols_input):
        self.user_controls_input = user_contols_input

    def get_llm_model(self):
        try:
            groq_api_key = self.user_controls_input.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
            selected_groq_model = self.user_controls_input.get("selected_groq_model")

            if not groq_api_key:
                st.error("Please enter the Groq API key")
                return None

            llm = build_llm(groq_api_key, selected_groq_model)

        except Exception as e:
            raise ValueError(f"Error Occurred With Exception: {e}")
        return llm
