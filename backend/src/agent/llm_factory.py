from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from config import get_settings


def create_llm() -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    match provider:
        case "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                streaming=True,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                streaming=True,
            )
        case "bedrock":
            from langchain_aws import ChatBedrock
            return ChatBedrock(
                model_id=settings.openai_model,
                region_name=settings.aws_region,
                streaming=True,
            )
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")
