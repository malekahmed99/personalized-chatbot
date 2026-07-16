"""
tools/registry.py - Tool name to async callable dispatch.

session_id and db are always supplied by the orchestrator from the trusted
HTTP request context, never from LLM-parsed arguments.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tools.report import generate_incident_report

TOOL_REGISTRY: dict[str, object] = {
    "generate_incident_report": generate_incident_report,
}


async def dispatch(
    name: str,
    args: dict,              # LLM-generated args (empty for report tool)
    session_id: uuid.UUID,   # Always from trusted request context
    db: AsyncSession,
) -> dict:
    """
    Dispatch a parsed tool call to its implementation.

    Returns a result dict (or error dict) suitable for persisting as a
    tool-role message and passing back into the LLM context.

    The session_id and db are injected by the orchestrator from the trusted
    HTTP request context. LLM-supplied args are passed through only for
    future tools that need them (e.g. lookup_cve needs cve_id). The report
    tool ignores args entirely.
    """
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    fn = TOOL_REGISTRY[name]
    return await fn(session_id=session_id, db=db, **args)
