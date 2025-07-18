"""
Adapters package for API adapters.
"""

from src.adapters.base import APIAdapterStrategy
from src.adapters.factory import AdapterFactory

# Import all adapters to register them
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.anthropic_adapter import AnthropicAdapter
from src.adapters.gemini_adapter import GeminiAdapter
from src.adapters.deepseek_adapter import DeepSeekAdapter

# Register adapters with the factory
AdapterFactory.register_adapter('openai', OpenAIAdapter)
AdapterFactory.register_adapter('anthropic', AnthropicAdapter)
AdapterFactory.register_adapter('gemini', GeminiAdapter)
AdapterFactory.register_adapter('deepseek', DeepSeekAdapter)

# Legacy adapter registry for backward compatibility
ADAPTER_REGISTRY = {
    'openai': OpenAIAdapter,
    'anthropic': AnthropicAdapter,
    'gemini': GeminiAdapter,
    'deepseek': DeepSeekAdapter
}

def get_adapter(adapter_name: str, **kwargs) -> APIAdapterStrategy:
    """
    Get an adapter instance.
    
    This is a legacy function that uses the new factory system internally.
    
    Args:
        adapter_name: Adapter name
        **kwargs: Adapter configuration
        
    Returns:
        Adapter instance
    """
    return AdapterFactory.create_adapter(adapter_name, **kwargs)

__all__ = [
    'APIAdapterStrategy',
    'AdapterFactory',
    'get_adapter',
    'ADAPTER_REGISTRY',
    'OpenAIAdapter',
    'AnthropicAdapter',
    'GeminiAdapter',
    'DeepSeekAdapter'
]