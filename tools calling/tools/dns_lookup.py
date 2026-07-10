"""
DNS lookup using dnspython. No API key required.
"""
import asyncio
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_domain, cache_get, cache_set

CACHE_TTL = 60 * 15  # DNS can change -- cache only 15 min
VALID_RECORD_TYPES = {"A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"}


class DNSLookupArgs(BaseModel):
    domain: str = Field(description="Domain name to resolve, e.g. example.com")
    record_type: str = Field(default="A", description="DNS record type: A, AAAA, MX, TXT, NS, CNAME, or SOA")


def _run_dns(domain: str, record_type: str) -> list[str]:
    import dns.resolver  # imported lazily
    answers = dns.resolver.resolve(domain, record_type)
    return [str(r) for r in answers]


@tool(args_schema=DNSLookupArgs)
async def dns_lookup(domain: str, record_type: str = "A") -> dict:
    """Resolve DNS records (A, AAAA, MX, TXT, NS, CNAME, SOA) for a domain."""
    domain = domain.strip().lower()
    record_type = record_type.strip().upper()

    if not is_valid_domain(domain):
        return {"error": "invalid_input", "detail": f"'{domain}' is not a valid domain name."}
    if record_type not in VALID_RECORD_TYPES:
        return {"error": "invalid_input", "detail": f"'{record_type}' is not supported. Use one of {sorted(VALID_RECORD_TYPES)}."}

    cache_key = f"dns:{domain}:{record_type}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    try:
        records = await asyncio.wait_for(asyncio.to_thread(_run_dns, domain, record_type), timeout=10)
    except asyncio.TimeoutError:
        return {"error": "timeout", "detail": f"DNS query for {domain} timed out."}
    except Exception as e:  # noqa: BLE001 -- covers dns.resolver.NXDOMAIN, NoAnswer, etc
        return {"error": "resolution_failed", "detail": str(e)}

    output = {"domain": domain, "record_type": record_type, "records": records}
    cache_set(cache_key, output)
    return output
