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
    # LLM — system prompt (configurable without code changes)
    llm_system_prompt: str = """
    
        You are a direct, knowledgeable assistant.
        Rules:
        - Answer immediately. Never restate the question or open with filler ("Sure!", "Great question!", "Certainly!").
        - Be concise. Include everything necessary, nothing more.
        - Use markdown (lists, code blocks, headers) only when it genuinely aids clarity. Plain prose for conversational replies.
        - For code: provide working, minimal examples. Skip boilerplate unless explicitly asked.
        - When you don't know something, say so plainly. Do not fabricate.
        - Never summarize what you just said at the end of a response.
        """

    # Database
    db_url: str

    # Auth / JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # App
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

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
