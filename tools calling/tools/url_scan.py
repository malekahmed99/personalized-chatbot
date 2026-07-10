"""
URL scanning via urlscan.io. Requires URLSCAN_API_KEY.

Submits the URL for scanning (visibility="unlisted" by default -- do not
change to "public" without the user's explicit knowledge, since public
scans are visible to anyone) and polls briefly for a result. If the scan
isn't done within the poll window, returns the result_url so the caller
can check back later instead of blocking indefinitely.
"""
import os
import asyncio
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from tools.common import is_valid_url, cache_get, cache_set, safe_post, safe_get

SUBMIT_URL = "https://urlscan.io/api/v1/scan/"
CACHE_TTL = 60 * 60 * 6
POLL_ATTEMPTS = 5
POLL_DELAY_SECONDS = 3


class URLScanArgs(BaseModel):
    url: str = Field(description="Full URL to scan, including http:// or https://")


@tool(args_schema=URLScanArgs)
async def url_scan(url: str) -> dict:
    """Submit a URL to urlscan.io and retrieve its scan report (verdicts, page redirects, detected technologies)."""
    url = url.strip()
    if not is_valid_url(url):
        return {"error": "invalid_input", "detail": f"'{url}' is not a valid http(s) URL."}

    api_key = os.getenv("URLSCAN_API_KEY")
    if not api_key:
        return {"error": "config_error", "detail": "URLSCAN_API_KEY is not set."}

    cache_key = f"urlscan:{url}"
    cached = cache_get(cache_key, CACHE_TTL)
    if cached:
        return cached

    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    submit = await safe_post(SUBMIT_URL, headers=headers, json_body={"url": url, "visibility": "unlisted"})
    if not submit["ok"]:
        return {"error": submit["error"], "detail": submit.get("detail")}

    result_api = submit["data"].get("api")
    result_page = submit["data"].get("result")
    if not result_api:
        return {"error": "submit_failed", "detail": "urlscan.io did not return a result URL."}

    # Poll briefly -- scans typically take 10-20s, we don't want to block
    # the agent loop for too long.
    for _ in range(POLL_ATTEMPTS):
        await asyncio.sleep(POLL_DELAY_SECONDS)
        poll = await safe_get(result_api)
        if poll["ok"]:
            data = poll["data"]
            verdicts = data.get("verdicts", {}).get("overall", {})
            page = data.get("page", {})
            output = {
                "url": url,
                "status": "complete",
                "malicious": verdicts.get("malicious"),
                "score": verdicts.get("score"),
                "categories": verdicts.get("categories"),
                "final_url": page.get("url"),
                "ip": page.get("ip"),
                "server": page.get("server"),
                "result_page": result_page,
            }
            cache_set(cache_key, output)
            return output
        # 404 while queued is expected -- keep polling
        if poll.get("error") not in ("http_error", "not_found"):
            break

    return {
        "url": url,
        "status": "pending",
        "detail": "Scan submitted but not finished within the poll window. Check result_page later.",
        "result_page": result_page,
    }
