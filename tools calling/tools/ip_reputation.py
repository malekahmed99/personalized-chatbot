"""
IP reputation via AbuseIPDB. Requires ABUSEIPDB_API_KEY (free tier available
at https://www.abuseipdb.com/account/api).
"""
import os
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_ip, cache_get, cache_set, safe_get

ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"
CACHE_TTL = 60 * 30  # reputation changes -- cache only 30 min


class IPReputationArgs(BaseModel):
    ip: str = Field(description="IPv4 address to check, e.g. 8.8.8.8")


@tool(args_schema=IPReputationArgs)
async def ip_reputation(ip: str) -> dict:
    """Check an IP address's abuse/reputation score, country, ISP, and recent report count."""
    ip = ip.strip()
    if not is_valid_ip(ip):
        return {"error": "invalid_input", "detail": f"'{ip}' is not a valid IPv4 address."}

    api_key = os.getenv("ABUSEIPDB_API_KEY")
    if not api_key:
        return {"error": "config_error", "detail": "ABUSEIPDB_API_KEY is not set."}

    cache_key = f"ip_rep:{ip}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    headers = {"Key": api_key, "Accept": "application/json"}
    params = {"ipAddress": ip, "maxAgeInDays": 90}
    result = await safe_get(ABUSEIPDB_URL, headers=headers, params=params)
    if not result["ok"]:
        return {"error": result["error"], "detail": result.get("detail")}

    d = result["data"].get("data", {})
    output = {
        "ip": ip,
        "abuse_confidence_score": d.get("abuseConfidenceScore"),
        "country": d.get("countryCode"),
        "isp": d.get("isp"),
        "domain": d.get("domain"),
        "total_reports": d.get("totalReports"),
        "last_reported_at": d.get("lastReportedAt"),
        "is_tor": d.get("isTor"),
        "usage_type": d.get("usageType"),
    }
    cache_set(cache_key, output)
    return output
