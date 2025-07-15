import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.request_times = deque(maxlen=max_records)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'errors': 0
        })
        self.status_code_stats = defaultdict(int)
        self.start_time = datetime.now()
    
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int):
        """记录请求性能数据"""
        key = f"{method} {endpoint}"
        
        # 记录请求时间
        self.request_times.append({
            'timestamp': datetime.now(),
            'duration': duration,
            'endpoint': key,
            'status_code': status_code
        })
        
        # 更新端点统计
        stats = self.endpoint_stats[key]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
        
        if status_code >= 400:
            stats['errors'] += 1
        
        # 更新状态码统计
        self.status_code_stats[status_code] += 1
    
    def get_stats(self, minutes: int = 60) -> Dict:
        """获取性能统计数据"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_requests = [
            req for req in self.request_times 
            if req['timestamp'] > cutoff_time
        ]
        
        if not recent_requests:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'requests_per_minute': 0,
                'error_rate': 0,
                'endpoint_stats': {},
                'status_codes': {},
                'system_info': self._get_system_info()
            }
        
        # 计算基本统计
        total_requests = len(recent_requests)
        avg_response_time = sum(req['duration'] for req in recent_requests) / total_requests
        requests_per_minute = total_requests / minutes
        
        # 计算错误率
        error_requests = sum(1 for req in recent_requests if req['status_code'] >= 400)
        error_rate = (error_requests / total_requests) * 100 if total_requests > 0 else 0
        
        # 端点统计（仅最近时间段）
        endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'errors': 0
        })
        
        for req in recent_requests:
            endpoint = req['endpoint']
            stats = endpoint_stats[endpoint]
            stats['count'] += 1
            stats['total_time'] += req['duration']
            if req['status_code'] >= 400:
                stats['errors'] += 1
        
        # 计算平均时间
        for endpoint, stats in endpoint_stats.items():
            if stats['count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['count']
        
        # 状态码统计（仅最近时间段）
        status_codes = defaultdict(int)
        for req in recent_requests:
            status_codes[req['status_code']] += 1
        
        return {
            'total_requests': total_requests,
            'avg_response_time': round(avg_response_time, 3),
            'requests_per_minute': round(requests_per_minute, 2),
            'error_rate': round(error_rate, 2),
            'endpoint_stats': dict(endpoint_stats),
            'status_codes': dict(status_codes),
            'system_info': self._get_system_info(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
        }
    
    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            logger.warning(f"获取系统信息失败: {e}")
            return {}


class MonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app, monitor: PerformanceMonitor):
        super().__init__(app)
        self.monitor = monitor
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 执行请求
        response = await call_next(request)
        
        # 计算处理时间
        duration = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 记录性能数据
        self.monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            duration=duration,
            status_code=response.status_code
        )
        
        # 添加性能头
        response.headers["X-Response-Time"] = f"{duration:.2f}ms"
        
        return response


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = None
        self.last_results = {}
    
    def register_check(self, name: str, check_func, timeout: int = 5):
        """注册健康检查项"""
        self.checks[name] = {
            'func': check_func,
            'timeout': timeout
        }
    
    async def run_checks(self, force: bool = False) -> Dict:
        """运行所有健康检查"""
        now = datetime.now()
        
        # 如果不是强制检查且距离上次检查不到30秒，返回缓存结果
        if (not force and self.last_check_time and 
            (now - self.last_check_time).total_seconds() < 30):
            return self.last_results
        
        results = {
            'status': 'healthy',
            'timestamp': now.isoformat(),
            'checks': {},
            'overall': True
        }
        
        for name, check_config in self.checks.items():
            try:
                # 运行检查（这里简化处理，实际应该支持异步超时）
                check_result = await self._run_single_check(
                    check_config['func'], 
                    check_config['timeout']
                )
                
                results['checks'][name] = {
                    'status': 'healthy' if check_result else 'unhealthy',
                    'healthy': check_result,
                    'message': 'OK' if check_result else 'Check failed'
                }
                
                if not check_result:
                    results['overall'] = False
                    
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'healthy': False,
                    'message': str(e)
                }
                results['overall'] = False
        
        # 设置整体状态
        if not results['overall']:
            results['status'] = 'unhealthy'
        
        self.last_check_time = now
        self.last_results = results
        
        return results
    
    async def _run_single_check(self, check_func, timeout: int) -> bool:
        """运行单个健康检查"""
        try:
            if callable(check_func):
                result = check_func()
                # 如果是协程，等待结果
                if hasattr(result, '__await__'):
                    result = await result
                return bool(result)
            return False
        except Exception as e:
            logger.error(f"健康检查执行失败: {e}")
            return False


# 全局实例
performance_monitor = PerformanceMonitor()
health_checker = HealthChecker()


def setup_monitoring(app):
    """设置监控功能"""
    # 添加性能监控中间件
    app.add_middleware(MonitoringMiddleware, monitor=performance_monitor)
    
    # 注册基本健康检查
    def check_database():
        """检查数据库连接"""
        try:
            from src.utils.db import get_db
            with next(get_db()) as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
    
    def check_memory():
        """检查内存使用率"""
        try:
            memory_percent = psutil.virtual_memory().percent
            return memory_percent < 90  # 内存使用率低于90%
        except Exception:
            return False
    
    def check_disk():
        """检查磁盘使用率"""
        try:
            disk_percent = psutil.disk_usage('/').percent
            return disk_percent < 95  # 磁盘使用率低于95%
        except Exception:
            return False
    
    health_checker.register_check('database', check_database)
    health_checker.register_check('memory', check_memory)
    health_checker.register_check('disk', check_disk)
    
    # 添加监控端点
    @app.get("/metrics")
    async def get_metrics(minutes: int = 60):
        """获取性能指标"""
        return performance_monitor.get_stats(minutes)
    
    @app.get("/health/detailed")
    async def detailed_health_check(force: bool = False):
        """详细健康检查"""
        return await health_checker.run_checks(force)