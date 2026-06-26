"""
llm/context.py — Token budget management and conversation history trimming.

Responsibilities:
  - Accept the full message history for a session.
  - Trim it from the oldest end until the total token_count fits within the
    configured CHAT_HISTORY_TOKEN_BUDGET.
  - Always preserve the most recent user message, even if it alone exceeds
    the budget.

This module has zero imports from llama_cpp or transformers.
It is pure Python arithmetic on pre-stored token counts.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imported only for type hints — avoids a circular import at runtime.
    from models.message import Message


def fit_history(
    messages: list["Message"],
    budget: int,
) -> list["Message"]:
    """
    Trim a message list so that the sum of token_count values is ≤ budget.

    Strategy:
      1. Sum token_count for every message (None counts as 0 for safety;
         assistant messages whose stream was interrupted may be None).
      2. Remove the oldest messages one-by-one until the total is within budget.
      3. Unconditionally preserve the last message in the list. The final entry
         is always the user's most recent prompt — removing it would produce
         an empty or incoherent context.

    Args:
        messages: ORM Message objects, ordered created_at ASC (oldest first).
                  This list is mutated internally; the caller's list is not
                  affected because we work on a copy.
        budget:   Maximum total token_count allowed. Sourced from
                  settings.chat_history_token_budget in the service layer.

    Returns:
        A (potentially shorter) list of Message objects that fits within budget,
        always containing at least the final message.
    """
    if not messages:
        return messages

    # Work on a copy so the caller's list is untouched.
    trimmed = list(messages)

    def _total(msgs: list) -> int:
        return sum(m.token_count or 0 for m in msgs)

    # Trim from the front until we fit, but never remove the last message.
    while len(trimmed) > 1 and _total(trimmed) > budget:
        trimmed.pop(0)

    return trimmed
