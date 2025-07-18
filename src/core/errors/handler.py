"""
Error handler for the application.
"""

import traceback
import httpx
from typing import Dict, Any, Optional, Type, Union, Tuple
from src.core.errors.exceptions import (
    ApiError,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    InternalError
)
from src.utils.logging import logger


class ErrorHandler:
    """
    Error handler for the application.
    
    This class provides methods for handling different types of errors
    and converting them to standardized ApiError instances.
    """
    
    @staticmethod
    def handle_provider_error(
        error: Exception,
        provider: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ApiError:
        """
        Handle a provider error.
        
        Args:
            error: The original exception
            provider: Provider name
            context: Additional context information
            
        Returns:
            An ApiError instance
        """
        context = context or {}
        
        # If it's already an ApiError, just return it
        if isinstance(error, ApiError):
            return error
        
        # Handle httpx errors
        if isinstance(error, httpx.HTTPStatusError):
            return ErrorHandler._handle_http_status_error(error, provider, context)
        elif isinstance(error, httpx.TimeoutException):
            return ServiceUnavailableError(
                message=f"Request to {provider} timed out",
                provider=provider,
                details={"original_error": str(error), **context}
            )
        elif isinstance(error, httpx.RequestError):
            return ServiceUnavailableError(
                message=f"Error connecting to {provider}",
                provider=provider,
                details={"original_error": str(error), **context}
            )
        
        # Handle other errors
        return ProviderError(
            message=f"Error from {provider}: {str(error)}",
            provider=provider,
            details={"original_error": str(error), **context}
        )
    
    @staticmethod
    def _handle_http_status_error(
        error: httpx.HTTPStatusError,
        provider: str,
        context: Dict[str, Any]
    ) -> ApiError:
        """
        Handle an HTTP status error.
        
        Args:
            error: The HTTP status error
            provider: Provider name
            context: Additional context information
            
        Returns:
            An ApiError instance
        """
        status_code = error.response.status_code
        
        try:
            response_json = error.response.json()
        except Exception:
            response_json = {}
        
        error_message = ErrorHandler._extract_error_message(response_json) or str(error)
        
        # Handle specific status codes
        if status_code == 401:
            return AuthenticationError(
                message=f"Authentication failed for {provider}: {error_message}",
                provider=provider,
                details={"original_error": error_message, **context}
            )
        elif status_code == 429:
            retry_after = error.response.headers.get("Retry-After")
            retry_after = int(retry_after) if retry_after and retry_after.isdigit() else None
            
            return RateLimitError(
                message=f"Rate limit exceeded for {provider}: {error_message}",
                provider=provider,
                retry_after=retry_after,
                details={"original_error": error_message, **context}
            )
        elif status_code >= 500:
            return ServiceUnavailableError(
                message=f"Service {provider} is unavailable: {error_message}",
                provider=provider,
                details={"original_error": error_message, **context}
            )
        else:
            return ProviderError(
                message=f"Error from {provider}: {error_message}",
                provider=provider,
                status_code=status_code,
                details={"original_error": error_message, **context}
            )
    
    @staticmethod
    def _extract_error_message(response_json: Dict[str, Any]) -> Optional[str]:
        """
        Extract an error message from a JSON response.
        
        Args:
            response_json: JSON response from the provider
            
        Returns:
            Error message or None
        """
        # Common error message patterns
        if "error" in response_json:
            error = response_json["error"]
            if isinstance(error, str):
                return error
            elif isinstance(error, dict):
                if "message" in error:
                    return error["message"]
                elif "error" in error:
                    return error["error"]
        
        if "message" in response_json:
            return response_json["message"]
        
        return None
    
    @staticmethod
    def handle_general_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ApiError:
        """
        Handle a general error.
        
        Args:
            error: The original exception
            context: Additional context information
            
        Returns:
            An ApiError instance
        """
        context = context or {}
        
        # If it's already an ApiError, just return it
        if isinstance(error, ApiError):
            return error
        
        # Log the error with traceback
        logger.error(f"Unhandled error: {error}")
        logger.error(traceback.format_exc())
        
        # Return a generic internal error
        return InternalError(
            message=f"Internal server error: {str(error)}",
            details={"original_error": str(error), **context}
        )
    
    @staticmethod
    def log_error(
        error: Union[Exception, ApiError],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with context.
        
        Args:
            error: The error to log
            context: Additional context information
        """
        context = context or {}
        
        if isinstance(error, ApiError):
            log_context = {
                "error_type": error.__class__.__name__,
                "error_code": error.error_code,
                "status_code": error.status_code,
                **error.details,
                **context
            }
            logger.error(f"{error.message}", extra=log_context)
        else:
            log_context = {
                "error_type": error.__class__.__name__,
                **context
            }
            logger.error(f"Error: {str(error)}", extra=log_context)
            logger.error(traceback.format_exc())