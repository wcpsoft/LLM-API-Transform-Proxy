from typing import Any, Dict, List
from abc import ABC, abstractmethod

class APIAdapterStrategy(ABC):
    """API适配器策略基类"""
    
    @abstractmethod
    def adapt_request(self, request: Dict[str, Any], target_model: str = None) -> Dict[str, Any]:
        """适配请求数据"""
        raise NotImplementedError
    
    @abstractmethod
    def adapt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """适配响应数据"""
        raise NotImplementedError
    
    def adapt_stream_response(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """适配流式响应数据块"""
        # 默认实现，子类可以重写
        return chunk
    
    def supports_multimodal(self) -> bool:
        """是否支持多模态"""
        return False
    
    def process_multimodal_content(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理多模态内容"""
        # 默认实现，直接返回原内容
        return content

# 插件注册表
ADAPTER_REGISTRY = {}

def register_adapter(name: str, adapter_cls):
    ADAPTER_REGISTRY[name] = adapter_cls

def get_adapter(name: str) -> APIAdapterStrategy:
    adapter_cls = ADAPTER_REGISTRY.get(name)
    if not adapter_cls:
        raise ValueError(f"No adapter registered for {name}")
    return adapter_cls()