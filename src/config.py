"""
Configuration module for the application.

This module provides a unified interface for accessing configuration values
from various sources (environment variables, YAML files, database).
"""

import os
import json
from typing import Dict, List, Optional, Any, Union

from src.core.config.instance import get_config_manager
from src.utils.api_key_manager import api_key_manager

# Get the configuration manager
config_manager = get_config_manager()

def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value.
    
    Args:
        key: The configuration key
        default: Default value if the key is not found
        
    Returns:
        The configuration value or the default
    """
    return config_manager.get_value(key, default)

def get_typed_config(key: str, default: Any = None, value_type: str = "string") -> Any:
    """
    Get a typed configuration value.
    
    Args:
        key: The configuration key
        default: Default value if the key is not found
        value_type: Type to convert the value to (string, int, bool, json, list)
        
    Returns:
        The typed configuration value or the default
    """
    return config_manager.get_typed_value(key, default, value_type)

# Global configuration values
MODE = get_typed_config("MODE", "transformer", "string").lower()
PREFERRED_PROVIDER = get_typed_config("PREFERRED_PROVIDER", "openai", "string").lower()

# Legacy API keys for backward compatibility
ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
GEMINI_API_KEY = get_config("GEMINI_API_KEY")

# Model lists
OPENAI_MODELS = [
    "o3-mini", "o1", "o1-mini", "o1-pro", "gpt-4.5-preview", "gpt-4o", "gpt-4o-audio-preview",
    "chatgpt-4o-latest", "gpt-4o-mini", "gpt-4o-mini-audio-preview", "gpt-4.1", "gpt-4.1-mini"
]
GEMINI_MODELS = [
    "gemini-2.5-pro-preview-03-25", "gemini-2.0-flash"
]

def init_api_key_pools():
    """Initialize API key pools from configuration."""
    # Get API key pools from configuration
    api_key_pools = get_config("API_KEY_POOLS", {})
    
    # Add keys from pools
    for provider, config in api_key_pools.items():
        keys = config.get("keys", [])
        if keys:
            api_key_manager.add_keys(provider, keys)
    
    # Add legacy keys for backward compatibility
    legacy_keys = {
        "openai": get_config("OPENAI_API_KEY"),
        "anthropic": get_config("ANTHROPIC_API_KEY"), 
        "gemini": get_config("GEMINI_API_KEY")
    }
    
    for provider, key in legacy_keys.items():
        if key and key != f"你的{provider.title()}密钥":
            api_key_manager.add_keys(provider, [key])

def get_api_key_config(provider: str) -> Dict:
    """
    Get API key configuration for a provider.
    
    Args:
        provider: The provider name
        
    Returns:
        Dictionary with API key configuration
    """
    api_key_pools = get_config("API_KEY_POOLS", {})
    
    if provider in api_key_pools:
        return api_key_pools[provider]
    
    # Backward compatibility
    legacy_key = get_config(f"{provider.upper()}_API_KEY")
    if legacy_key:
        return {
            "keys": [legacy_key],
            "auth_header": "Authorization" if provider != "anthropic" else "x-api-key",
            "auth_format": "Bearer {key}" if provider != "anthropic" else "{key}"
        }
    
    return {}

def get_route_api_keys(route_config: Dict) -> Optional[List[str]]:
    """
    Get API keys for a specific route.
    
    Args:
        route_config: Route configuration dictionary
        
    Returns:
        List of API keys or None
    """
    return route_config.get("api_keys")

def get_route_auth_config(route_config: Dict) -> Dict:
    """
    Get authentication configuration for a route.
    
    Args:
        route_config: Route configuration dictionary
        
    Returns:
        Dictionary with authentication configuration
    """
    return {
        "auth_header": route_config.get("auth_header", "Authorization"),
        "auth_format": route_config.get("auth_format", "Bearer {key}")
    }

def get_mode() -> str:
    """
    Get the application mode.
    
    Returns:
        Application mode (transformer or direct)
    """
    return get_config("MODE", "transformer")

def get_system_config_value(key: str, default: Any = None, config_type: str = "string") -> Any:
    """
    Get a system configuration value from the database.
    
    This is a legacy function that uses the new configuration system internally.
    
    Args:
        key: The configuration key
        default: Default value if the key is not found
        config_type: Type to convert the value to (string, int, bool, json)
        
    Returns:
        The configuration value or the default
    """
    return get_typed_config(key, default, config_type)

def get_host() -> str:
    """
    Get the server host address.
    
    Returns:
        Server host address
    """
    return get_typed_config("server.host", get_config("HOST", "0.0.0.0"), "string")

def get_port() -> int:
    """
    Get the server port.
    
    Returns:
        Server port
    """
    return get_typed_config("server.port", get_config("PORT", 8082), "int")

def get_debug() -> bool:
    """
    Get the debug mode.
    
    Returns:
        True if debug mode is enabled, False otherwise
    """
    return get_typed_config("server.debug", get_config("DEBUG", False), "bool")

def get_admin_auth_key() -> str:
    """
    Get the admin API authentication key.
    
    Returns:
        Admin API authentication key
    """
    return get_typed_config("auth.admin_key", get_config("ADMIN_AUTH_KEY", ""), "string")

def get_structured_logging() -> bool:
    """
    Get whether structured logging is enabled.
    
    Returns:
        True if structured logging is enabled, False otherwise
    """
    return get_typed_config("logging.structured", True, "bool")

def get_logging_level() -> str:
    """
    Get the logging level.
    
    Returns:
        Logging level
    """
    return get_typed_config("logging.level", "INFO", "string")

def get_all_models_and_providers(group_by_provider: bool = False, with_model_map: bool = False) -> Union[List[Dict], Dict]:
    """
    Get all models and providers.
    
    Args:
        group_by_provider: Whether to group models by provider
        with_model_map: Whether to include a model-to-route mapping
        
    Returns:
        List of models or dictionary with models and mappings
    """
    from src.utils.db import list_model_configs
    configs = list_model_configs()
    models = []
    provider_map = {}
    model_to_route = {}
    
    for config in configs:
        if config.enabled:
            entry = {
                "route_key": config.route_key,
                "target_model": config.target_model,
                "provider": config.provider,
                "prompt_keywords": config.prompt_keywords or []
            }
            models.append(entry)
            provider = config.provider
            if provider:
                provider_map.setdefault(provider, []).append(entry)
            model_to_route[config.target_model] = config.route_key
    
    if group_by_provider and with_model_map:
        return {"by_provider": provider_map, "model_to_route": model_to_route}
    if group_by_provider:
        return provider_map
    if with_model_map:
        return {"models": models, "model_to_route": model_to_route}
    return models

def get_db_config() -> Dict[str, Any]:
    """
    Get the database configuration.
    
    Returns:
        Dictionary with database configuration
    """
    # Try to load from YAML file first
    base_dir = os.path.dirname(os.path.dirname(__file__))
    db_yml = os.path.join(base_dir, 'config', 'db.yml')
    
    if os.path.exists(db_yml):
        try:
            import yaml
            conf = yaml.safe_load(open(db_yml, 'r', encoding='utf-8')).get('duckdb', {})
            # Force path to db/api_log.duckdb
            conf['path'] = os.path.join('db', 'api_log.duckdb')
            return conf
        except Exception:
            pass
    
    # Default configuration
    return {"path": os.path.join('db', 'api_log.duckdb'), "user": "", "password": ""}

# Initialize API key pools
init_api_key_pools()