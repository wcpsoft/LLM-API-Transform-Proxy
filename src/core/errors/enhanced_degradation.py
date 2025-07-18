"""
增强的优雅降级系统 - 集成所有改进功能
"""
import asyncio
from typing import Any, Dict, Optional
import logging

from .graceful_degradation import fallback_handler, graceful_degradation
from .enhanced_retry import EnhancedRetryHandler
from .error_context import ErrorContext
from src.core.health.health_checker import health_checker

logger = logging.getLogger(__name__)


class EnhancedDegradationManager:
    """增强的降级管理器"""
    
    def __init__(self):
        self.retry_handler = EnhancedRetryHandler()
        self.fallback_handler = fallback_handler
        
    async def execute_with_full_resilience(
        self,
        service_name: str,
        primary_func: callable,
        *args,
        max_retries: int = 3,
        fallback_func: callable = None,
        use_cache: bool = True,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行具有完整弹性的操作
        
        包含：重试、熔断、降级、缓存、健康检查
        """
        
        # 注册健康检查
        health_checker.register_service(
            service_name,
            lambda: self._health_check(service_name)
        )
        
        # 注册降级函数
        if fallback_func:
            fallback_handler.register_fallback(
                service_name,
                fallback_func,
                priority=1
            )
        
        # 使用重试装饰器
        @self.retry_handler.retry(
            max_retries=max_retries,
            service_name=service_name
        )
        async def _execute_with_retry():
            return await fallback_handler.execute_with_fallback(
                service_name,
                primary_func,
                *args,
                use_cache=use_cache,
                **kwargs
            )
        
        try:
            return await asyncio.wait_for(
                _execute_with_retry(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"操作超时: {service_name}")
            
            # 超时降级
            if fallback_func:
                result = await fallback_func(*args, **kwargs)
                return {
                    "data": result,
                    "source": "timeout_fallback",
                    "degraded": True,
                    "cached": False
                }
            raise
    
    def _health_check(self, service_name: str) -> bool:
        """健康检查"""
        # 这里可以添加具体的健康检查逻辑
        return True
    
    def get_service_metrics(self, service_name: str) -> Dict[str, Any]:
        """获取服务指标"""
        return {
            "health_status": health_checker.get_service_status(service_name),
            "fallbacks_registered": len(fallback_handler.fallbacks.get(service_name, [])),
            "cache_size": len(fallback_handler.cache)
        }


# 全局实例
enhanced_degradation_manager = EnhancedDegradationManager()


# 便捷装饰器
def resilient_operation(
    service_name: str,
    max_retries: int = 3,
    fallback_func: callable = None,
    use_cache: bool = True,
    timeout: float = 30.0
):
    """弹性操作装饰器"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await enhanced_degradation_manager.execute_with_full_resilience(
                service_name=service_name,
                primary_func=func,
                max_retries=max_retries,
                fallback_func=fallback_func,
                use_cache=use_cache,
                timeout=timeout,
                *args,
                **kwargs
            )
        return wrapper
    return decorator


# 示例使用
if __name__ == "__main__":
    
    async def example_usage():
        """示例用法"""
        
        # 定义主函数
        async def chat_completion_service(prompt: str) -> str:
            # 模拟API调用
            if "error" in prompt:
                raise Exception("API调用失败")
            return f"回复: {prompt}"
        
        # 定义降级函数
        async def mock_response(prompt: str) -> str:
            return f"这是模拟回复: {prompt}"
        
        # 使用装饰器
        @resilient_operation(
            service_name="chat_completion",
            max_retries=2,
            fallback_func=mock_response,
            timeout=10.0
        )
        async def resilient_chat_completion(prompt: str) -> Dict[str, Any]:
            return await chat_completion_service(prompt)
        
        # 执行
        try:
            result = await resilient_chat_completion("你好")
            print(f"结果: {result}")
        except Exception as e:
            print(f"错误: {e}")
    
    # 运行示例
    asyncio.run(example_usage())