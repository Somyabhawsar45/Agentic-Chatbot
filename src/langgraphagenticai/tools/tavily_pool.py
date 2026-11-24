"""
Several Tavily keys for the app's own web searches, like GROQ_API_KEYS does for Groq.

    TAVILY_API_KEY   the main key
    TAVILY_API_KEYS  extra keys, comma-separated; tried in turn when a key is out of credits,
                     rejected or rate-limited

A visitor's own key (typed in ⚙ Settings) is used on its own and never mixed with the app's keys.
After a key fails, the client stays on the next working key, so a used-up key isn't retried on
every search.
"""

import os
import threading

from tavily import TavilyClient
from tavily.errors import ForbiddenError, InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError

# errors where another key can help (out of credits, bad/revoked key, plan limits)
RETRYABLE = (UsageLimitExceededError, InvalidAPIKeyError, ForbiddenError, MissingAPIKeyError)


def _split(value: str) -> list:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def builtin_tavily_keys() -> list:
    keys = []
    for key in [os.environ.get("TAVILY_API_KEY", "")] + _split(os.environ.get("TAVILY_API_KEYS", "")):
        if key and key not in keys:
            keys.append(key)
    return keys


def tavily_key_pool(api_key: str = None) -> list:
    """The keys to try, in order. No key given (or one of the app's): all of the app's keys."""
    pool = builtin_tavily_keys()
    if not api_key or api_key in pool:
        return pool or [None]          # None lets TavilyClient report the missing key clearly
    return [api_key]                   # a visitor's own key, on its own


class RotatingTavilyClient:
    """Same .search() as TavilyClient, but moves on to the next key when one runs out."""

    def __init__(self, api_key: str = None, client_factory=TavilyClient):
        self.keys = tavily_key_pool(api_key)
        self._factory = client_factory
        self._clients = {}
        self._current = 0
        self._lock = threading.Lock()

    def _client(self, index: int):
        if index not in self._clients:
            self._clients[index] = self._factory(api_key=self.keys[index])
        return self._clients[index]

    def search(self, *args, **kwargs):
        with self._lock:
            start = self._current
        last_error = None
        for offset in range(len(self.keys)):
            index = (start + offset) % len(self.keys)
            try:
                result = self._client(index).search(*args, **kwargs)
            except RETRYABLE as e:
                last_error = e
                continue
            with self._lock:
                self._current = index          # stay on the key that works
            return result
        raise last_error
