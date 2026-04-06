import logging

from models.model_config import ModelConfig
from services.ai.base import BaseAIAdapter

logger = logging.getLogger(__name__)


def get_adapter(model_config: ModelConfig) -> BaseAIAdapter:
    if model_config.adapter_type == "openai":
        from services.ai.openai_adapter import OpenAIAdapter
        logger.info("创建 OpenAI 适配器 — 模型=%s", model_config.name)
        return OpenAIAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    elif model_config.adapter_type == "anthropic":
        from services.ai.anthropic_adapter import AnthropicAdapter
        logger.info("创建 Anthropic 适配器 — 模型=%s", model_config.name)
        return AnthropicAdapter(
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_name=model_config.name,
        )
    else:
        raise ValueError(f"Unknown adapter type: {model_config.adapter_type}")
