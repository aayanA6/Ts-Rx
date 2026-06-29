from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

# Simple in-memory sliding-window rate limiter.
# NOTE: Per-process only — limits are not shared across multiple uvicorn workers.
# For multi-worker deployments, replace with a Redis-backed solution (e.g. slowapi).
_AUTH_MAX_CALLS = 10
_AUTH_WINDOW_SECONDS = 60.0

_auth_buckets: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


async def check_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency — raises 429 when the client IP exceeds the auth rate limit."""
    ip = _client_ip(request)
    now = time.monotonic()
    _auth_buckets[ip] = [t for t in _auth_buckets[ip] if now - t < _AUTH_WINDOW_SECONDS]
    if len(_auth_buckets[ip]) >= _AUTH_MAX_CALLS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait {int(_AUTH_WINDOW_SECONDS)}s before trying again.",
            headers={"Retry-After": str(int(_AUTH_WINDOW_SECONDS))},
        )
    _auth_buckets[ip].append(now)
