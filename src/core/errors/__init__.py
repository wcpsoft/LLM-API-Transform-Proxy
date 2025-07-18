"""
Error handling framework for the application.
"""

from src.core.errors.exceptions import (
    ApiError,
    ConfigurationError,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    AdapterError,
    ValidationError,
    InternalError
)

from src.core.errors.handler import ErrorHandler

__all__ = [
    'ApiError',
    'ConfigurationError',
    'ProviderError',
    'AuthenticationError',
    'RateLimitError',
    'ServiceUnavailableError',
    'AdapterError',
    'ValidationError',
    'InternalError',
    'ErrorHandler'
]