from .base import BaseProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider

# 提供商注册表
PROVIDER_REGISTRY = {
    'openai': OpenAIProvider,
    'anthropic': AnthropicProvider,
    'gemini': GeminiProvider,
    'deepseek': DeepSeekProvider
}

def get_provider(provider_name: str) -> BaseProvider:
    """获取提供商实例"""
    provider_class = PROVIDER_REGISTRY.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")
    return provider_class()

__all__ = ['BaseProvider', 'get_provider', 'PROVIDER_REGISTRY']