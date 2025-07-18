"""
Configuration manager for the configuration system.
"""

from typing import Any, Dict, List, Optional, Union
from src.core.config.sources import ConfigurationSource


class ConfigurationManager:
    """
    Configuration manager that coordinates multiple configuration sources.
    
    The manager maintains a list of configuration sources with a defined
    precedence order. When retrieving a value, it checks each source in
    order until it finds the requested key.
    """
    
    def __init__(self, sources: Optional[List[ConfigurationSource]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            sources: List of configuration sources in order of precedence
                    (highest precedence first)
        """
        self.sources = sources or []
    
    def add_source(self, source: ConfigurationSource, index: int = None) -> None:
        """
        Add a configuration source.
        
        Args:
            source: The configuration source to add
            index: Optional index to insert the source at (None = append)
        """
        if index is None:
            self.sources.append(source)
        else:
            self.sources.insert(index, source)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key
            default: Default value if the key is not found
            
        Returns:
            The configuration value or the default
        """
        for source in self.sources:
            if source.has_key(key):
                value = source.get_value(key)
                if value is not None:
                    return value
        
        return default
    
    def get_typed_value(self, key: str, default: Any = None, value_type: str = "string") -> Any:
        """
        Get a typed configuration value.
        
        Args:
            key: The configuration key
            default: Default value if the key is not found
            value_type: Type to convert the value to (string, int, bool, json, list)
            
        Returns:
            The typed configuration value or the default
        """
        value = self.get_value(key, default)
        
        # If we got the default value, return it as is
        if value is default:
            return default
        
        # Use the first source that has type conversion to convert the value
        for source in self.sources:
            if hasattr(source, 'get_typed_value'):
                return source.get_typed_value(key, default, value_type)
        
        # Fallback to basic type conversion
        try:
            if value_type == "int":
                return int(value)
            elif value_type == "float":
                return float(value)
            elif value_type == "bool":
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes", "on")
            elif value_type == "json":
                import json
                if isinstance(value, (dict, list)):
                    return value
                return json.loads(value)
            elif value_type == "list":
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return value.split(",")
                return [value]
            else:
                return str(value)
        except (ValueError, TypeError):
            return default
    
    def set_value(self, key: str, value: Any, source_index: int = 0) -> bool:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key
            value: The value to set
            source_index: Index of the source to set the value in
            
        Returns:
            True if the value was set successfully, False otherwise
        """
        if not self.sources or source_index >= len(self.sources):
            return False
        
        return self.sources[source_index].set_value(key, value)
    
    def has_key(self, key: str) -> bool:
        """
        Check if a key exists in any configuration source.
        
        Args:
            key: The configuration key
            
        Returns:
            True if the key exists, False otherwise
        """
        return any(source.has_key(key) for source in self.sources)
    
    def get_all_values(self) -> Dict[str, Any]:
        """
        Get all configuration values from all sources.
        
        Returns:
            Dictionary of all configuration values
        """
        # This is a simplified implementation that doesn't handle nested keys
        # A more complete implementation would need to merge nested dictionaries
        result = {}
        
        # Process sources in reverse order so higher precedence sources override lower ones
        for source in reversed(self.sources):
            # This assumes each source can provide all its keys, which might not be true
            # for all source types (e.g., environment variables)
            if hasattr(source, 'get_all_values'):
                result.update(source.get_all_values())
        
        return result