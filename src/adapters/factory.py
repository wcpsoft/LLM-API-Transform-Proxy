"""
Adapter factory for creating adapter instances.
"""

from typing import Dict, Type, Any, Optional
from src.adapters.base import APIAdapterStrategy
from src.core.errors.exceptions import ConfigurationError
from src.utils.logging import logger


class AdapterFactory:
    """
    Factory for creating adapter instances.
    
    This class manages the registration and creation of adapter instances,
    allowing for dynamic adapter discovery and instantiation.
    """
    
    # Registry of adapter classes
    _registry: Dict[str, Type[APIAdapterStrategy]] = {}
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[APIAdapterStrategy]) -> None:
        """
        Register an adapter class.
        
        Args:
            name: Adapter name
            adapter_class: Adapter class
        """
        cls._registry[name.lower()] = adapter_class
        logger.debug(f"Registered adapter: {name}")
    
    @classmethod
    def create_adapter(
        cls,
        adapter_name: str,
        **kwargs
    ) -> APIAdapterStrategy:
        """
        Create an adapter instance.
        
        Args:
            adapter_name: Adapter name
            **kwargs: Additional adapter-specific arguments
            
        Returns:
            Adapter instance
            
        Raises:
            ConfigurationError: If the adapter is not registered
        """
        adapter_name = adapter_name.lower()
        
        if adapter_name not in cls._registry:
            raise ConfigurationError(
                message=f"Adapter '{adapter_name}' is not registered",
                config_key="adapter",
                details={"available_adapters": list(cls._registry.keys())}
            )
        
        adapter_class = cls._registry[adapter_name]
        
        try:
            return adapter_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to create adapter '{adapter_name}': {str(e)}",
                config_key="adapter",
                details={"adapter": adapter_name, "error": str(e)}
            )
    
    @classmethod
    def get_registered_adapters(cls) -> Dict[str, Type[APIAdapterStrategy]]:
        """
        Get all registered adapters.
        
        Returns:
            Dictionary of adapter names to adapter classes
        """
        return cls._registry.copy()
    
    @classmethod
    def is_adapter_registered(cls, name: str) -> bool:
        """
        Check if an adapter is registered.
        
        Args:
            name: Adapter name
            
        Returns:
            True if the adapter is registered, False otherwise
        """
        return name.lower() in cls._registry
    
    @classmethod
    def get_adapter_for_provider(cls, provider_name: str) -> Optional[APIAdapterStrategy]:
        """
        Get an adapter for a provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Adapter instance or None if no adapter is found
        """
        # Try to find an adapter with the same name as the provider
        if cls.is_adapter_registered(provider_name):
            return cls.create_adapter(provider_name)
        
        # If no adapter is found, return None
        return None