from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

# Simple in-memory sliding-window rate limiter.
# NOTE: Per-process only — limits are not shared across multiple uvicorn workers.
# For multi-worker deployments, replace with a Redis-backed solution (e.g. slowapi).
_AUTH_MAX_CALLS = 10
_AUTH_WINDOW_SECONDS = 60.0

# Ingest webhooks legitimately burst — a monitor host can report many services
# in a short window — so this ceiling is higher than the auth one, but still
# bounded so an unauthenticated flood of bad API keys can't hammer the DB or
# rack up Gemini calls for free.
_INGEST_MAX_CALLS = 120
_INGEST_WINDOW_SECONDS = 60.0

_buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def _client_ip(request: Request) -> str:
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request, *, bucket: str, max_calls: int, window_seconds: float) -> None:
    ip = _client_ip(request)
    calls = _buckets[bucket][ip]
    now = time.monotonic()
    fresh = [t for t in calls if now - t < window_seconds]
    if len(fresh) >= max_calls:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait {int(window_seconds)}s before trying again.",
            headers={"Retry-After": str(int(window_seconds))},
        )
    fresh.append(now)
    _buckets[bucket][ip] = fresh


async def check_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency — raises 429 when the client IP exceeds the auth rate limit."""
    _check_rate_limit(request, bucket="auth", max_calls=_AUTH_MAX_CALLS, window_seconds=_AUTH_WINDOW_SECONDS)


async def check_ingest_rate_limit(request: Request) -> None:
    """FastAPI dependency — raises 429 when the client IP exceeds the webhook ingest rate limit."""
    _check_rate_limit(request, bucket="ingest", max_calls=_INGEST_MAX_CALLS, window_seconds=_INGEST_WINDOW_SECONDS)
