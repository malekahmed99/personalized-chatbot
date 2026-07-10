"""
Shared helpers used across all tool modules:
- input validation (so we never send junk to external APIs)
- a simple in-memory cache stub (swap for Postgres in production)
- a safe async HTTP GET/POST wrapper that never raises, always returns a dict
"""
import re
import time
import httpx
from typing import Any, Optional

IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
DOMAIN_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(\.[A-Za-z0-9-]{1,63})+$")
CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")  # md5/sha1/sha256
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

DEFAULT_TIMEOUT = 15.0


def is_valid_ip(value: str) -> bool:
    if not IP_RE.match(value):
        return False
    return all(0 <= int(octet) <= 255 for octet in value.split("."))


def is_valid_domain(value: str) -> bool:
    return bool(DOMAIN_RE.match(value))


def is_valid_cve(value: str) -> bool:
    return bool(CVE_RE.match(value))


def is_valid_hash(value: str) -> bool:
    return bool(HASH_RE.match(value))


def is_valid_url(value: str) -> bool:
    return bool(URL_RE.match(value))


# --- Very simple TTL cache (process-local). Replace with Postgres-backed
# cache in production -- see README "Caching" section for the schema. ---
_CACHE: dict[str, tuple[float, Any]] = {}


def cache_get(key: str, ttl_seconds: int) -> Optional[Any]:
    entry = _CACHE.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > ttl_seconds:
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.time(), value)


async def safe_get(
    url: str,
    *,
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET that never raises -- always returns {'ok': bool, ...}."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            return {"ok": False, "error": "rate_limited", "detail": "API rate limit hit, try again shortly."}
        if resp.status_code == 401 or resp.status_code == 403:
            return {"ok": False, "error": "auth_failed", "detail": "Missing or invalid API key."}
        if resp.status_code >= 400:
            return {"ok": False, "error": "http_error", "status": resp.status_code, "detail": resp.text[:300]}
        return {"ok": True, "data": resp.json()}
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout", "detail": f"Request to {url} timed out."}
    except Exception as e:  # noqa: BLE001 -- intentionally broad, this must never raise into the agent loop
        return {"ok": False, "error": "unexpected", "detail": str(e)}


async def safe_post(
    url: str,
    *,
    headers: Optional[dict] = None,
    json_body: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=json_body)
        if resp.status_code == 429:
            return {"ok": False, "error": "rate_limited", "detail": "API rate limit hit, try again shortly."}
        if resp.status_code in (401, 403):
            return {"ok": False, "error": "auth_failed", "detail": "Missing or invalid API key."}
        if resp.status_code >= 400:
            return {"ok": False, "error": "http_error", "status": resp.status_code, "detail": resp.text[:300]}
        try:
            return {"ok": True, "data": resp.json()}
        except Exception:
            return {"ok": True, "data": resp.text}
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout", "detail": f"Request to {url} timed out."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": "unexpected", "detail": str(e)}
