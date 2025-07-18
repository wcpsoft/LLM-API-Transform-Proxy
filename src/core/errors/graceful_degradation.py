#!/usr/bin/env python3
"""
优雅降级机制 - 实现服务熔断和降级处理
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from .retry_handler import CircuitBreaker, CircuitState
from .error_logger import ErrorContext, error_logger
from src.core.health.health_checker import health_checker

logger = logging.getLogger(__name__)


class ServiceHealth(Enum):
    """服务健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"


@dataclass
class ServiceStatus:
    """服务状态信息"""
    service_name: str
    health: ServiceHealth
    response_time: float
    error_rate: float
    last_check: float
    circuit_state: CircuitState
    message: Optional[str] = None


class ServiceHealthMonitor:
    """服务健康监控器"""
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.services: Dict[str, Dict[str, Any]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._running = False
        self._monitor_task = None
    
    def register_service(
        self,
        service_name: str,
        health_check_func: Callable,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """注册服务"""
        
        self.services[service_name] = {
            "health_check": health_check_func,
            "last_status": ServiceStatus(
                service_name=service_name,
                health=ServiceHealth.HEALTHY,
                response_time=0.0,
                error_rate=0.0,
                last_check=time.time(),
                circuit_state=CircuitState.CLOSED
            )
        }
        
        if circuit_breaker:
            self.circuit_breakers[service_name] = circuit_breaker
    
    async def start_monitoring(self):
        """开始监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("服务健康监控已启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("服务健康监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"健康监控循环出错: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """检查所有服务"""
        tasks = []
        for service_name in self.services:
            tasks.append(self._check_service(service_name))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service(self, service_name: str):
        """检查单个服务"""
        try:
            service_info = self.services[service_name]
            health_check = service_info["health_check"]
            
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(health_check):
                is_healthy = await health_check()
            else:
                is_healthy = health_check()
            
            response_time = time.time() - start_time
            
            # 获取熔断器状态
            circuit_breaker = self.circuit_breakers.get(service_name)
            circuit_state = circuit_breaker.state if circuit_breaker else CircuitState.CLOSED
            
            # 计算错误率（这里简化处理，实际应该基于历史数据）
            error_rate = 0.0 if is_healthy else 1.0
            
            # 确定健康状态
            if not is_healthy:
                health = ServiceHealth.UNHEALTHY
            elif response_time > 5.0:  # 响应时间超过5秒
                health = ServiceHealth.DEGRADED
            elif circuit_state == CircuitState.OPEN:
                health = ServiceHealth.UNAVAILABLE
            else:
                health = ServiceHealth.HEALTHY
            
            status = ServiceStatus(
                service_name=service_name,
                health=health,
                response_time=response_time,
                error_rate=error_rate,
                last_check=time.time(),
                circuit_state=circuit_state,
                message=f"服务检查完成，响应时间: {response_time:.2f}s"
            )
            
            service_info["last_status"] = status
            
            if health != ServiceHealth.HEALTHY:
                logger.warning(f"服务 {service_name} 状态异常: {health.value}")
            
        except Exception as e:
            logger.error(f"检查服务 {service_name} 时出错: {e}")
            
            status = ServiceStatus(
                service_name=service_name,
                health=ServiceHealth.UNHEALTHY,
                response_time=0.0,
                error_rate=1.0,
                last_check=time.time(),
                circuit_state=CircuitState.OPEN,
                message=str(e)
            )
            
            self.services[service_name]["last_status"] = status
    
    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """获取服务状态"""
        if service_name in self.services:
            return self.services[service_name]["last_status"]
        return None
    
    def get_all_statuses(self) -> Dict[str, ServiceStatus]:
        """获取所有服务状态"""
        return {
            name: info["last_status"]
            for name, info in self.services.items()
        }


class FallbackHandler:
    """降级处理器"""
    
    def __init__(self):
        self.fallbacks: Dict[str, Dict[str, Any]] = {}
        self.health_monitor = ServiceHealthMonitor()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 默认缓存5分钟
    
    def register_fallback(
        self,
        service_name: str,
        fallback_func: Callable,
        priority: int = 1,
        conditions: Optional[List[str]] = None
    ):
        """注册降级处理函数"""
        
        if service_name not in self.fallbacks:
            self.fallbacks[service_name] = []
        
        self.fallbacks[service_name].append({
            "function": fallback_func,
            "priority": priority,
            "conditions": conditions or ["unhealthy", "unavailable"]
        })
        
        # 按优先级排序
        self.fallbacks[service_name].sort(key=lambda x: x["priority"])
    
    def _get_cache_key(self, service_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            "service": service_name,
            "args": str(args),
            "kwargs": str(sorted(kwargs.items()))
        }
        return json.dumps(key_data, sort_keys=True)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.utcnow() < entry["expires"]:
                return entry["value"]
            else:
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, value: Any, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.cache_ttl
        self.cache[cache_key] = {
            "value": value,
            "expires": datetime.utcnow() + timedelta(seconds=ttl)
        }
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        context: Optional[ErrorContext] = None,
        use_cache: bool = True,
        cache_ttl: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行带降级的操作"""
        
        cache_key = self._get_cache_key(service_name, *args, **kwargs)
        
        # 检查缓存
        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return {
                    "data": cached_result,
                    "source": "cache",
                    "degraded": False,
                    "cached": True
                }
        
        # 检查服务健康状态
        health_status = health_checker.get_service_status(service_name)
        should_degrade = (
            health_status and 
            health_status.get("status") in ["unhealthy", "unavailable"]
        )
        
        try:
            if not should_degrade:
                # 服务健康，执行主函数
                result = await self._execute_primary(service_name, primary_func, *args, **kwargs)
                
                # 缓存结果
                if use_cache:
                    self._set_cache(cache_key, result, cache_ttl)
                
                return {
                    "data": result,
                    "source": "primary",
                    "degraded": False,
                    "cached": False
                }
            else:
                logger.warning(f"服务 {service_name} 不健康，使用降级处理")
                
        except Exception as e:
            # 主函数失败，记录错误并尝试降级
            logger.error(f"主函数执行失败: {e}")
            error_logger.log_error(
                e,
                context={
                    "service": service_name,
                    "operation": "primary",
                    "cache_key": cache_key,
                    **(context.context if context else {})
                }
            )
        
        # 执行降级处理
        fallback_result = await self._execute_fallback(
            service_name, *args, context=context, **kwargs
        )
        
        # 缓存降级结果（较短的TTL）
        if use_cache:
            self._set_cache(cache_key, fallback_result, cache_ttl or 60)  # 降级结果缓存1分钟
        
        return {
            "data": fallback_result,
            "source": "fallback",
            "degraded": True,
            "cached": False
        }
    
    async def _execute_primary(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行主函数"""
        
        try:
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(*args, **kwargs)
            else:
                return primary_func(*args, **kwargs)
        
        except Exception as e:
            logger.error(f"主函数执行失败: {e}")
            raise
    
    async def _execute_fallback(
        self,
        service_name: str,
        *args,
        context: Optional[ErrorContext] = None,
        **kwargs
    ) -> Any:
        """执行降级处理"""
        
        if service_name not in self.fallbacks:
            raise Exception(f"没有为服务 {service_name} 注册降级处理")
        
        for fallback in self.fallbacks[service_name]:
            try:
                fallback_func = fallback["function"]
                
                logger.info(f"执行降级处理: {service_name}")
                
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"降级处理失败: {e}")
                continue
        
        # 所有降级处理都失败
        raise Exception(f"所有降级处理都失败: {service_name}")
    
    def add_timeout_handler(
        self,
        timeout_seconds: float = 30.0,
        timeout_message: str = "操作超时"
    ):
        """添加超时处理器"""
        
        def timeout_fallback(*args, **kwargs):
            raise TimeoutError(timeout_message)
        
        return timeout_fallback


# 全局实例
health_monitor = ServiceHealthMonitor()
fallback_handler = FallbackHandler()


# 装饰器
class graceful_degradation:
    """优雅降级装饰器"""
    
    def __init__(
        self,
        service_name: str,
        fallback_func: Optional[Callable] = None,
        timeout: float = 30.0
    ):
        self.service_name = service_name
        self.fallback_func = fallback_func
        self.timeout = timeout
    
    def __call__(self, func: Callable) -> Callable:
        
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    fallback_handler.execute_with_fallback(
                        self.service_name,
                        func,
                        *args,
                        **kwargs
                    ),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                if self.fallback_func:
                    return await self.fallback_func(*args, **kwargs)
                raise
        
        return async_wrapper