#!/usr/bin/env python3
"""
增强的错误日志记录器 - 实现结构化错误日志和上下文信息
"""
import json
import logging
import traceback
import time
from typing import Any, Dict, Optional, Union
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ErrorContext:
    """错误上下文信息"""
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.endpoint = endpoint
        self.method = method
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.extra_context = extra_context or {}
        self.timestamp = datetime.utcnow().isoformat()


class StructuredErrorLogger:
    """结构化错误日志记录器"""
    
    def __init__(self, logger_name: str = "error_logger"):
        self.logger = logging.getLogger(logger_name)
    
    def _create_error_payload(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        level: str = "ERROR",
        stack_trace: bool = True
    ) -> Dict[str, Any]:
        """创建错误负载"""
        
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_code": getattr(error, "error_code", None),
            "request_id": getattr(context, "request_id", None) if context else None,
            "context": self._serialize_context(context) if context else {},
            "metadata": {
                "python_version": f"{traceback.sys.version_info.major}.{traceback.sys.version_info.minor}",
                "process_id": traceback.os.getpid(),
                "thread_id": traceback.threading.current_thread().ident
            }
        }
        
        if stack_trace:
            payload["stack_trace"] = traceback.format_exc()
        
        # 添加特定错误类型的额外信息
        if hasattr(error, 'response'):
            payload["response"] = str(getattr(error, 'response'))
        
        if hasattr(error, 'status_code'):
            payload["http_status"] = getattr(error, 'status_code')
        
        if hasattr(error, 'provider'):
            payload["provider"] = getattr(error, 'provider')
        
        return payload
    
    def _serialize_context(self, context: ErrorContext) -> Dict[str, Any]:
        """序列化上下文信息"""
        return {
            "request_id": context.request_id,
            "user_id": context.user_id,
            "api_key": self._mask_sensitive_data(context.api_key),
            "model": context.model,
            "provider": context.provider,
            "endpoint": context.endpoint,
            "method": context.method,
            "ip_address": context.ip_address,
            "user_agent": context.user_agent,
            "extra_context": context.extra_context,
            "timestamp": context.timestamp
        }
    
    def _mask_sensitive_data(self, data: Optional[str]) -> str:
        """脱敏敏感数据"""
        if not data:
            return None
        
        if len(data) <= 8:
            return "***"
        
        return f"{data[:4]}...{data[-4:]}"
    
    def log_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        level: str = "ERROR",
        extra: Optional[Dict[str, Any]] = None
    ):
        """记录错误日志"""
        
        payload = self._create_error_payload(error, context, level)
        
        if extra:
            payload.update(extra)
        
        # 记录到标准日志
        self.logger.error(json.dumps(payload, ensure_ascii=False))
        
        # 同时记录到专门的错误日志文件
        self._log_to_file(payload)
    
    def log_warning(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """记录警告日志"""
        
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "message": message,
            "request_id": getattr(context, "request_id", None) if context else None,
            "context": self._serialize_context(context) if context else {}
        }
        
        if extra:
            payload.update(extra)
        
        self.logger.warning(json.dumps(payload, ensure_ascii=False))
    
    def _log_to_file(self, payload: Dict[str, Any]):
        """记录到专门的错误日志文件"""
        try:
            log_file = f"logs/errors_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
            
            # 确保日志目录存在
            import os
            os.makedirs("logs", exist_ok=True)
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"无法写入错误日志文件: {e}")


class ErrorReporter:
    """错误报告器 - 用于监控和告警"""
    
    def __init__(self, logger: StructuredErrorLogger):
        self.logger = logger
        self.error_counts = {}
        self.last_report_time = time.time()
    
    def report_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        severity: str = "medium"
    ):
        """报告错误"""
        
        error_type = type(error).__name__
        
        # 更新错误计数
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # 记录错误
        self.logger.log_error(error, context, level="ERROR")
        
        # 检查是否需要发送告警
        self._check_alert_conditions(error_type, context, severity)
    
    def _check_alert_conditions(
        self,
        error_type: str,
        context: Optional[ErrorContext],
        severity: str
    ):
        """检查告警条件"""
        
        current_time = time.time()
        
        # 每5分钟检查一次
        if current_time - self.last_report_time < 300:
            return
        
        self.last_report_time = current_time
        
        # 检查错误频率
        for err_type, count in self.error_counts.items():
            if count >= 10:  # 5分钟内超过10次相同错误
                self._send_alert(err_type, count, context, severity)
        
        # 重置计数
        self.error_counts.clear()
    
    def _send_alert(
        self,
        error_type: str,
        count: int,
        context: Optional[ErrorContext],
        severity: str
    ):
        """发送告警"""
        
        alert_payload = {
            "alert_type": "error_frequency",
            "error_type": error_type,
            "count": count,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "context": {
                "provider": getattr(context, "provider", None) if context else None,
                "model": getattr(context, "model", None) if context else None,
                "endpoint": getattr(context, "endpoint", None) if context else None
            }
        }
        
        # 这里可以集成实际的告警系统
        logger.critical(f"高频错误告警: {json.dumps(alert_payload, ensure_ascii=False)}")


class ErrorMetrics:
    """错误指标统计"""
    
    def __init__(self):
        self.success_counts = {}
        self.failure_counts = {}
        self.circuit_breaker_states = {}
    
    def record_success(self, circuit_breaker_name: str):
        """记录成功"""
        if circuit_breaker_name not in self.success_counts:
            self.success_counts[circuit_breaker_name] = 0
        self.success_counts[circuit_breaker_name] += 1
    
    def record_failure(self, circuit_breaker_name: str):
        """记录失败"""
        if circuit_breaker_name not in self.failure_counts:
            self.failure_counts[circuit_breaker_name] = 0
        self.failure_counts[circuit_breaker_name] += 1
    
    def get_stats(self, circuit_breaker_name: str) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "success": self.success_counts.get(circuit_breaker_name, 0),
            "failure": self.failure_counts.get(circuit_breaker_name, 0),
            "total": self.success_counts.get(circuit_breaker_name, 0) + 
                    self.failure_counts.get(circuit_breaker_name, 0)
        }


# 全局错误日志记录器实例
error_logger = StructuredErrorLogger()
error_reporter = ErrorReporter(error_logger)
error_metrics = ErrorMetrics()