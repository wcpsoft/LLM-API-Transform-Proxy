"""
Service factory for dependency injection and service management.
"""

from typing import Optional
from src.service.interfaces import IChatCompletionService, IModelService, IApiKeyService, ILogService
from src.service.chat_completion_service import ChatCompletionService
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.log_service import LogService
from src.service.model_transformer_service import ModelTransformerService
from src.dao.model_dao import ModelDAO
from src.dao.api_key_dao import ApiKeyDAO
from src.dao.log_dao import LogDAO


class ServiceFactory:
    """Factory class for creating and managing services with dependency injection."""
    
    _instance: Optional['ServiceFactory'] = None
    _services: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._services = {}
    
    def get_model_service(self) -> IModelService:
        """Get model service instance."""
        if 'model_service' not in self._services:
            model_dao = ModelDAO()
            self._services['model_service'] = ModelService(model_dao)
        return self._services['model_service']
    
    def get_api_key_service(self) -> IApiKeyService:
        """Get API key service instance."""
        if 'api_key_service' not in self._services:
            api_key_dao = ApiKeyDAO()
            self._services['api_key_service'] = ApiKeyService(api_key_dao)
        return self._services['api_key_service']
    
    def get_log_service(self) -> ILogService:
        """Get log service instance."""
        if 'log_service' not in self._services:
            log_dao = LogDAO()
            self._services['log_service'] = LogService(log_dao)
        return self._services['log_service']
    
    def get_model_transformer_service(self) -> ModelTransformerService:
        """Get model transformer service instance."""
        if 'model_transformer_service' not in self._services:
            self._services['model_transformer_service'] = ModelTransformerService()
        return self._services['model_transformer_service']
    
    def get_chat_completion_service(self) -> IChatCompletionService:
        """Get chat completion service instance."""
        if 'chat_completion_service' not in self._services:
            model_service = self.get_model_service()
            api_key_service = self.get_api_key_service()
            log_service = self.get_log_service()
            model_transformer_service = self.get_model_transformer_service()
            
            self._services['chat_completion_service'] = ChatCompletionService(
                model_service=model_service,
                api_key_service=api_key_service,
                log_service=log_service,
                model_transformer_service=model_transformer_service
            )
        return self._services['chat_completion_service']
    
    def reset(self):
        """Reset all cached services."""
        self._services.clear()


# Global service factory instance
service_factory = ServiceFactory()