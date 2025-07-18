"""
增强的重试装饰器 - 集成熔断器、健康检查和错误日志
"""
import asyncio
import functools
import time
from typing import Any, Callable, Optional, Dict
from functools import wraps

from src.core.errors.retry_handler import RetryConfig, CircuitBreaker, RetryStrategy
from src.core.errors.error_logger import error_logger, error_metrics
from src.core.health.health_checker import health_checker


class EnhancedRetryHandler:
    """增强的重试处理器"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout,
                success_threshold=2,
                name=name
            )
        return self.circuit_breakers[name]
    
    def retry_with_circuit_breaker(
        self,
        max_retries: int = None,
        base_delay: float = None,
        strategy: RetryStrategy = None,
        circuit_breaker_name: str = None,
        fallback_func: Callable = None,
        health_check_before_retry: bool = True
    ):
        """
        带熔断器的重试装饰器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
            strategy: 重试策略
            circuit_breaker_name: 熔断器名称
            fallback_func: 降级函数
            health_check_before_retry: 重试前是否检查健康状态
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_retry(
                    func, args, kwargs, max_retries, base_delay, 
                    strategy, circuit_breaker_name, fallback_func,
                    health_check_before_retry
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_sync_with_retry(
                    func, args, kwargs, max_retries, base_delay,
                    strategy, circuit_breaker_name, fallback_func,
                    health_check_before_retry
                )
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def _execute_with_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        max_retries: int,
        base_delay: float,
        strategy: RetryStrategy,
        circuit_breaker_name: str,
        fallback_func: Callable,
        health_check_before_retry: bool
    ) -> Any:
        """异步执行带重试的逻辑"""
        max_retries = max_retries or self.config.max_retries
        base_delay = base_delay or self.config.base_delay
        strategy = strategy or self.config.strategy
        circuit_breaker_name = circuit_breaker_name or func.__name__
        
        circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
        
        # 检查熔断器状态
        if not circuit_breaker.can_execute():
            if fallback_func:
                return await fallback_func(*args, **kwargs)
            raise Exception(f"Circuit breaker is open for {circuit_breaker_name}")
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # 重试前健康检查
                if attempt > 0 and health_check_before_retry:
                    service_status = await health_checker.check_provider_health("default")
                    if service_status.status == "unhealthy":
                        logger.warning(f"Service unhealthy, skipping retry {attempt}")
                        break
                
                result = await func(*args, **kwargs)
                circuit_breaker.call_succeeded()
                
                # 记录成功指标
                error_metrics.record_success(circuit_breaker_name)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 记录错误
                error_logger.log_error(
                    e,
                    context={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "circuit_breaker": circuit_breaker_name
                    }
                )
                
                if attempt == max_retries:
                    circuit_breaker.call_failed(str(e))
                    break
                
                # 计算延迟
                delay = self._calculate_delay(attempt, base_delay, strategy)
                await asyncio.sleep(delay)
        
        if fallback_func:
            return await fallback_func(*args, **kwargs)
        
        raise last_exception
    
    def _execute_sync_with_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        max_retries: int,
        base_delay: float,
        strategy: RetryStrategy,
        circuit_breaker_name: str,
        fallback_func: Callable,
        health_check_before_retry: bool
    ) -> Any:
        """同步执行带重试的逻辑"""
        max_retries = max_retries or self.config.max_retries
        base_delay = base_delay or self.config.base_delay
        strategy = strategy or self.config.strategy
        circuit_breaker_name = circuit_breaker_name or func.__name__
        
        circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
        
        if not circuit_breaker.can_execute():
            if fallback_func:
                return fallback_func(*args, **kwargs)
            raise Exception(f"Circuit breaker is open for {circuit_breaker_name}")
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                circuit_breaker.call_succeeded()
                return result
                
            except Exception as e:
                last_exception = e
                
                error_logger.log_error(
                    e,
                    context={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "circuit_breaker": circuit_breaker_name
                    }
                )
                
                if attempt == max_retries:
                    circuit_breaker.call_failed(str(e))
                    break
                
                delay = self._calculate_delay(attempt, base_delay, strategy)
                time.sleep(delay)
        
        if fallback_func:
            return fallback_func(*args, **kwargs)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int, base_delay: float, strategy: RetryStrategy) -> float:
        """计算重试延迟"""
        if strategy == RetryStrategy.FIXED:
            return base_delay
        elif strategy == RetryStrategy.LINEAR:
            return base_delay * (attempt + 1)
        elif strategy == RetryStrategy.EXPONENTIAL:
            return base_delay * (2 ** attempt)
        elif strategy == RetryStrategy.EXPONENTIAL_JITTER:
            import random
            return base_delay * (2 ** attempt) + random.uniform(0, 1)
        else:
            return base_delay
    
    def get_circuit_breaker_status(self, name: str = None) -> Dict[str, Any]:
        """获取熔断器状态"""
        if name:
            if name in self.circuit_breakers:
                return self.circuit_breakers[name].get_status()
            return {}
        
        return {
            cb_name: cb.get_status()
            for cb_name, cb in self.circuit_breakers.items()
        }


# 全局增强重试处理器实例
enhanced_retry = EnhancedRetryHandler()


def retry_with_fallback(
    max_retries: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    circuit_breaker_name: str = None,
    fallback_func: Callable = None
):
    """简化版的重试装饰器"""
    return enhanced_retry.retry_with_circuit_breaker(
        max_retries=max_retries,
        base_delay=base_delay,
        strategy=strategy,
        circuit_breaker_name=circuit_breaker_name,
        fallback_func=fallback_func
    )