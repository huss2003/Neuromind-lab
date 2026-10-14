"""One pooled HTTP client per warm instance (keeps TLS connections to Supabase open) and per-request upstream timing.

Opening a new TLS connection for every database call dominated request time when the API and database are far apart."""
import contextvars
import time
from typing import Any

import httpx

_client: httpx.AsyncClient | None = None
upstream: contextvars.ContextVar[list[float] | None] = contextvars.ContextVar("upstream", default=None)


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(8, connect=4), limits=httpx.Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=60))
    return _client


async def request(method: str, url: str, **kw: Any) -> httpx.Response:
    start = time.perf_counter()
    try:
        return await client().request(method, url, **kw)
    finally:
        bucket = upstream.get()
        if bucket is not None:
            bucket.append((time.perf_counter() - start) * 1000)


def service_headers(key: str) -> dict[str, str]:
    """Headers for the server-only Supabase key. Legacy service_role keys are JWTs and go in both headers; the newer `sb_secret_...`
    keys are opaque, are sent in `apikey` only, and the gateway maps them to the service role."""
    return {"apikey": key} if key.startswith("sb_secret_") else {"apikey": key, "Authorization": f"Bearer {key}"}
