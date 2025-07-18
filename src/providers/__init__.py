"""
Providers package for API providers.
"""

from src.providers.base import BaseProvider
from src.providers.factory import ProviderFactory

# Import all providers to register them
from src.providers.openai_provider import OpenAIProvider
from src.providers.anthropic_provider import AnthropicProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.deepseek_provider import DeepSeekProvider

# Register providers with the factory
ProviderFactory.register_provider('openai', OpenAIProvider)
ProviderFactory.register_provider('anthropic', AnthropicProvider)
ProviderFactory.register_provider('gemini', GeminiProvider)
ProviderFactory.register_provider('deepseek', DeepSeekProvider)

# Legacy provider registry for backward compatibility
PROVIDER_REGISTRY = {
    'openai': OpenAIProvider,
    'anthropic': AnthropicProvider,
    'gemini': GeminiProvider,
    'deepseek': DeepSeekProvider
}

def get_provider(provider_name: str, **kwargs) -> BaseProvider:
    """
    Get a provider instance.
    
    This is a legacy function that uses the new factory system internally.
    
    Args:
        provider_name: Provider name
        **kwargs: Provider configuration
        
    Returns:
        Provider instance
    """
    return ProviderFactory.create_provider(provider_name, **kwargs)

__all__ = [
    'BaseProvider',
    'ProviderFactory',
    'get_provider',
    'PROVIDER_REGISTRY',
    'OpenAIProvider',
    'AnthropicProvider',
    'GeminiProvider',
    'DeepSeekProvider'
]