"""
Protection for the Scholr API: an API key on every route, and a simple per-caller rate limit.

* API key: Scholr's server sends `X-API-Key`. It is compared in constant time
  (secrets.compare_digest), and the API fails closed: with no NETRA_API_KEY configured on the
  server, every request is refused.
* Rate limit: a sliding one-minute window per caller IP, kept in memory (one server process).
  Scholr's server is normally the only caller, so the limits are sized for all of its students
  together; tune them with NETRA_API_DOUBTS_PER_MIN / NETRA_API_INDEX_PER_MIN.
"""

import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request


def require_api_key(x_api_key: str = Header(default="")):
    expected = os.getenv("NETRA_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _per_minute(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


class RateLimiter:
    """At most `limit()` calls per caller in any 60-second window."""

    def __init__(self, env_name: str, default: int, window: float = 60.0, clock=time.monotonic):
        self.env_name, self.default, self.window, self.clock = env_name, default, window, clock
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def limit(self) -> int:
        return _per_minute(self.env_name, self.default)

    def hit(self, caller: str) -> bool:
        """Record one call. False if the caller is over the limit (the call is not counted)."""
        now = self.clock()
        with self._lock:
            hits = self._hits[caller]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit():
                return False
            hits.append(now)
            if len(self._hits) > 10_000:          # don't grow forever with many callers
                for key in [k for k, v in self._hits.items() if not v][:5_000]:
                    del self._hits[key]
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()

    def __call__(self, request: Request):
        caller = request.client.host if request.client else "unknown"
        if not self.hit(caller):
            raise HTTPException(status_code=429, detail="Too many requests, please slow down.",
                                headers={"Retry-After": str(int(self.window))})


doubt_limiter = RateLimiter("NETRA_API_DOUBTS_PER_MIN", 60)
index_limiter = RateLimiter("NETRA_API_INDEX_PER_MIN", 20)
