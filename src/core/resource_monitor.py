#!/usr/bin/env python3
"""
资源泄漏检测器 - 监控和修复资源泄漏
"""
import asyncio
import gc
import psutil
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from contextlib import contextmanager
import threading
import weakref
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """资源使用情况"""
    memory_mb: float
    cpu_percent: float
    file_descriptors: int
    threads: int
    connections: int
    timestamp: float


@dataclass
class LeakDetection:
    """泄漏检测结果"""
    resource_type: str
    current_value: float
    baseline_value: float
    growth_rate: float
    threshold_exceeded: bool
    potential_leak: bool
    details: Dict[str, Any]


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self.baseline_usage: Optional[ResourceUsage] = None
        self.usage_history: List[ResourceUsage] = []
        self.max_history_size = 100
        self._running = False
        self._monitor_task = None
        self._lock = threading.Lock()
        
        # 资源追踪
        self._tracked_objects: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._resource_allocations: Dict[str, int] = defaultdict(int)
        
        # 泄漏检测配置
        self.leak_thresholds = {
            "memory_growth_mb": 50.0,
            "memory_growth_rate": 0.1,
            "fd_growth": 10,
            "thread_growth": 5,
            "connection_growth": 20
        }
    
    async def start_monitoring(self):
        """开始监控"""
        if self._running:
            return
        
        self._running = True
        self.baseline_usage = await self._get_current_usage()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("资源监控已启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("资源监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._collect_usage()
                await self._detect_leaks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _collect_usage(self):
        """收集资源使用情况"""
        usage = await self._get_current_usage()
        
        with self._lock:
            self.usage_history.append(usage)
            if len(self.usage_history) > self.max_history_size:
                self.usage_history.pop(0)
    
    async def _get_current_usage(self) -> ResourceUsage:
        """获取当前资源使用情况"""
        process = psutil.Process()
        
        # 内存使用
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # CPU使用
        cpu_percent = process.cpu_percent()
        
        # 文件描述符
        try:
            file_descriptors = process.num_fds()
        except:
            file_descriptors = 0
        
        # 线程数
        threads = process.num_threads()
        
        # 网络连接
        connections = len(process.connections())
        
        return ResourceUsage(
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            file_descriptors=file_descriptors,
            threads=threads,
            connections=connections,
            timestamp=time.time()
        )
    
    async def _detect_leaks(self) -> List[LeakDetection]:
        """检测资源泄漏"""
        if not self.baseline_usage or len(self.usage_history) < 2:
            return []
        
        current = self.usage_history[-1]
        baseline = self.baseline_usage
        
        leaks = []
        
        # 检测内存泄漏
        memory_leak = self._check_memory_leak(current, baseline)
        if memory_leak:
            leaks.append(memory_leak)
        
        # 检测文件描述符泄漏
        fd_leak = self._check_fd_leak(current, baseline)
        if fd_leak:
            leaks.append(fd_leak)
        
        # 检测线程泄漏
        thread_leak = self._check_thread_leak(current, baseline)
        if thread_leak:
            leaks.append(thread_leak)
        
        # 检测连接泄漏
        connection_leak = self._check_connection_leak(current, baseline)
        if connection_leak:
            leaks.append(connection_leak)
        
        # 记录检测结果
        for leak in leaks:
            if leak.potential_leak:
                logger.warning(f"检测到潜在泄漏: {leak.resource_type}")
        
        return leaks
    
    def _check_memory_leak(self, current: ResourceUsage, baseline: ResourceUsage) -> Optional[LeakDetection]:
        """检查内存泄漏"""
        growth = current.memory_mb - baseline.memory_mb
        growth_rate = growth / max(baseline.memory_mb, 1)
        
        # 计算增长率趋势
        recent_growth = 0
        if len(self.usage_history) >= 5:
            recent = self.usage_history[-5:]
            recent_growth = (recent[-1].memory_mb - recent[0].memory_mb) / 5
        
        return LeakDetection(
            resource_type="memory",
            current_value=current.memory_mb,
            baseline_value=baseline.memory_mb,
            growth_rate=growth_rate,
            threshold_exceeded=growth > self.leak_thresholds["memory_growth_mb"],
            potential_leak=growth_rate > self.leak_thresholds["memory_growth_rate"],
            details={
                "growth_mb": growth,
                "recent_growth_mb": recent_growth,
                "gc_objects": len(gc.get_objects()),
                "gc_garbage": len(gc.garbage)
            }
        )
    
    def _check_fd_leak(self, current: ResourceUsage, baseline: ResourceUsage) -> Optional[LeakDetection]:
        """检查文件描述符泄漏"""
        growth = current.file_descriptors - baseline.file_descriptors
        
        return LeakDetection(
            resource_type="file_descriptors",
            current_value=current.file_descriptors,
            baseline_value=baseline.file_descriptors,
            growth_rate=growth / max(baseline.file_descriptors, 1),
            threshold_exceeded=abs(growth) > self.leak_thresholds["fd_growth"],
            potential_leak=growth > 0,
            details={
                "growth_count": growth,
                "open_files": self._get_open_files()
            }
        )
    
    def _check_thread_leak(self, current: ResourceUsage, baseline: ResourceUsage) -> Optional[LeakDetection]:
        """检查线程泄漏"""
        growth = current.threads - baseline.threads
        
        return LeakDetection(
            resource_type="threads",
            current_value=current.threads,
            baseline_value=baseline.threads,
            growth_rate=growth / max(baseline.threads, 1),
            threshold_exceeded=abs(growth) > self.leak_thresholds["thread_growth"],
            potential_leak=growth > 0,
            details={
                "growth_count": growth,
                "active_threads": threading.active_count(),
                "thread_names": [t.name for t in threading.enumerate()]
            }
        )
    
    def _check_connection_leak(self, current: ResourceUsage, baseline: ResourceUsage) -> Optional[LeakDetection]:
        """检查连接泄漏"""
        growth = current.connections - baseline.connections
        
        return LeakDetection(
            resource_type="connections",
            current_value=current.connections,
            baseline_value=baseline.connections,
            growth_rate=growth / max(baseline.connections, 1),
            threshold_exceeded=abs(growth) > self.leak_thresholds["connection_growth"],
            potential_leak=growth > 0,
            details={
                "growth_count": growth,
                "connections": self._get_connection_details()
            }
        )
    
    def _get_open_files(self) -> List[str]:
        """获取打开的文件列表"""
        try:
            process = psutil.Process()
            return [f.path for f in process.open_files()]
        except:
            return []
    
    def _get_connection_details(self) -> List[Dict[str, Any]]:
        """获取连接详情"""
        try:
            process = psutil.Process()
            connections = []
            for conn in process.connections():
                connections.append({
                    "fd": conn.fd,
                    "family": conn.family.name,
                    "type": conn.type.name,
                    "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if hasattr(conn, 'laddr') and conn.laddr else None,
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if hasattr(conn, 'raddr') and conn.raddr else None,
                    "status": conn.status
                })
            return connections
        except:
            return []
    
    def track_object(self, obj: Any, category: str = "generic"):
        """追踪对象"""
        weak_ref = weakref.ref(obj)
        with self._lock:
            self._tracked_objects[category].append(weak_ref)
            self._resource_allocations[category] += 1
    
    def get_tracked_objects(self, category: str = None) -> Dict[str, int]:
        """获取追踪的对象"""
        result = {}
        
        with self._lock:
            categories = [category] if category else list(self._tracked_objects.keys())
            
            for cat in categories:
                refs = self._tracked_objects[cat]
                alive_count = sum(1 for ref in refs if ref() is not None)
                total_count = len(refs)
                
                result[cat] = {
                    "alive": alive_count,
                    "total": total_count,
                    "garbage": total_count - alive_count,
                    "allocations": self._resource_allocations[cat]
                }
        
        return result
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """强制垃圾回收"""
        before = len(gc.get_objects())
        gc.collect()
        after = len(gc.get_objects())
        
        logger.info(f"垃圾回收完成: {before} -> {after} 对象")
        
        return {
            "before": before,
            "after": after,
            "collected": before - after
        }
    
    def get_usage_report(self) -> Dict[str, Any]:
        """获取使用报告"""
        current = self.usage_history[-1] if self.usage_history else None
        
        return {
            "current_usage": {
                "memory_mb": current.memory_mb if current else 0,
                "cpu_percent": current.cpu_percent if current else 0,
                "file_descriptors": current.file_descriptors if current else 0,
                "threads": current.threads if current else 0,
                "connections": current.connections if current else 0
            },
            "tracked_objects": self.get_tracked_objects(),
            "gc_stats": {
                "objects": len(gc.get_objects()),
                "garbage": len(gc.garbage),
                "thresholds": gc.get_threshold()
            },
            "uptime": time.time() - (self.baseline_usage.timestamp if self.baseline_usage else time.time())
        }


class ResourceLeakFixer:
    """资源泄漏修复器"""
    
    def __init__(self, monitor: ResourceMonitor):
        self.monitor = monitor
        self.fix_strategies = {
            "memory": self._fix_memory_leak,
            "file_descriptors": self._fix_fd_leak,
            "threads": self._fix_thread_leak,
            "connections": self._fix_connection_leak
        }
    
    async def fix_leaks(self, leaks: List[LeakDetection]) -> Dict[str, bool]:
        """修复检测到的泄漏"""
        results = {}
        
        for leak in leaks:
            if leak.potential_leak:
                strategy = self.fix_strategies.get(leak.resource_type)
                if strategy:
                    try:
                        success = await strategy(leak)
                        results[leak.resource_type] = success
                        logger.info(f"修复 {leak.resource_type} 泄漏: {'成功' if success else '失败'}")
                    except Exception as e:
                        logger.error(f"修复 {leak.resource_type} 泄漏时出错: {e}")
                        results[leak.resource_type] = False
        
        return results
    
    async def _fix_memory_leak(self, leak: LeakDetection) -> bool:
        """修复内存泄漏"""
        try:
            # 强制垃圾回收
            gc_result = self.monitor.force_garbage_collection()
            
            # 清理未引用的对象
            gc.collect(2)  # 最彻底的垃圾回收
            
            return gc_result["collected"] > 0
        except Exception as e:
            logger.error(f"修复内存泄漏失败: {e}")
            return False
    
    async def _fix_fd_leak(self, leak: LeakDetection) -> bool:
        """修复文件描述符泄漏"""
        try:
            # 这里可以添加具体的FD清理逻辑
            # 例如关闭未使用的文件句柄
            logger.warning("文件描述符泄漏需要手动处理")
            return False
        except Exception as e:
            logger.error(f"修复文件描述符泄漏失败: {e}")
            return False
    
    async def _fix_thread_leak(self, leak: LeakDetection) -> bool:
        """修复线程泄漏"""
        try:
            # 检查并清理僵尸线程
            import threading
            
            active_threads = threading.enumerate()
            daemon_threads = [t for t in active_threads if t.daemon]
            
            logger.info(f"发现 {len(daemon_threads)} 个守护线程")
            
            # 这里可以添加线程清理逻辑
            return len(daemon_threads) > 0
        except Exception as e:
            logger.error(f"修复线程泄漏失败: {e}")
            return False
    
    async def _fix_connection_leak(self, leak: LeakDetection) -> bool:
        """修复连接泄漏"""
        try:
            # 这里可以添加连接清理逻辑
            # 例如关闭空闲连接
            logger.warning("连接泄漏需要手动处理")
            return False
        except Exception as e:
            logger.error(f"修复连接泄漏失败: {e}")
            return False


# 全局实例
resource_monitor = ResourceMonitor()
resource_fixer = ResourceLeakFixer(resource_monitor)