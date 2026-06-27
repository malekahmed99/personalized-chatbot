"""
llm/prompt.py — Chat template formatting and token counting.

Responsibilities:
  - Load and cache the HuggingFace AutoTokenizer from TOKENIZER_PATH.
  - Format a list of message dicts into the ChatML prompt string using
    the Jinja2 template embedded in tokenizer_config.json.
  - Count tokens in a raw string for storage in the messages.token_count column.

Nothing in this file touches llama_cpp or the GGUF file.
"""
from __future__ import annotations

from functools import lru_cache

from transformers import AutoTokenizer, PreTrainedTokenizerFast

from core.config import settings

# ── Private ──────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_tokenizer() -> PreTrainedTokenizerFast:
    """
    Load the AutoTokenizer from TOKENIZER_PATH exactly once.

    The @lru_cache(maxsize=1) guarantees a single load regardless of how many
    times get_tokenizer() is called — even under concurrent async tasks.
    AutoTokenizer reads tokenizer.json, tokenizer_config.json,
    special_tokens_map.json, and optionally config.json from the directory.
    """
    tokenizer = AutoTokenizer.from_pretrained(
        settings.tokenizer_path,
        trust_remote_code=False,
    )
    return tokenizer  # type: ignore[return-value]


# ── Public API ───────────────────────────────────────────────────────────────


def get_tokenizer() -> PreTrainedTokenizerFast:
    """Return the cached tokenizer instance, loading it on the first call."""
    return _load_tokenizer()


def format_chat_prompt(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
) -> str:
    """
    Convert a list of {"role": ..., "content": ...} dicts into the
    ChatML-formatted string the Qwen3 model expects.

    Args:
        messages:      Conversation history, oldest first. Must include at
                       least the most recent user message.
        system_prompt: If provided, prepended as a {"role": "system"} message.
                       Falls back to settings.llm_system_prompt if None.

    Returns:
        A single string ending with '<|im_start|>assistant\\n', which is the
        signal for the model to begin generating its response.
    """
    tokenizer = get_tokenizer()

    effective_system_prompt = system_prompt or settings.llm_system_prompt
    full_messages = [{"role": "system", "content": effective_system_prompt}] + messages

    prompt: str = tokenizer.apply_chat_template(
        full_messages,
        tokenize=False,           # Return string, not token ID list
        add_generation_prompt=True,  # Append the <|im_start|>assistant\n suffix
        enable_thinking=False,    # Disable Qwen3's internal reasoning phase
    )
    return prompt


def count_tokens(text: str) -> int:
    """
    Return the number of tokens in `text` using the loaded tokenizer.

    Called by chat_service before persisting a message so that token_count
    is always stored. Never call this inside the generation hot-path —
    it tokenizes the entire text on each call.
    """
    tokenizer = get_tokenizer()
    return len(tokenizer.encode(text))
