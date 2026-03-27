from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    aws_region: str = "us-east-1"

    dynamodb_table_name: str = "tool_results"
    dynamodb_endpoint_url: str | None = None

    backend_port: int = 8080
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"

    chunk_token_budget: int = 10_000

    # Should be below your org's TPM limit with headroom for the LLM response.
    max_context_tokens: int = 25_000
    recent_turns_to_preserve: int = 5

    user_id: str = "default"

    s3_results_bucket: str = ""
    s3_presigned_url_expiry: int = 3600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
