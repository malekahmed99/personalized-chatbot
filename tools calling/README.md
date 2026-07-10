# CyberSentry — Cybersecurity Tool-Calling Agent

Wraps your fine-tuned Qwen3-4B (q3_k_m GGUF) in a LangGraph agent with 8
cybersecurity investigation tools.

## Project layout

```
cybersentry/
├── tools/
│   ├── common.py           # shared validation, caching, safe HTTP wrapper
│   ├── cve_lookup.py        # NVD API — no key required
│   ├── ip_reputation.py     # AbuseIPDB — needs ABUSEIPDB_API_KEY
│   ├── whois_lookup.py      # python-whois — no key required
│   ├── dns_lookup.py        # dnspython — no key required
│   ├── virustotal.py        # VT API v3 — needs VIRUSTOTAL_API_KEY
│   ├── shodan_tool.py       # Shodan — needs SHODAN_API_KEY
│   ├── malwarebazaar.py     # abuse.ch — needs MALWAREBAZAAR_API_KEY
│   └── url_scan.py          # urlscan.io — needs URLSCAN_API_KEY
├── system_prompt.py         # agent's system prompt
├── agent.py                 # LangGraph wiring + model loading
├── Modelfile                # Ollama config for your GGUF
├── requirements.txt
├── .env.example
└── tests/
    ├── test_tools_standalone.py    # tests tools directly, no model needed
    └── test_agent_tool_selection.py # tests the model's tool-selection behavior
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API keys** — copy `.env.example` to `.env` and fill in the keys you have.
   Free tools (CVE, WHOIS, DNS) work with no keys at all. Get keys for the rest at:
   - AbuseIPDB: https://www.abuseipdb.com/account/api
   - VirusTotal: https://www.virustotal.com/gui/my-apikey
   - Shodan: https://account.shodan.io/
   - abuse.ch (MalwareBazaar): https://auth.abuse.ch/
   - urlscan.io: https://urlscan.io/user/profile/

   Load them before running:
   ```bash
   export $(grep -v '^#' .env | xargs)
   ```

3. **Load the model into Ollama**
   ```bash
   # place your model-q3-k-m.gguf in this directory, then:
   ollama create cybersentry -f Modelfile
   ollama run cybersentry "What is CVE-2024-3400?"
   ```
   If tool calls come back as text inside the response instead of a
   structured `tool_calls` field, your GGUF's chat template likely didn't
   preserve Qwen3's tool-calling format — see the comment in `Modelfile`.

## Testing order (do this before wiring into your FastAPI app)

**Step 1 — test tools without the model:**
```bash
python -m tests.test_tools_standalone
```
This confirms each tool function works (or fails cleanly with `config_error`
if a key is missing) — isolates tool bugs from model bugs.

**Step 2 — test the model's tool selection:**
```bash
python -m tests.test_agent_tool_selection
```
This runs real questions through the full LangGraph agent and prints
which tool(s) the model chooses, so you can eyeball whether it's picking
correctly and refusing out-of-scope requests.

**Step 3 — interactive single question:**
```bash
python agent.py
```
Runs one hardcoded question end-to-end as a quick smoke test.

## What was verified in this environment vs. what you need to check yourself

This sandbox has a restricted outbound network (only pypi/github/npm-type
domains), so I could not reach NVD, AbuseIPDB, VirusTotal, Shodan,
abuse.ch, or urlscan.io from here — those calls will show `auth_failed`
or timeout in this sandbox regardless of correctness. What I *did* verify
here:
- DNS lookup works end-to-end against real DNS (`example.com` resolved correctly).
- All input-validation paths (bad CVE ID, bad IP, bad domain, bad hash)
  correctly return structured `invalid_input` errors instead of raising.
- The code imports and runs cleanly with no syntax/dependency issues.

On your machine (with real internet + API keys), run `test_tools_standalone.py`
first to confirm each key-gated tool actually returns data, before moving to
the model tests.

## Caching note

`tools/common.py` currently uses a simple in-memory TTL cache
(`_CACHE` dict), which resets on restart and isn't shared across
processes. For production, swap `cache_get`/`cache_set` for a Postgres
table:
```sql
CREATE TABLE tool_cache (
    cache_key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
matching your existing FastAPI/Postgres stack.

## Next step

Once tool selection looks right in `test_agent_tool_selection.py`, wire
`build_agent()` and `ask()` from `agent.py` into a FastAPI endpoint,
streaming `app.astream(...)` events to your React frontend so tool calls
are visible live.
