"""
弹性配置 - 错误处理和降级配置
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import yaml
import os


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2
    name: str = "default"


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl: int = 300
    fallback_ttl: int = 60
    max_size: int = 1000


@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    enabled: bool = True
    interval: float = 30.0
    timeout: float = 10.0
    retries: int = 3


@dataclass
class DegradationConfig:
    """降级配置"""
    enabled: bool = True
    timeout: float = 30.0
    use_cache: bool = True
    mock_responses: bool = True
    fallback_priority: int = 1


@dataclass
class ServiceConfig:
    """服务特定配置"""
    retry: RetryConfig
    circuit_breaker: CircuitBreakerConfig
    cache: CacheConfig
    health_check: HealthCheckConfig
    degradation: DegradationConfig


class ResilienceConfig:
    """弹性配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv(
            "RESILIENCE_CONFIG_PATH", 
            "config/resilience.yaml"
        )
        self.services: Dict[str, ServiceConfig] = {}
        self.global_config = self._load_default_config()
        self._load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "retry": RetryConfig(),
            "circuit_breaker": CircuitBreakerConfig(),
            "cache": CacheConfig(),
            "health_check": HealthCheckConfig(),
            "degradation": DegradationConfig()
        }
    
    def _load_config(self):
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # 加载全局配置
                if "global" in config_data:
                    self._update_config_from_dict(
                        self.global_config, 
                        config_data["global"]
                    )
                
                # 加载服务特定配置
                for service_name, service_config in config_data.get("services", {}).items():
                    service_obj = ServiceConfig(
                        retry=RetryConfig(**service_config.get("retry", {})),
                        circuit_breaker=CircuitBreakerConfig(**service_config.get("circuit_breaker", {})),
                        cache=CacheConfig(**service_config.get("cache", {})),
                        health_check=HealthCheckConfig(**service_config.get("health_check", {})),
                        degradation=DegradationConfig(**service_config.get("degradation", {}))
                    )
                    self.services[service_name] = service_obj
                    
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
    
    def _update_config_from_dict(self, config_obj: Any, config_dict: Dict[str, Any]):
        """从字典更新配置对象"""
        for key, value in config_dict.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
    
    def get_service_config(self, service_name: str) -> ServiceConfig:
        """获取服务配置"""
        return self.services.get(service_name, ServiceConfig(
            retry=self.global_config["retry"],
            circuit_breaker=self.global_config["circuit_breaker"],
            cache=self.global_config["cache"],
            health_check=self.global_config["health_check"],
            degradation=self.global_config["degradation"]
        ))
    
    def save_config(self):
        """保存配置到文件"""
        config_data = {
            "global": {
                "retry": asdict(self.global_config["retry"]),
                "circuit_breaker": asdict(self.global_config["circuit_breaker"]),
                "cache": asdict(self.global_config["cache"]),
                "health_check": asdict(self.global_config["health_check"]),
                "degradation": asdict(self.global_config["degradation"])
            },
            "services": {}
        }
        
        for service_name, service_config in self.services.items():
            config_data["services"][service_name] = {
                "retry": asdict(service_config.retry),
                "circuit_breaker": asdict(service_config.circuit_breaker),
                "cache": asdict(service_config.cache),
                "health_check": asdict(service_config.health_check),
                "degradation": asdict(service_config.degradation)
            }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def update_service_config(self, service_name: str, **kwargs):
        """更新服务配置"""
        if service_name not in self.services:
            self.services[service_name] = self.get_service_config(service_name)
        
        for key, value in kwargs.items():
            if hasattr(self.services[service_name], key):
                setattr(self.services[service_name], key, value)


# 全局配置实例
resilience_config = ResilienceConfig()


# 示例配置文件内容
def create_example_config():
    """创建示例配置文件"""
    example_config = {
        "global": {
            "retry": {
                "max_retries": 3,
                "base_delay": 1.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0,
                "jitter": True
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 60.0,
                "success_threshold": 2,
                "name": "default"
            },
            "cache": {
                "enabled": True,
                "ttl": 300,
                "fallback_ttl": 60,
                "max_size": 1000
            },
            "health_check": {
                "enabled": True,
                "interval": 30.0,
                "timeout": 10.0,
                "retries": 3
            },
            "degradation": {
                "enabled": True,
                "timeout": 30.0,
                "use_cache": True,
                "mock_responses": True,
                "fallback_priority": 1
            }
        },
        "services": {
            "openai": {
                "retry": {"max_retries": 5, "base_delay": 2.0},
                "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 120.0},
                "cache": {"ttl": 600, "max_size": 500},
                "degradation": {"timeout": 15.0}
            },
            "anthropic": {
                "retry": {"max_retries": 4, "base_delay": 1.5},
                "circuit_breaker": {"failure_threshold": 4, "recovery_timeout": 90.0},
                "cache": {"ttl": 300, "max_size": 200}
            }
        }
    }
    
    os.makedirs("config", exist_ok=True)
    with open("config/resilience.yaml", "w", encoding="utf-8") as f:
        yaml.dump(example_config, f, default_flow_style=False, allow_unicode=True)


if __name__ == "__main__":
    create_example_config()
    print("示例配置文件已创建: config/resilience.yaml")