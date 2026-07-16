"""
tools/schemas.py - Tool definitions passed to apply_chat_template().

generate_incident_report intentionally omits session_id from its parameters.
session_id is always injected by the orchestrator from the trusted HTTP request
context, never from LLM-generated arguments (IDOR defense).
"""

REPORT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "generate_incident_report",
        "description": (
            "Synthesize the current session's investigation findings into a "
            "structured markdown incident report and save it to disk. "
            "ONLY call this when the user explicitly asks to generate, save, "
            "or document a report. Do not call this autonomously."
        ),
        "parameters": {
            "type": "object",
            "properties": {},   # No model-settable arguments
            "required": [],
        },
    },
}

# The list passed to format_chat_prompt(tools=...) for all agentic turns.
# Extend this list when CVE Lookup and MITRE ATT&CK are added.
ACTIVE_TOOL_SCHEMAS: list[dict] = [REPORT_TOOL_SCHEMA]
