"""
Configuration sources for the configuration system.
"""

import os
import yaml
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union


class ConfigurationSource(ABC):
    """Abstract base class for configuration sources."""
    
    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        pass
    
    @abstractmethod
    def set_value(self, key: str, value: Any) -> bool:
        """Set a configuration value by key."""
        pass
    
    @abstractmethod
    def has_key(self, key: str) -> bool:
        """Check if a key exists in this configuration source."""
        pass
    
    def get_typed_value(self, key: str, default: Any = None, value_type: str = "string") -> Any:
        """Get a typed configuration value."""
        value = self.get_value(key, default)
        
        if value is None:
            return default
        
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
        except (ValueError, TypeError, json.JSONDecodeError):
            return default


class EnvironmentConfigSource(ConfigurationSource):
    """Configuration source that reads from environment variables."""
    
    def __init__(self, prefix: str = "", case_sensitive: bool = False):
        """
        Initialize the environment configuration source.
        
        Args:
            prefix: Optional prefix for environment variables
            case_sensitive: Whether keys are case-sensitive
        """
        self.prefix = prefix
        self.case_sensitive = case_sensitive
    
    def _get_env_key(self, key: str) -> str:
        """Convert a configuration key to an environment variable name."""
        env_key = f"{self.prefix}{key}"
        if not self.case_sensitive:
            env_key = env_key.upper()
        return env_key.replace(".", "_")
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from environment variables."""
        env_key = self._get_env_key(key)
        return os.environ.get(env_key, default)
    
    def set_value(self, key: str, value: Any) -> bool:
        """Set a configuration value in environment variables."""
        env_key = self._get_env_key(key)
        os.environ[env_key] = str(value)
        return True
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists in environment variables."""
        env_key = self._get_env_key(key)
        return env_key in os.environ


class YamlConfigSource(ConfigurationSource):
    """Configuration source that reads from YAML files."""
    
    def __init__(self, file_path: str, auto_reload: bool = False):
        """
        Initialize the YAML configuration source.
        
        Args:
            file_path: Path to the YAML file
            auto_reload: Whether to reload the file on each access
        """
        self.file_path = file_path
        self.auto_reload = auto_reload
        self._config_data = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from the YAML file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading YAML config from {self.file_path}: {e}")
                self._config_data = {}
        else:
            self._config_data = {}
    
    def _get_nested_value(self, data: Dict[str, Any], key_parts: List[str]) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        if not key_parts:
            return None
        
        if len(key_parts) == 1:
            return data.get(key_parts[0])
        
        if key_parts[0] not in data or not isinstance(data[key_parts[0]], dict):
            return None
        
        return self._get_nested_value(data[key_parts[0]], key_parts[1:])
    
    def _set_nested_value(self, data: Dict[str, Any], key_parts: List[str], value: Any) -> bool:
        """Set a nested value in a dictionary using dot notation."""
        if not key_parts:
            return False
        
        if len(key_parts) == 1:
            data[key_parts[0]] = value
            return True
        
        if key_parts[0] not in data:
            data[key_parts[0]] = {}
        
        if not isinstance(data[key_parts[0]], dict):
            data[key_parts[0]] = {}
        
        return self._set_nested_value(data[key_parts[0]], key_parts[1:], value)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from the YAML file."""
        if self.auto_reload:
            self._load_config()
        
        key_parts = key.split(".")
        value = self._get_nested_value(self._config_data, key_parts)
        return value if value is not None else default
    
    def set_value(self, key: str, value: Any) -> bool:
        """Set a configuration value in the YAML file."""
        key_parts = key.split(".")
        result = self._set_nested_value(self._config_data, key_parts, value)
        
        if result:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config_data, f, default_flow_style=False)
                return True
            except Exception as e:
                print(f"Error saving YAML config to {self.file_path}: {e}")
                return False
        
        return False
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists in the YAML file."""
        if self.auto_reload:
            self._load_config()
        
        key_parts = key.split(".")
        current = self._config_data
        
        for part in key_parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        
        return True


class DatabaseConfigSource(ConfigurationSource):
    """Configuration source that reads from a database."""
    
    def __init__(self, db_service=None):
        """
        Initialize the database configuration source.
        
        Args:
            db_service: Database service for accessing configuration
        """
        self.db_service = db_service
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from the database."""
        if not self.db_service:
            return default
        
        try:
            from src.utils.db import get_system_config
            config = get_system_config(key)
            return config.config_value if config and config.config_value is not None else default
        except Exception:
            return default
    
    def set_value(self, key: str, value: Any) -> bool:
        """Set a configuration value in the database."""
        if not self.db_service:
            return False
        
        try:
            from src.utils.db import set_system_config
            set_system_config(key, str(value))
            return True
        except Exception:
            return False
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists in the database."""
        if not self.db_service:
            return False
        
        try:
            from src.utils.db import get_system_config
            config = get_system_config(key)
            return config is not None
        except Exception:
            return False