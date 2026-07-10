from tools.cve_lookup import cve_lookup
from tools.ip_reputation import ip_reputation
from tools.whois_lookup import whois_lookup
from tools.dns_lookup import dns_lookup
from tools.virustotal import virustotal_lookup
from tools.shodan_tool import shodan_lookup
from tools.malwarebazaar import malwarebazaar_lookup
from tools.url_scan import url_scan

ALL_TOOLS = [
    cve_lookup,
    ip_reputation,
    whois_lookup,
    dns_lookup,
    virustotal_lookup,
    shodan_lookup,
    malwarebazaar_lookup,
    url_scan,
]
