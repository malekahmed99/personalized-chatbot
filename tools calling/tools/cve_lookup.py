"""
CVE lookup via the NVD (National Vulnerability Database) REST API.
No API key required for low-volume use (public rate limit ~5 req/30s;
set NVD_API_KEY env var if you have one, to get a higher limit).
"""
import os
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_cve, cache_get, cache_set, safe_get

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CACHE_TTL = 60 * 60 * 24  # CVE data is fairly static; cache 24h


class CVELookupArgs(BaseModel):
    cve_id: str = Field(description="CVE identifier, e.g. CVE-2024-3400")


@tool(args_schema=CVELookupArgs)
async def cve_lookup(cve_id: str) -> dict:
    """Look up a CVE by ID and return its description, CVSS severity, and references."""
    cve_id = cve_id.strip().upper()
    if not is_valid_cve(cve_id):
        return {"error": "invalid_input", "detail": f"'{cve_id}' is not a valid CVE ID (expected CVE-YYYY-NNNN)."}

    cache_key = f"cve:{cve_id}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    headers = {}
    api_key = os.getenv("NVD_API_KEY")
    if api_key:
        headers["apiKey"] = api_key

    result = await safe_get(NVD_URL, headers=headers, params={"cveId": cve_id})
    if not result["ok"]:
        return {"error": result["error"], "detail": result.get("detail")}

    vulns = result["data"].get("vulnerabilities", [])
    if not vulns:
        return {"error": "not_found", "detail": f"No record found for {cve_id}."}

    cve = vulns[0]["cve"]
    descriptions = cve.get("descriptions", [])
    description = next((d["value"] for d in descriptions if d["lang"] == "en"), "No description available.")

    metrics = cve.get("metrics", {})
    severity = None
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if key in metrics:
            m = metrics[key][0]
            severity = {
                "version": key,
                "baseScore": m["cvssData"].get("baseScore"),
                "baseSeverity": m["cvssData"].get("baseSeverity", m.get("baseSeverity")),
                "vectorString": m["cvssData"].get("vectorString"),
            }
            break

    references = [ref["url"] for ref in cve.get("references", [])][:5]

    output = {
        "cve_id": cve_id,
        "published": cve.get("published"),
        "last_modified": cve.get("lastModified"),
        "description": description,
        "severity": severity,
        "references": references,
    }
    cache_set(cache_key, output)
    return output
