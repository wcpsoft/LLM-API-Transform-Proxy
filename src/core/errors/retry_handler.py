#!/usr/bin/env python3
"""
重试处理器 - 实现指数退避和熔断器模式
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略枚举"""
    EXPONENTIAL_BACKOFF = "exponential"
    LINEAR_BACKOFF = "linear"
    FIXED_DELAY = "fixed"


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


class RetryConfig:
    """重试配置类"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        exponential_base: float = 2.0,
        jitter: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 60.0,
        retry_exceptions: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.retry_exceptions = retry_exceptions


class CircuitBreaker:
    """增强的熔断器实现"""
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        timeout: float = 60.0,
        success_threshold: int = 2,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.failure_reasons = []
    
    def call_succeeded(self):
        """调用成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.failure_count = 0
                self.success_count = 0
                self.failure_reasons.clear()
                self.state = CircuitState.CLOSED
                logger.info(f"熔断器 {self.name} 关闭")
        else:
            self.failure_count = 0
            self.success_count = 0
    
    def call_failed(self, reason: str = None):
        """调用失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if reason:
            self.failure_reasons.append(reason)
            if len(self.failure_reasons) > 10:
                self.failure_reasons.pop(0)
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"熔断器 {self.name} 打开，失败次数: {self.failure_count}, "
                f"最近失败原因: {self.failure_reasons[-3:]}"
            )
    
    def can_execute(self) -> bool:
        """检查是否可以执行调用"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"熔断器 {self.name} 进入半开状态")
                return True
            return False
        
        # HALF_OPEN状态允许有限次数的尝试
        return self.success_count < self.success_threshold
    
    def record_success(self):
        """记录半开状态的成功调用"""
        if self.state == CircuitState.HALF_OPEN:
            self.call_succeeded()
    
    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout": self.timeout,
            "last_failure_time": self.last_failure_time,
            "failure_reasons": self.failure_reasons[-5:]
        }


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.circuit_breakers = {}
    
    def _get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
        return self.circuit_breakers[key]
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        else:  # EXPONENTIAL_BACKOFF
            delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        circuit_key: Optional[str] = None,
        **kwargs
    ) -> Any:
        """执行带重试的异步函数"""
        
        circuit_breaker = None
        if circuit_key:
            circuit_breaker = self._get_circuit_breaker(circuit_key)
            if not circuit_breaker.can_execute():
                raise Exception(f"熔断器打开，服务不可用: {circuit_key}")
        
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                if attempt > 0:
                    logger.info(f"重试成功，尝试次数: {attempt + 1}")
                
                return result
                
            except self.config.retry_exceptions as e:
                last_exception = e
                
                if circuit_breaker:
                    circuit_breaker.call_failed()
                
                if attempt == self.config.max_retries:
                    logger.error(f"达到最大重试次数: {self.config.max_retries}")
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"操作失败，{delay:.2f}秒后重试 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                
                await asyncio.sleep(delay)
        
        raise last_exception


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
    retry_exceptions: tuple = (Exception,),
    circuit_key: Optional[str] = None
):
    """重试装饰器"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                strategy=strategy,
                retry_exceptions=retry_exceptions
            )
            handler = RetryHandler(config)
            return await handler.execute_with_retry(func, *args, circuit_key=circuit_key, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                strategy=strategy,
                retry_exceptions=retry_exceptions
            )
            handler = RetryHandler(config)
            
            # 同步版本需要特殊处理
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper(*args, **kwargs)
            else:
                # 对于同步函数，使用线程池执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(func, *args, **kwargs)
                    return future.result()
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator