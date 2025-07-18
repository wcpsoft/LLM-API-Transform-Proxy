"""
错误传播上下文 - 提供完整的错误链追踪和上下文信息
"""
import time
import traceback
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_type: str
    message: str
    timestamp: datetime
    stack_trace: str
    correlation_id: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "severity": self.severity,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "context_data": self.context_data,
            "stack_trace": self.stack_trace
        }


class ErrorPropagationContext:
    """错误传播上下文，携带完整的错误链信息"""
    
    def __init__(self, error: Exception, context: Dict[str, Any] = None):
        self.error = error
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.correlation_id = self._generate_correlation_id()
        self.stack_trace = traceback.format_exc()
        self.error_chain: List[ErrorContext] = []
        
    def _generate_correlation_id(self) -> str:
        """生成唯一的关联ID"""
        return str(uuid.uuid4())
    
    def add_error_context(self, error_context: ErrorContext):
        """添加错误上下文到错误链"""
        self.error_chain.append(error_context)
    
    def create_error_context(
        self,
        error_type: str,
        message: str,
        severity: str = "ERROR",
        **kwargs
    ) -> ErrorContext:
        """创建错误上下文"""
        return ErrorContext(
            error_type=error_type,
            message=message,
            timestamp=datetime.utcnow(),
            stack_trace=self.stack_trace,
            correlation_id=self.correlation_id,
            severity=severity,
            context_data=kwargs
        )
    
    def get_full_error_chain(self) -> List[Dict[str, Any]]:
        """获取完整的错误链信息"""
        return [ctx.to_dict() for ctx in self.error_chain]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            "correlation_id": self.correlation_id,
            "total_errors": len(self.error_chain),
            "first_error_time": self.error_chain[0].timestamp.isoformat() if self.error_chain else self.timestamp.isoformat(),
            "last_error_time": self.error_chain[-1].timestamp.isoformat() if self.error_chain else self.timestamp.isoformat(),
            "error_types": list(set(ctx.error_type for ctx in self.error_chain))
        }