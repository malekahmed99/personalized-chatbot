"""
Shodan host lookup. Requires SHODAN_API_KEY.

Note: this only queries Shodan's existing index (passive) -- it does NOT
trigger a live scan against the target, which keeps it safe to use on any
IP without needing separate authorization for active scanning.
"""
import os
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_ip, cache_get, cache_set, safe_get

SHODAN_URL = "https://api.shodan.io/shodan/host/{ip}"
CACHE_TTL = 60 * 60 * 6


class ShodanArgs(BaseModel):
    ip: str = Field(description="IPv4 address to look up in Shodan's index, e.g. 1.1.1.1")


@tool(args_schema=ShodanArgs)
async def shodan_lookup(ip: str) -> dict:
    """Look up an IP in Shodan's index: open ports, services, banners, org, and location. Passive lookup only, does not scan the target."""
    ip = ip.strip()
    if not is_valid_ip(ip):
        return {"error": "invalid_input", "detail": f"'{ip}' is not a valid IPv4 address."}

    api_key = os.getenv("SHODAN_API_KEY")
    if not api_key:
        return {"error": "config_error", "detail": "SHODAN_API_KEY is not set."}

    cache_key = f"shodan:{ip}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    url = SHODAN_URL.format(ip=ip)
    result = await safe_get(url, params={"key": api_key})
    if not result["ok"]:
        return {"error": result["error"], "detail": result.get("detail")}

    d = result["data"]
    ports = d.get("ports", [])
    services = []
    for item in d.get("data", [])[:10]:  # cap to avoid huge payloads back to the model
        services.append({
            "port": item.get("port"),
            "transport": item.get("transport"),
            "product": item.get("product"),
            "banner_excerpt": (item.get("data") or "")[:200],
        })

    output = {
        "ip": ip,
        "org": d.get("org"),
        "isp": d.get("isp"),
        "country": d.get("country_name"),
        "city": d.get("city"),
        "open_ports": ports,
        "hostnames": d.get("hostnames"),
        "services": services,
    }
    cache_set(cache_key, output)
    return output
