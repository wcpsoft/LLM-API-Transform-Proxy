"""
Exception classes for the error handling framework.
"""

from typing import Dict, Any, Optional


class ApiError(Exception):
    """Base class for API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for API clients
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        result = {
            "error": {
                "message": self.message,
                "type": self.error_code
            }
        }
        
        if self.details:
            result["error"]["details"] = self.details
        
        return result


class ConfigurationError(ApiError):
    """Error related to configuration."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            details: Additional error details
        """
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            status_code=500,
            error_code="configuration_error",
            details=error_details
        )


class ProviderError(ApiError):
    """Error related to a provider."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int = 500,
        error_code: str = "provider_error",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the provider error.
        
        Args:
            message: Error message
            provider: Provider name
            status_code: HTTP status code
            error_code: Error code for API clients
            details: Additional error details
        """
        error_details = details or {}
        error_details["provider"] = provider
        
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            details=error_details
        )


class AuthenticationError(ProviderError):
    """Error related to authentication with a provider."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the authentication error.
        
        Args:
            message: Error message
            provider: Provider name
            details: Additional error details
        """
        super().__init__(
            message=message,
            provider=provider,
            status_code=401,
            error_code="authentication_error",
            details=details
        )


class RateLimitError(ProviderError):
    """Error related to rate limiting by a provider."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the rate limit error.
        
        Args:
            message: Error message
            provider: Provider name
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        error_details = details or {}
        if retry_after is not None:
            error_details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            provider=provider,
            status_code=429,
            error_code="rate_limit_error",
            details=error_details
        )


class ServiceUnavailableError(ProviderError):
    """Error related to a provider being unavailable."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the service unavailable error.
        
        Args:
            message: Error message
            provider: Provider name
            details: Additional error details
        """
        super().__init__(
            message=message,
            provider=provider,
            status_code=503,
            error_code="service_unavailable",
            details=details
        )


class AdapterError(ApiError):
    """Error related to an adapter."""
    
    def __init__(
        self,
        message: str,
        adapter: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the adapter error.
        
        Args:
            message: Error message
            adapter: Adapter name
            details: Additional error details
        """
        error_details = details or {}
        error_details["adapter"] = adapter
        
        super().__init__(
            message=message,
            status_code=500,
            error_code="adapter_error",
            details=error_details
        )


class ValidationError(ApiError):
    """Error related to request validation."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            details: Additional error details
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            status_code=400,
            error_code="validation_error",
            details=error_details
        )


class InternalError(ApiError):
    """Error related to internal server issues."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the internal error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code="internal_error",
            details=details
        )