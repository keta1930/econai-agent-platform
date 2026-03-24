from models.model_config import ModelConfig
from services.ai.base import BaseAIAdapter


def get_adapter(model_config: ModelConfig) -> BaseAIAdapter:
    if model_config.adapter_type == "openai":
        from services.ai.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    elif model_config.adapter_type == "anthropic":
        from services.ai.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    else:
        raise ValueError(f"Unknown adapter type: {model_config.adapter_type}")
