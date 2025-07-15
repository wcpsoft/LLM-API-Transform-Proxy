import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.service.log_service import LogService

logger = logging.getLogger(__name__)
log_service = LogService()


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()
        
        try:
            response = await call_next(request)
            
            # 记录成功请求
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_request(request, response.status_code, processing_time)
            
            return response
            
        except HTTPException as e:
            # 处理HTTP异常
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_request(request, e.status_code, processing_time, str(e.detail))
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.status_code,
                        "message": e.detail,
                        "timestamp": datetime.now().isoformat(),
                        "path": str(request.url.path)
                    }
                }
            )
            
        except Exception as e:
            # 处理未预期的异常
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_id = self._generate_error_id()
            error_message = f"Internal server error (ID: {error_id})"
            
            # 记录详细错误信息
            logger.error(
                f"Unhandled exception {error_id}: {str(e)}\n"
                f"Request: {request.method} {request.url}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            await self._log_request(request, 500, processing_time, f"{str(e)} (ID: {error_id})")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": error_message,
                        "error_id": error_id,
                        "timestamp": datetime.now().isoformat(),
                        "path": str(request.url.path)
                    }
                }
            )
    
    async def _log_request(self, request: Request, status_code: int, 
                          processing_time: float, error_message: Optional[str] = None):
        """记录请求日志"""
        try:
            # 获取请求信息
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            # 获取API相关信息
            source_api = request.url.path
            target_api = request.headers.get("x-target-api", "")
            provider = request.headers.get("x-provider", "")
            
            # 创建请求日志
            log_service.create_request_log(
                source_api=source_api,
                target_api=target_api,
                request_method=request.method,
                request_headers=dict(request.headers),
                request_body="",  # 出于性能考虑，不记录请求体
                response_body="",  # 出于性能考虑，不记录响应体
                client_ip=client_ip,
                user_agent=user_agent,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time,
                provider=provider
            )
        except Exception as e:
            logger.error(f"记录请求日志失败: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # 返回直接连接的IP
        return request.client.host if request.client else "unknown"
    
    def _generate_error_id(self) -> str:
        """生成错误ID"""
        import uuid
        return str(uuid.uuid4())[:8]


class ValidationException(Exception):
    """验证异常"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class BusinessException(Exception):
    """业务异常"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ExternalAPIException(Exception):
    """外部API异常"""
    def __init__(self, message: str, provider: str = None, status_code: int = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(self.message)


def setup_exception_handlers(app):
    """设置异常处理器"""
    
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": 400,
                    "message": exc.message,
                    "field": exc.field,
                    "type": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                    "path": str(request.url.path)
                }
            }
        )
    
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": 422,
                    "message": exc.message,
                    "business_code": exc.code,
                    "type": "business_error",
                    "timestamp": datetime.now().isoformat(),
                    "path": str(request.url.path)
                }
            }
        )
    
    @app.exception_handler(ExternalAPIException)
    async def external_api_exception_handler(request: Request, exc: ExternalAPIException):
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": 502,
                    "message": exc.message,
                    "provider": exc.provider,
                    "upstream_status": exc.status_code,
                    "type": "external_api_error",
                    "timestamp": datetime.now().isoformat(),
                    "path": str(request.url.path)
                }
            }
        )