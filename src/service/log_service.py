#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Service - 日志管理业务逻辑层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.dao.log_dao import LogDAO
from src.models.log import ApiRequestLog
from src.utils.logging import logger


class LogService:
    """日志管理服务"""
    
    def __init__(self):
        self.dao = LogDAO()
    
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
        processing_time: float = None
    ) -> ApiRequestLog:
        """创建请求日志"""
        try:
            return self.dao.create_request_log(
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
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取每日统计"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            return self.dao.get_daily_stats(days)
        except Exception as e:
            logger.error(f"获取每日统计失败: {e}")
            raise
    
    def get_model_usage_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取模型使用统计"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            return self.dao.get_model_usage_stats(days)
        except Exception as e:
            logger.error(f"获取模型使用统计失败: {e}")
            raise
    
    def get_error_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取错误统计"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            # 获取错误状态码统计
            filters = {
                'start_time': (datetime.now() - timedelta(days=days)).isoformat(),
                'error_only': True
            }
            
            result = self.dao.get_logs_paginated(1, 1000, **filters)
            logs = result["items"]
            
            # 统计错误类型
            error_stats = {}
            for log in logs:
                status_code = log.status_code or 'unknown'
                if status_code not in error_stats:
                    error_stats[status_code] = {
                        'status_code': status_code,
                        'count': 0,
                        'percentage': 0
                    }
                error_stats[status_code]['count'] += 1
            
            # 计算百分比
            total_errors = sum(stat['count'] for stat in error_stats.values())
            if total_errors > 0:
                for stat in error_stats.values():
                    stat['percentage'] = round((stat['count'] / total_errors) * 100, 2)
            
            return list(error_stats.values())
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
        """获取API性能统计"""
        try:
            if days < 1 or days > 365:
                days = 7
            
            # 获取最近N天的日志
            filters = {
                'start_time': (datetime.now() - timedelta(days=days)).isoformat()
            }
            
            result = self.dao.get_logs_paginated(1, 10000, **filters)
            logs = result["items"]
            
            # 按API分组统计
            api_stats = {}
            for log in logs:
                api_key = f"{log.source_api} -> {log.target_api}"
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
                
                if log.status_code and 200 <= log.status_code < 300:
                    stat['success_requests'] += 1
                else:
                    stat['error_requests'] += 1
                
                if log.processing_time:
                    stat['total_processing_time'] += log.processing_time
            
            # 计算平均值和成功率
            for stat in api_stats.values():
                if stat['total_requests'] > 0:
                    stat['success_rate'] = round((stat['success_requests'] / stat['total_requests']) * 100, 2)
                    if stat['success_requests'] > 0:
                        stat['avg_processing_time'] = round(stat['total_processing_time'] / stat['success_requests'], 3)
                
                # 移除临时字段
                del stat['total_processing_time']
            
            return list(api_stats.values())
        except Exception as e:
            logger.error(f"获取API性能统计失败: {e}")
            raise