"""
健康检查系统 - 提供服务健康状态监控和报告
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import logging

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """健康状态信息"""
    service: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    message: str
    timestamp: datetime
    response_time: float
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "response_time": self.response_time,
            "details": self.details or {}
        }


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, HealthStatus] = {}
        self.circuit_breakers: Dict[str, int] = {}
        self.failure_threshold = 3
        self.recovery_time = 60  # 秒
    
    def register_check(self, name: str, check_func: Callable):
        """注册健康检查"""
        self.checks[name] = check_func
    
    def register_service(self, name: str, check_func: Callable):
        """注册服务健康检查（兼容接口）"""
        self.register_check(name, check_func)
    
    async def check_database(self) -> HealthStatus:
        """检查数据库健康状态"""
        start_time = time.time()
        try:
            from src.utils.db import get_db
            db = get_db()
            # 简单的查询测试
            db.execute("SELECT 1")
            response_time = time.time() - start_time
            return HealthStatus(
                service="database",
                status="healthy",
                message="Database connection is healthy",
                timestamp=datetime.utcnow(),
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service="database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"error": str(e)}
            )
    
    async def check_provider_health(self, provider_name: str) -> HealthStatus:
        """检查提供商健康状态"""
        start_time = time.time()
        try:
            from src.providers.factory import ProviderFactory
            provider = ProviderFactory.create_provider(provider_name)
            
            # 使用轻量级健康检查
            if hasattr(provider, 'health_check'):
                is_healthy = await provider.health_check()
            else:
                # 默认健康检查 - 尝试获取模型列表
                models = await provider.get_models()
                is_healthy = len(models) > 0
            
            response_time = time.time() - start_time
            
            if is_healthy:
                return HealthStatus(
                    service=f"provider_{provider_name}",
                    status="healthy",
                    message=f"Provider {provider_name} is healthy",
                    timestamp=datetime.utcnow(),
                    response_time=response_time
                )
            else:
                return HealthStatus(
                    service=f"provider_{provider_name}",
                    status="degraded",
                    message=f"Provider {provider_name} is degraded",
                    timestamp=datetime.utcnow(),
                    response_time=response_time
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service=f"provider_{provider_name}",
                status="unhealthy",
                message=f"Provider {provider_name} is unavailable: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={"error": str(e)}
            )
    
    async def check_redis(self) -> HealthStatus:
        """检查Redis健康状态"""
        start_time = time.time()
        try:
            # 这里需要根据实际的Redis客户端实现
            # 暂时返回未知状态
            response_time = time.time() - start_time
            return HealthStatus(
                service="redis",
                status="unknown",
                message="Redis health check not implemented",
                timestamp=datetime.utcnow(),
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service="redis",
                status="unhealthy",
                message=f"Redis connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time
            )
    
    async def check_disk_space(self) -> HealthStatus:
        """检查磁盘空间"""
        start_time = time.time()
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            
            response_time = time.time() - start_time
            
            if free_percent > 20:
                status = "healthy"
                message = f"Disk space OK: {free_percent:.1f}% free"
            elif free_percent > 10:
                status = "degraded"
                message = f"Disk space low: {free_percent:.1f}% free"
            else:
                status = "unhealthy"
                message = f"Disk space critical: {free_percent:.1f}% free"
            
            return HealthStatus(
                service="disk_space",
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                details={
                    "total_gb": total / (1024**3),
                    "used_gb": used / (1024**3),
                    "free_gb": free / (1024**3),
                    "free_percent": free_percent
                }
            )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service="disk_space",
                status="unknown",
                message=f"Disk space check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time
            )
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        results = {}
        
        # 注册默认检查
        if not self.checks:
            self.register_check("database", self.check_database)
            self.register_check("disk_space", self.check_disk_space)
            # 可以添加更多提供商检查
        
        # 运行所有注册的检查
        tasks = []
        for name, check_func in self.checks.items():
            if asyncio.iscoroutinefunction(check_func):
                tasks.append((name, check_func()))
            else:
                tasks.append((name, asyncio.create_task(asyncio.to_thread(check_func))))
        
        # 并行执行所有检查
        for name, task in tasks:
            try:
                if asyncio.iscoroutine(task):
                    result = await task
                else:
                    result = await task
                results[name] = result.to_dict()
                self.last_check_results[name] = result
            except Exception as e:
                results[name] = HealthStatus(
                    service=name,
                    status="unknown",
                    message=f"Health check failed: {str(e)}",
                    timestamp=datetime.utcnow(),
                    response_time=0.0
                ).to_dict()
        
        # 计算整体状态
        overall_status = self._calculate_overall_status(results)
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }
    
    def _calculate_overall_status(self, results: Dict[str, Any]) -> str:
        """计算整体健康状态"""
        statuses = [result["status"] for result in results.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        elif all(status == "healthy" for status in statuses):
            return "healthy"
        else:
            return "unknown"
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取特定服务的状态"""
        if service_name in self.last_check_results:
            return self.last_check_results[service_name].to_dict()
        return None


# 全局健康检查器实例
health_checker = HealthChecker()