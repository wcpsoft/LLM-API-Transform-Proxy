import os
import yaml
import json
from typing import Dict, List, Optional
from src.utils.api_key_manager import api_key_manager

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'app.yml')

def load_yaml_config(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

_yaml_config = load_yaml_config(CONFIG_PATH)

def get_config(key, default=None):
    return os.environ.get(key) or _yaml_config.get(key, default)

# 全局配置
MODE = get_config("MODE", "transformer").lower()
PREFERRED_PROVIDER = get_config("PREFERRED_PROVIDER", "openai").lower()

def init_api_key_pools():
    """初始化API密钥池"""
    api_key_pools = _yaml_config.get("API_KEY_POOLS", {})
    
    for provider, config in api_key_pools.items():
        keys = config.get("keys", [])
        if keys:
            api_key_manager.add_keys(provider, keys)
    
    # 向后兼容：添加单个密钥到池中
    legacy_keys = {
        "openai": get_config("OPENAI_API_KEY"),
        "anthropic": get_config("ANTHROPIC_API_KEY"), 
        "gemini": get_config("GEMINI_API_KEY")
    }
    
    for provider, key in legacy_keys.items():
        if key and key != f"你的{provider.title()}密钥":
            api_key_manager.add_keys(provider, [key])

def get_api_key_config(provider: str) -> Dict:
    """获取API密钥配置"""
    api_key_pools = _yaml_config.get("API_KEY_POOLS", {})
    
    if provider in api_key_pools:
        return api_key_pools[provider]
    
    # 向后兼容
    legacy_key = get_config(f"{provider.upper()}_API_KEY")
    if legacy_key:
        return {
            "keys": [legacy_key],
            "auth_header": "Authorization" if provider != "anthropic" else "x-api-key",
            "auth_format": "Bearer {key}" if provider != "anthropic" else "{key}"
        }
    
    return {}

def get_route_api_keys(route_config: Dict) -> Optional[List[str]]:
    """获取路由专用API密钥"""
    return route_config.get("api_keys")

def get_route_auth_config(route_config: Dict) -> Dict:
    """获取路由认证配置"""
    return {
        "auth_header": route_config.get("auth_header", "Authorization"),
        "auth_format": route_config.get("auth_format", "Bearer {key}")
    }

ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
GEMINI_API_KEY = get_config("GEMINI_API_KEY")

# 新增：模型映射和指令转发配置


OPENAI_MODELS = [
    "o3-mini", "o1", "o1-mini", "o1-pro", "gpt-4.5-preview", "gpt-4o", "gpt-4o-audio-preview",
    "chatgpt-4o-latest", "gpt-4o-mini", "gpt-4o-mini-audio-preview", "gpt-4.1", "gpt-4.1-mini"
]
GEMINI_MODELS = [
    "gemini-2.5-pro-preview-03-25", "gemini-2.0-flash"
]

def get_mode():
    return _yaml_config.get("MODE", "transformer")

def get_system_config_value(key: str, default=None, config_type: str = "string"):
    """从数据库获取系统配置值"""
    try:
        from src.utils.db import get_system_config
        config = get_system_config(key)
        if config and config.config_value is not None:
            value = config.config_value
            # 根据类型转换值
            if config_type == "int":
                return int(value)
            elif config_type == "bool":
                return value.lower() in ("true", "1", "yes", "on")
            elif config_type == "json":
                return json.loads(value)
            else:
                return value
        return default
    except Exception:
        # 如果数据库不可用，回退到默认值
        return default

def get_host():
    """获取服务器主机地址"""
    return get_system_config_value("server.host", get_config("HOST", "0.0.0.0"))

def get_port():
    """获取服务器端口"""
    return get_system_config_value("server.port", get_config("PORT", 8082), "int")

def get_debug():
    """获取调试模式"""
    return get_system_config_value("server.debug", get_config("DEBUG", False), "bool")

def get_admin_auth_key():
    """获取管理API认证密钥"""
    return get_system_config_value("auth.admin_key", get_config("ADMIN_AUTH_KEY", ""))

def get_structured_logging():
    """获取是否启用结构化日志"""
    return get_system_config_value("logging.structured", True, "bool")

def get_logging_level():
    """获取日志级别"""
    return get_system_config_value("logging.level", "INFO")

# 初始化API密钥池
init_api_key_pools()

def get_all_models_and_providers(group_by_provider=False, with_model_map=False):
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

def get_db_config():
    db_yml = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'db.yml')
    if os.path.exists(db_yml):
        conf = yaml.safe_load(open(db_yml, 'r', encoding='utf-8')).get('duckdb', {})
        # 强制路径为db/api_log.duckdb
        conf['path'] = os.path.join('db', 'api_log.duckdb')
        return conf
    return {"path": os.path.join('db', 'api_log.duckdb'), "user": "", "password": ""}