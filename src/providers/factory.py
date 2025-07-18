"""
Provider factory for creating provider instances.
"""

from typing import Dict, Any, Type, Optional
from src.providers.base import BaseProvider
from src.core.errors.exceptions import ConfigurationError
from src.utils.logging import logger


class ProviderFactory:
    """
    Factory for creating provider instances.
    
    This class manages the registration and creation of provider instances,
    allowing for dynamic provider discovery and instantiation.
    """
    
    # Registry of provider classes
    _registry: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        Register a provider class.
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls._registry[name.lower()] = provider_class
        logger.debug(f"Registered provider: {name}")
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        api_key: str,
        api_base: Optional[str] = None,
        auth_header: Optional[str] = None,
        auth_format: Optional[str] = None,
        **kwargs
    ) -> BaseProvider:
        """
        Create a provider instance.
        
        Args:
            provider_name: Provider name
            api_key: API key
            api_base: API base URL
            auth_header: Authentication header name
            auth_format: Authentication format
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Provider instance
            
        Raises:
            ConfigurationError: If the provider is not registered
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._registry:
            raise ConfigurationError(
                message=f"Provider '{provider_name}' is not registered",
                config_key="provider",
                details={"available_providers": list(cls._registry.keys())}
            )
        
        provider_class = cls._registry[provider_name]
        
        # Create provider instance with the specified configuration
        provider_args = {
            "api_key": api_key,
            "api_base": api_base
        }
        
        # Add optional arguments if provided
        if auth_header:
            provider_args["auth_header"] = auth_header
        
        if auth_format:
            provider_args["auth_format"] = auth_format
        
        # Add any additional provider-specific arguments
        provider_args.update(kwargs)
        
        try:
            return provider_class(**provider_args)
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to create provider '{provider_name}': {str(e)}",
                config_key="provider",
                details={"provider": provider_name, "error": str(e)}
            )
    
    @classmethod
    def get_registered_providers(cls) -> Dict[str, Type[BaseProvider]]:
        """
        Get all registered providers.
        
        Returns:
            Dictionary of provider names to provider classes
        """
        return cls._registry.copy()
    
    @classmethod
    def is_provider_registered(cls, name: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            name: Provider name
            
        Returns:
            True if the provider is registered, False otherwise
        """
        return name.lower() in cls._registry