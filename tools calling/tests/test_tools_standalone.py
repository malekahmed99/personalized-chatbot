"""
Run each tool directly, with no model/agent involved, to verify API keys
and connectivity first. This isolates "is my API key/network broken" from
"is the model calling tools correctly."

Usage:
    python -m tests.test_tools_standalone
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()  # reads .env from the current working directory

from tools import (
    cve_lookup, ip_reputation, whois_lookup, dns_lookup,
    virustotal_lookup, shodan_lookup, malwarebazaar_lookup, url_scan,
)


async def run_case(name: str, coro):
    print(f"\n=== {name} ===")
    try:
        result = await coro
        print(result)
    except Exception as e:  # noqa: BLE001
        print(f"EXCEPTION: {e}")


async def main():
    # Free/no-key tools -- these should work immediately
    await run_case("CVE lookup", cve_lookup.ainvoke({"cve_id": "CVE-2024-3400"}))
    await run_case("DNS lookup", dns_lookup.ainvoke({"domain": "example.com", "record_type": "A"}))
    await run_case("WHOIS lookup", whois_lookup.ainvoke({"domain": "example.com"}))

    # Key-gated tools -- will return config_error until you set env vars
    await run_case("IP reputation", ip_reputation.ainvoke({"ip": "8.8.8.8"}))
    await run_case("VirusTotal", virustotal_lookup.ainvoke({"target": "8.8.8.8", "target_type": "ip"}))
    await run_case("Shodan", shodan_lookup.ainvoke({"ip": "1.1.1.1"}))
    await run_case("MalwareBazaar", malwarebazaar_lookup.ainvoke({
        "file_hash": "e5b3cb0d4e30d0c6c0e19d19f39a5c1747c8b3cf5c9c15b0f0b3c68f0c8d9b3d"
    }))
    await run_case("URL scan", url_scan.ainvoke({"url": "https://example.com"}))

    # Validation checks -- should all return error dicts, not exceptions
    print("\n=== Validation checks (should all return invalid_input errors) ===")
    await run_case("Bad CVE", cve_lookup.ainvoke({"cve_id": "not-a-cve"}))
    await run_case("Bad IP", ip_reputation.ainvoke({"ip": "999.999.999.999"}))
    await run_case("Bad domain", dns_lookup.ainvoke({"domain": "not a domain"}))
    await run_case("Bad hash", malwarebazaar_lookup.ainvoke({"file_hash": "tooshort"}))


if __name__ == "__main__":
    asyncio.run(main())
