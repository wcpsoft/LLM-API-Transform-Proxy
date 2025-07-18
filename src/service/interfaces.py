"""
Service interfaces for dependency injection and better abstraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from src.schemas import CreateModelRequest, UpdateModelRequest


class IChatCompletionService(ABC):
    """Interface for chat completion service."""
    
    @abstractmethod
    async def create_chat_completion(self, request_data: Dict[str, Any], source_api: str = "/v1/chat/completions") -> Any:
        """Create a chat completion."""
        pass
    
    @abstractmethod
    async def create_stream_response(self, source_model: str, processed_request: Dict[str, Any], 
                                   request_data: Dict[str, Any], start_time: float, 
                                   source_api: str = "/v1/chat/completions", 
                                   use_transformer: bool = True, 
                                   provider_route_key: Optional[str] = None,
                                   anthropic_format: bool = False, 
                                   request_id: str = None) -> Any:
        """Create a streaming response."""
        pass
    
    @abstractmethod
    async def preprocess_multimodal_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess a multimodal request."""
        pass


class IModelService(ABC):
    """Interface for model service."""
    
    @abstractmethod
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all model configurations."""
        pass
    
    @abstractmethod
    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID."""
        pass
    
    @abstractmethod
    def create_model(self, request: CreateModelRequest) -> Dict[str, Any]:
        """Create a new model configuration."""
        pass
    
    @abstractmethod
    def update_model(self, model_id: int, request: UpdateModelRequest) -> Dict[str, str]:
        """Update an existing model configuration."""
        pass
    
    @abstractmethod
    def delete_model(self, model_id: int) -> Dict[str, str]:
        """Delete a model configuration."""
        pass
    
    @abstractmethod
    def get_models_by_route_key(self, route_key: str) -> List[Dict[str, Any]]:
        """Get model configurations by route key."""
        pass
    
    @abstractmethod
    def validate_model_config(self, model_data: Dict[str, Any]) -> bool:
        """Validate model configuration."""
        pass


class ILogService(ABC):
    """Interface for log service."""
    
    @abstractmethod
    def create_request_log(self, **kwargs) -> None:
        """Create a request log entry."""
        pass


class IApiKeyService(ABC):
    """Interface for API key service."""
    
    @abstractmethod
    def get_active_keys_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Get active API keys for a provider."""
        pass