"""
Singleton instance of the configuration manager.
"""

import os
from src.core.config.manager import ConfigurationManager
from src.core.config.sources import (
    EnvironmentConfigSource,
    YamlConfigSource,
    DatabaseConfigSource
)

# Create the configuration sources
env_source = EnvironmentConfigSource()

# Determine the path to the config files
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
app_config_path = os.path.join(base_dir, 'config', 'app.yml')
yaml_source = YamlConfigSource(app_config_path, auto_reload=True)

# Database source will be initialized later when the database is available
db_source = DatabaseConfigSource()

# Create the configuration manager with sources in order of precedence
# (environment variables override YAML config, which overrides database config)
config_manager = ConfigurationManager([
    env_source,
    yaml_source,
    db_source
])

# Export the singleton instance
def get_config_manager() -> ConfigurationManager:
    """Get the singleton configuration manager instance."""
    return config_manager