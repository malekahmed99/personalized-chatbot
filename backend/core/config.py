from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    # API Routing
    api_prefix: str = "/api"
    allowed_origins: str = "http://localhost:5173"

    # LLM — paths
    model_path: str
    tokenizer_path: str
    # LLM — context & budget
    model_max_context: int = 8192
    chat_history_token_budget: int = 6144
    # LLM — runtime tuning
    n_threads: int = 8          # CPU threads handed to llama.cpp
    n_gpu_layers: int = 0       # 0 = CPU-only; -1 = offload all layers to GPU
    max_new_tokens: int = 2048  # Hard cap on generated tokens per response
    # LLM — stop tokens (comma-separated in .env, e.g. <|im_end|>,<|endoftext|>)
    llm_stop_tokens: list[str] = ["<|im_end|>", "<|endoftext|>"]
    # LLM — sampling parameters (Qwen3 community-established defaults)
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    llm_top_k: int = 40
    llm_repeat_penalty: float = 1.1
    llm_min_p: float = 0.05
    # LLM — system prompt (configurable without code changes)
    llm_system_prompt: str = """You are a precise, knowledgeable assistant. Follow these rules exactly.

FORMAT RULES:
- Always format responses in Markdown.
- Use numbered lists for any sequence of steps, instructions, or ranked items.
- Use bullet points for unordered collections of facts or options.
- Use headers (##, ###) to separate distinct sections in responses longer than 150 words.
- Use inline code (`like this`) for commands, variables, file names, and technical terms.
- Use fenced code blocks for any multi-line code samples.
- Use **bold** to emphasise the single most important term or action per section.
- For short factual answers (one sentence), plain prose is correct.

BEHAVIOR RULES:
- Answer immediately. Never open with filler phrases like "Sure!", "Great question!", or "Certainly!".
- Never restate the question before answering it.
- Never summarise what you just said at the end of a response.
- If you do not know something, say so plainly. Never fabricate information.
- Be concise. Include everything necessary; omit everything else.
"""

    # Database
    db_url: str

    # Auth / JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 7

    # App
    debug: bool = False
    cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("llm_stop_tokens", mode="before")
    @classmethod
    def parse_stop_tokens(cls, v) -> list[str]:
        if isinstance(v, list):
            return v  # already a list (e.g. injected in tests)
        if isinstance(v, str):
            return [token.strip() for token in v.split(",") if token.strip()]
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v) -> str:
        return v if v else ""

    def get_allowed_origins(self) -> List[str]:
        """Returns allowed_origins as a Python list. Use this in main.py."""
        if not self.allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

# Singleton instance to be used across the project
settings = Settings()

@lru_cache()
def get_settings() -> Settings:
    """Factory for backward compatibility."""
    return settings
