#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Service - 日志管理业务逻辑层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
from src.dao.log_dao import LogDAO
from src.models.log import ApiRequestLog
from src.utils.logging import logger


class LogService:
    """日志管理服务 - 支持缓存和批量处理"""
    
    def __init__(self, log_dao: Optional[LogDAO] = None):
        self.dao = log_dao or LogDAO()
        self._stats_cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def create_request_log(
        self,
        source_api: str,
        target_api: str,
        source_model: str = None,
        target_model: str = None,
        request_headers: str = None,
        request_body: str = None,
        response_body: str = None,
        status_code: int = None,
        error_message: str = None,
        processing_time: float = None,
        request_method: str = None,
        client_ip: str = None,
        user_agent: str = None,
        provider: str = None,
        **kwargs  # 接受额外的参数但忽略它们
    ) -> ApiRequestLog:
        """创建请求日志（创建后清除相关缓存）"""
        try:
            result = self.dao.create_request_log(
                source_api=source_api,
                target_api=target_api,
                source_model=source_model,
                target_model=target_model,
                request_headers=request_headers,
                request_body=request_body,
                response_body=response_body,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time
            )
            
            # 清除相关缓存以保持数据一致性
            self._invalidate_cache()
            
            return result
        except Exception as e:
            logger.error(f"创建请求日志失败: {e}")
            raise
    
    def get_logs_paginated(
        self,
        page: int = 1,
        size: int = 20,
        start_time: str = None,
        end_time: str = None,
        source_api: str = None,
        target_api: str = None,
        source_model: str = None,
        target_model: str = None,
        status_code: int = None
    ) -> Dict[str, Any]:
        """分页获取日志"""
        try:
            # 验证分页参数
            if page < 1:
                page = 1
            if size < 1 or size > 100:
                size = 20
            
            offset = (page - 1) * size
            
            # 构建过滤条件
            filters = {}
            if start_time:
                filters['start_time'] = start_time
            if end_time:
                filters['end_time'] = end_time
            if source_api:
                filters['source_api'] = source_api
            if target_api:
                filters['target_api'] = target_api
            if source_model:
                filters['source_model'] = source_model
            if target_model:
                filters['target_model'] = target_model
            if status_code:
                filters['status_code'] = status_code
            
            result = self.dao.get_logs_paginated(page, size, **filters)
            logs = result["items"]
            total = result["total"]
            
            return {
                "items": logs,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        except Exception as e:
            logger.error(f"分页获取日志失败: {e}")
            raise
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        params = '_'.join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        return f"{prefix}_{params}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._stats_cache:
            return False
        
        timestamp, _ = self._stats_cache[cache_key]
        return datetime.now() - timestamp < self._cache_ttl
    
    def _get_cached_stats(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取统计信息"""
        if self._is_cache_valid(cache_key):
            return self._stats_cache[cache_key][1]
        return None
    
    def _set_cached_stats(self, cache_key: str, data: List[Dict[str, Any]]):
        """设置缓存统计信息"""
        self._stats_cache[cache_key] = (datetime.now(), data)
    
    def _invalidate_cache(self):
        """清除所有缓存"""
        self._stats_cache.clear()
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取每日统计（带缓存）"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            cache_key = self._get_cache_key("daily_stats", days=days)
            cached = self._get_cached_stats(cache_key)
            if cached is not None:
                return cached
            
            result = self.dao.get_daily_stats(days)
            self._set_cached_stats(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取每日统计失败: {e}")
            raise
    
    def get_model_usage_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取模型使用统计（带缓存）"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            cache_key = self._get_cache_key("model_usage_stats", days=days)
            cached = self._get_cached_stats(cache_key)
            if cached is not None:
                return cached
            
            result = self.dao.get_model_usage_stats(days)
            self._set_cached_stats(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取模型使用统计失败: {e}")
            raise
    
    def get_error_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取错误统计（带缓存和优化）"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            cache_key = self._get_cache_key("error_stats", days=days)
            cached = self._get_cached_stats(cache_key)
            if cached is not None:
                return cached
            
            # 使用DAO的聚合查询优化性能
            result = self.dao.get_error_stats(days)
            self._set_cached_stats(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            raise
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """清理旧日志"""
        try:
            if days < 1:
                raise ValueError("保留天数必须大于0")
            
            return self.dao.cleanup_old_logs(days)
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            raise
    
    def get_api_performance_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取API性能统计（带缓存）"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            cache_key = self._get_cache_key("api_performance_stats", days=days)
            cached = self._get_cached_stats(cache_key)
            if cached is not None:
                return cached
            
            # 获取最近N天的日志
            filters = {
                'start_time': (datetime.now() - timedelta(days=days)).isoformat()
            }
            
            result = self.dao.get_logs_paginated(1, 10000, **filters)
            logs = result["items"]
            
            # 按API分组统计
            api_stats = {}
            for log in logs:
                api_key = f"{log.get('source_api', 'unknown')} -> {log.get('target_api', 'unknown')}"
                if api_key not in api_stats:
                    api_stats[api_key] = {
                        'api': api_key,
                        'total_requests': 0,
                        'success_requests': 0,
                        'error_requests': 0,
                        'avg_processing_time': 0,
                        'total_processing_time': 0,
                        'success_rate': 0
                    }
                
                stat = api_stats[api_key]
                stat['total_requests'] += 1
                
                status_code = log.get('status_code')
                if status_code and 200 <= status_code < 300:
                    stat['success_requests'] += 1
                else:
                    stat['error_requests'] += 1
                
                processing_time = log.get('processing_time')
                if processing_time:
                    stat['total_processing_time'] += processing_time
            
            # 计算平均值和成功率
            for stat in api_stats.values():
                if stat['total_requests'] > 0:
                    stat['success_rate'] = round((stat['success_requests'] / stat['total_requests']) * 100, 2)
                    if stat['success_requests'] > 0:
                        stat['avg_processing_time'] = round(stat['total_processing_time'] / stat['success_requests'], 3)
                
                # 移除临时字段
                del stat['total_processing_time']
            
            result_list = list(api_stats.values())
            self._set_cached_stats(cache_key, result_list)
            return result_list
        except Exception as e:
            logger.error(f"获取API性能统计失败: {e}")
            raise