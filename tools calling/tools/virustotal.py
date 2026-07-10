"""
VirusTotal API v3 lookup. Requires VIRUSTOTAL_API_KEY.
Free tier: 4 requests/min, 500/day -- caching matters here.
"""
import os
import base64
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_ip, is_valid_domain, is_valid_hash, is_valid_url, cache_get, cache_set, safe_get

VT_BASE = "https://www.virustotal.com/api/v3"
CACHE_TTL = 60 * 60 * 6  # 6h -- respects the tight free-tier rate limit


class VirusTotalArgs(BaseModel):
    target: str = Field(description="The IP, domain, file hash (md5/sha1/sha256), or URL to check")
    target_type: Literal["ip", "domain", "hash", "url"] = Field(description="Type of the target")


def _endpoint_for(target_type: str, target: str) -> str:
    if target_type == "ip":
        return f"{VT_BASE}/ip_addresses/{target}"
    if target_type == "domain":
        return f"{VT_BASE}/domains/{target}"
    if target_type == "hash":
        return f"{VT_BASE}/files/{target}"
    if target_type == "url":
        # VT requires the URL identifier to be base64 (no padding)
        url_id = base64.urlsafe_b64encode(target.encode()).decode().strip("=")
        return f"{VT_BASE}/urls/{url_id}"
    raise ValueError("unreachable")


@tool(args_schema=VirusTotalArgs)
async def virustotal_lookup(target: str, target_type: str) -> dict:
    """Get a VirusTotal report for an IP, domain, file hash, or URL (detection ratio, categories, last analysis)."""
    target = target.strip()

    validators = {
        "ip": is_valid_ip,
        "domain": is_valid_domain,
        "hash": is_valid_hash,
        "url": is_valid_url,
    }
    if target_type not in validators:
        return {"error": "invalid_input", "detail": f"target_type must be one of {list(validators)}."}
    if not validators[target_type](target):
        return {"error": "invalid_input", "detail": f"'{target}' is not a valid {target_type}."}

    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        return {"error": "config_error", "detail": "VIRUSTOTAL_API_KEY is not set."}

    cache_key = f"vt:{target_type}:{target}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    url = _endpoint_for(target_type, target)
    headers = {"x-apikey": api_key}
    result = await safe_get(url, headers=headers)
    if not result["ok"]:
        return {"error": result["error"], "detail": result.get("detail")}

    attrs = result["data"].get("data", {}).get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    output = {
        "target": target,
        "target_type": target_type,
        "malicious": stats.get("malicious", 0),
        "suspicious": stats.get("suspicious", 0),
        "harmless": stats.get("harmless", 0),
        "undetected": stats.get("undetected", 0),
        "reputation": attrs.get("reputation"),
        "categories": attrs.get("categories"),
        "last_analysis_date": attrs.get("last_analysis_date"),
    }
    cache_set(cache_key, output)
    return output
