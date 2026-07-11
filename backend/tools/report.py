"""
tools/report.py - generate_incident_report() implementation.

Flow (per generate_incident_report_spec.md):
  1. Fetch session transcript (user + assistant messages only).
  2. Dedicated synthesis LLM call with a narrow summarization system prompt
     NOT the forensic persona prompt.
  3. Extract the first paragraph of ## Summary for model awareness context.
  4. Write synthesized markdown to storage/reports/.
  5. Create File DB row (message_id left NULL; orchestrator sets it via
     two-phase commit after creating the confirmation Message row).
  6. Return result dict: filename, file_id, storage_path, summary.

session_id is ALWAYS injected by the orchestrator from the trusted HTTP
request context. It never comes from LLM-generated arguments.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from llm.client import LLMClient
from llm.prompt import format_chat_prompt
from models.file import File
from models.message import Message
from schemas.enums import RoleEnum

import logging

_logger = logging.getLogger("tools.report")

# Narrow system prompt for synthesis. Deliberately NOT the forensic persona
# prompt - this call is a technical writer producing a structured postmortem,
# not an investigator answering a question.
_SYNTHESIS_SYSTEM_PROMPT = """\
You are a technical writer summarizing a resolved investigation conversation.
Read the conversation and produce a structured incident report in Markdown using
exactly these sections:

# Incident Report

## Summary
[1-3 sentence plain-language description of what the issue was and how it was resolved]

## Root Cause
[The confirmed underlying cause, stated directly]

## Evidence
[The specific log lines, error messages, or observations that confirmed the root cause]

## Resolution
[The exact fix that resolved the issue, described precisely enough to be reproducible]

## Why It Happened
[Brief causal explanation connecting the root cause to the resolution]

## Verification
[How the fix was confirmed to have worked]

## Ruled-Out Approaches
[Brief bullet list of approaches tried and discarded. Write N/A if nothing was ruled out.]

Rules:
- Exclude unresolved tangents and small talk.
- Use only what is confirmed in the conversation - do not invent details.
- If a section has no content, write N/A rather than omitting the section.
"""


def _extract_summary(markdown: str) -> str:
    """
    Extract the first paragraph of the ## Summary section for model awareness.

    This excerpt is stored in the tool-role message so that on subsequent turns
    the model can reference what the report was about without the full content
    consuming the context window.
    """
    marker = "## Summary"
    idx = markdown.find(marker)
    if idx == -1:
        return ""
    after = markdown[idx + len(marker):].lstrip("\n")
    # Stop at next blank line or next ## header, whichever comes first.
    end_blank = after.find("\n\n")
    end_header = after.find("\n##")
    candidates = [e for e in (end_blank, end_header) if e != -1]
    end = min(candidates) if candidates else len(after)
    return after[:end].strip()[:400]  # Hard cap at 400 chars (~100 tokens)


async def generate_incident_report(
    session_id: uuid.UUID,
    db: AsyncSession,
    **_ignored_llm_args,  # LLM-generated args intentionally ignored (empty schema)
) -> dict:
    """
    Synthesize the session into a structured markdown report, write it to disk,
    and create a File DB row.

    Returns:
        {
            "status": "ok",
            "filename": "Incident_Report_YYYYMMDD_HHMMSS.md",
            "file_id": "<uuid>",
            "storage_path": "/absolute/path/to/report.md",
            "summary": "<first paragraph of ## Summary section>",
        }
        or {"error": "<message>"} on failure.
    """
    try:
        # 1. Fetch transcript - user and assistant roles only (exclude tool messages)
        result = await db.execute(
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.role.in_([RoleEnum.user.value, RoleEnum.assistant.value]),
            )
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())

        if not messages:
            return {"error": "No conversation content to report."}

        # 2. Build transcript dict for the synthesis prompt
        transcript_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        # 3. Synthesis call - dedicated narrow prompt, no tools active
        synthesis_prompt = format_chat_prompt(
            messages=transcript_messages,
            system_prompt=_SYNTHESIS_SYSTEM_PROMPT,
            tools=None,
        )

        client = LLMClient.get()
        # NOTE: This call acquires the semaphore. The semaphore was released
        # after the first generation (tool-detection pass) completed. A second
        # request could theoretically slip in during that brief window - this is
        # accepted behavior (FLAG-02 resolution). Both calls are serialized at
        # the semaphore level; inference is never actually concurrent.
        report_chunks: list[str] = []
        async for token in client.generate_stream(synthesis_prompt):
            report_chunks.append(token)
        report_markdown = "".join(report_chunks)

        # 4. Extract summary paragraph for model awareness on subsequent turns
        summary = _extract_summary(report_markdown)

        # 5. Write report to disk
        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"Incident_Report_{timestamp}.md"
        file_path = reports_dir / filename
        file_path.write_text(report_markdown, encoding="utf-8")
        _logger.info("Report written to %s", file_path)

        # 6. Create File DB row.
        # message_id is intentionally NULL here - the orchestrator in core/utils.py
        # sets it after creating the confirmation Message row (two-phase commit,
        # FLAG-01 resolution - tool does not have knowledge of the Message layer).
        file_record = File(
            session_id=session_id,
            storage_path=str(file_path.resolve()),
            original_filename=filename,
            mime_type="text/markdown",
        )
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)

        return {
            "status": "ok",
            "filename": filename,
            "file_id": str(file_record.id),
            "storage_path": str(file_path.resolve()),
            "summary": summary,
        }

    except Exception as exc:
        _logger.error("Report generation failed: %s", exc, exc_info=True)
        return {"error": f"Report generation failed: {exc}"}
