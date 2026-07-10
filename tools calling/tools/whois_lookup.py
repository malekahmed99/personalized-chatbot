"""
WHOIS lookup using the `python-whois` library (queries registrar WHOIS
servers directly -- no API key needed, but can be slow/rate-limited by
registrars for high-volume use).
"""
import asyncio
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_domain, cache_get, cache_set

CACHE_TTL = 60 * 60 * 12  # registration data rarely changes -- cache 12h


class WhoisLookupArgs(BaseModel):
    domain: str = Field(description="Domain name to look up, e.g. example.com")


def _run_whois(domain: str) -> dict:
    import whois  # python-whois; imported lazily so missing dep fails only when tool is used
    w = whois.whois(domain)
    return {
        "domain": domain,
        "registrar": w.get("registrar"),
        "creation_date": str(w.get("creation_date")),
        "expiration_date": str(w.get("expiration_date")),
        "updated_date": str(w.get("updated_date")),
        "name_servers": w.get("name_servers"),
        "status": w.get("status"),
        "emails": w.get("emails"),
        "org": w.get("org"),
        "country": w.get("country"),
    }


@tool(args_schema=WhoisLookupArgs)
async def whois_lookup(domain: str) -> dict:
    """Look up WHOIS registration details for a domain (registrar, creation date, name servers, etc)."""
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return {"error": "invalid_input", "detail": f"'{domain}' is not a valid domain name."}

    cache_key = f"whois:{domain}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    try:
        # python-whois is blocking/synchronous -- run in a thread so it
        # doesn't block the agent's event loop.
        output = await asyncio.wait_for(asyncio.to_thread(_run_whois, domain), timeout=15)
    except asyncio.TimeoutError:
        return {"error": "timeout", "detail": f"WHOIS query for {domain} timed out."}
    except Exception as e:  # noqa: BLE001
        return {"error": "unexpected", "detail": str(e)}

    cache_set(cache_key, output)
    return output
