from app.core.config import get_settings
from app.llm.mock import MockLLMClient
from app.llm.openai_compatible import OpenAICompatibleLLMClient


def build_llm_client(model_name: str | None = None):
    settings = get_settings()
    if settings.llm_provider.lower() == "mock":
        return MockLLMClient()
    if settings.llm_provider.lower() in {"openai", "openai_compatible"}:
        return OpenAICompatibleLLMClient(model_name=model_name)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
