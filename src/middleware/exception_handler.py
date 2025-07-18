"""
Exception handling middleware and utilities.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.service.log_service import LogService
from src.core.errors.exceptions import (
    ApiError,
    ValidationError,
    ProviderError,
    InternalError
)
from src.core.errors.handler import ErrorHandler

logger = logging.getLogger(__name__)
log_service = LogService()


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state for logging
        request.state.request_id = request_id
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log successful request
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_request(request, response.status_code, processing_time)
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._log_request(request, e.status_code, processing_time, str(e.detail))
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.detail,
                        "type": "http_error",
                        "request_id": request_id
                    }
                }
            )
            
        except ApiError as e:
            # Handle our custom API errors
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log the error with context
            context = {
                "request_id": request_id,
                "request_path": str(request.url.path),
                "request_method": request.method
            }
            ErrorHandler.log_error(e, context)
            
            await self._log_request(
                request, 
                e.status_code, 
                processing_time, 
                f"{e.message} ({e.error_code})"
            )
            
            # Create response with error details
            error_response = e.to_dict()
            error_response["error"]["request_id"] = request_id
            
            return JSONResponse(
                status_code=e.status_code,
                content=error_response
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Convert to internal error
            context = {
                "request_id": request_id,
                "request_path": str(request.url.path),
                "request_method": request.method
            }
            internal_error = ErrorHandler.handle_general_error(e, context)
            
            # Log the error
            logger.error(
                f"Unhandled exception {request_id}: {str(e)}\n"
                f"Request: {request.method} {request.url}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            await self._log_request(
                request, 
                internal_error.status_code, 
                processing_time, 
                f"{str(e)} (ID: {request_id})"
            )
            
            # Create response with error details
            error_response = internal_error.to_dict()
            error_response["error"]["request_id"] = request_id
            
            return JSONResponse(
                status_code=internal_error.status_code,
                content=error_response
            )
    
    async def _log_request(
        self, 
        request: Request, 
        status_code: int, 
        processing_time: float, 
        error_message: Optional[str] = None
    ):
        """Log request details."""
        try:
            # Get request information
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            
            # Get API-related information
            source_api = request.url.path
            target_api = request.headers.get("x-target-api", "")
            provider = request.headers.get("x-provider", "")
            
            # Create request log
            log_service.create_request_log(
                source_api=source_api,
                target_api=target_api,
                request_method=request.method,
                request_headers=dict(request.headers),
                request_body="",  # Skip request body for performance
                response_body="",  # Skip response body for performance
                client_ip=client_ip,
                user_agent=user_agent,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time,
                provider=provider,
                request_id=request_id
            )
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check proxy headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Return direct connection IP
        return request.client.host if request.client else "unknown"


def setup_exception_handlers(app):
    """Set up exception handlers for the application."""
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error_response = exc.to_dict()
        error_response["error"]["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=error_response)
    
    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error_response = exc.to_dict()
        error_response["error"]["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=error_response)
    
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        error_response = exc.to_dict()
        error_response["error"]["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=error_response)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        # Convert to internal error
        context = {
            "request_id": request_id,
            "request_path": str(request.url.path),
            "request_method": request.method
        }
        internal_error = ErrorHandler.handle_general_error(exc, context)
        
        # Create response with error details
        error_response = internal_error.to_dict()
        error_response["error"]["request_id"] = request_id
        
        return JSONResponse(
            status_code=internal_error.status_code,
            content=error_response
        )