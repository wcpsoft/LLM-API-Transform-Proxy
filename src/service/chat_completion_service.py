"""
Chat completion service for handling chat completion requests.
"""

from typing import Optional, Dict, Any, AsyncGenerator, Tuple, Type, Union
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import json
import time
import uuid

from src.service.interfaces import IChatCompletionService, IModelService, IApiKeyService, ILogService
from src.service.model_transformer_service import ModelTransformerService
from src.utils.logging import logger
from src.utils.multimodal import MultimodalProcessor
from src.providers.factory import ProviderFactory
from src.adapters.base import APIAdapterStrategy
from src.adapters.factory import AdapterFactory
from src.core.errors.exceptions import (
    ProviderError,
    ValidationError,
    ServiceUnavailableError
)


class ChatCompletionService(IChatCompletionService):
    """Chat completion service for handling chat completion requests."""
    
    def __init__(self, model_service: IModelService, api_key_service: IApiKeyService, 
                 log_service: ILogService, model_transformer_service=None):
        """初始化聊天补全服务"""
        self.model_service = model_service
        self.api_key_service = api_key_service
        self.log_service = log_service
        self.model_transformer_service = model_transformer_service
    
    def get_provider_and_adapter(self, provider_name: str) -> Tuple[Type, Type[APIAdapterStrategy]]:
        """
        Get provider and adapter classes for a provider.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Tuple of (provider_class, adapter_class)
            
        Raises:
            ValueError: If the provider is not supported
        """
        # Get provider class from factory registry
        provider_registry = ProviderFactory.get_registered_providers()
        if provider_name.lower() not in provider_registry:
            raise ValueError(f"Unsupported provider: {provider_name}")
        
        provider_class = provider_registry[provider_name.lower()]
        
        # Get adapter class from factory registry
        adapter_registry = AdapterFactory.get_registered_adapters()
        if provider_name.lower() not in adapter_registry:
            raise ValueError(f"No adapter available for provider: {provider_name}")
        
        adapter_class = adapter_registry[provider_name.lower()]
        
        return provider_class, adapter_class
    
    async def preprocess_multimodal_request(self, request_data: dict) -> dict:
        """
        Preprocess a multimodal request.
        
        Args:
            request_data: Request data
            
        Returns:
            Processed request data
            
        Raises:
            ValidationError: If the multimodal content is invalid
        """
        try:
            processed_request = request_data.copy()
            
            # Process multimodal content in messages
            if 'messages' in processed_request:
                processed_messages = []
                
                for message in processed_request['messages']:
                    processed_message = message.copy()
                    content = message.get('content')
                    
                    # If content is a list, process multimodal content
                    if isinstance(content, list):
                        # Process local files and mark images for download
                        processed_content = MultimodalProcessor.process_message_content(content)
                        # Download pending images
                        processed_content = await MultimodalProcessor.download_pending_images(processed_content)
                        processed_message['content'] = processed_content
                    
                    processed_messages.append(processed_message)
                
                processed_request['messages'] = processed_messages
            
            return processed_request
            
        except Exception as e:
            logger.error(f"Multimodal request preprocessing failed: {e}")
            raise ValidationError(
                message=f"Multimodal content processing failed: {str(e)}",
                field="messages.content",
                details={"error": str(e)}
            )
    
    def log_request(
        self,
        source_model: str,
        target_model: str,
        provider: str,
        request_data: dict,
        response_data: dict = None,
        status_code: int = 200,
        error_message: str = None,
        processing_time: float = 0,
        source_api: str = "/v1/chat/completions",
        request_id: str = None
    ) -> None:
        """
        Log a request to file and database.
        
        Args:
            source_model: Source model name
            target_model: Target model name
            provider: Provider name
            request_data: Request data
            response_data: Response data (optional)
            status_code: HTTP status code (optional)
            error_message: Error message (optional)
            processing_time: Processing time in seconds (optional)
            source_api: Source API endpoint (optional)
            request_id: Request ID (optional)
        """
        try:
            # Generate request ID if not provided
            if not request_id:
                request_id = str(uuid.uuid4())
            
            # Log to file system
            from src.utils.logging import log_api_request
            target_api = f"/{provider}/chat/completions"
            log_api_request(
                source_api=source_api,
                target_api=target_api,
                request_data=request_data,
                response_data=response_data,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time,
                request_id=request_id
            )
            
            # Log to database
            self.log_service.create_request_log(
                source_api=source_api,
                target_api=target_api,
                source_model=source_model,
                target_model=target_model,
                provider=provider,
                request_body=json.dumps(request_data, ensure_ascii=False),
                response_body=json.dumps(response_data, ensure_ascii=False) if response_data else None,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time,
                request_id=request_id
            )
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

    async def create_stream_response(
        self,
        source_model: str,
        processed_request: dict,
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False,
        request_id: str = None
    ) -> StreamingResponse:
        """
        Create a streaming response.
        
        Args:
            source_model: Source model name
            processed_request: Processed request data
            request_data: Original request data
            start_time: Request start time
            source_api: Source API endpoint (optional)
            use_transformer: Whether to use transformer mode (optional)
            provider_route_key: Provider route key (optional)
            anthropic_format: Whether to use Anthropic format (optional)
            request_id: Request ID (optional)
            
        Returns:
            Streaming response
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())
        
        async def generate_response() -> AsyncGenerator[str, None]:
            selected_key = None
            
            try:
                # Get model configuration
                if use_transformer:
                    selected_model = self.model_transformer_service.find_best_model(source_model, enable_transformer=True)
                    if not selected_model:
                        raise ServiceUnavailableError(
                            message=f"Model '{source_model}' not found",
                            details={"model": source_model}
                        )
                    
                    target_model = selected_model['target_model']
                    provider_name = selected_model['provider']
                    
                    # Get API key
                    selected_key = self.model_transformer_service.get_available_api_key(provider_name)
                    if not selected_key:
                        raise ServiceUnavailableError(
                            message=f"No available {provider_name} API key",
                            details={"provider": provider_name}
                        )
                else:
                    # Route to specific model by provider
                    models = self.model_service.get_models_by_route_key(provider_route_key)
                    if not models:
                        raise ServiceUnavailableError(
                            message=f"No available models for route key '{provider_route_key}'",
                            details={"route_key": provider_route_key}
                        )
                    
                    selected_model = models[0]
                    target_model = selected_model['target_model']
                    provider_name = selected_model['provider']
                    
                    # Get API key
                    api_keys = self.api_key_service.get_active_keys_by_provider(provider_name)
                    if not api_keys:
                        raise ServiceUnavailableError(
                            message=f"No available {provider_name} API key",
                            details={"provider": provider_name}
                        )
                    selected_key = api_keys[0]
                
                # Get provider and adapter
                provider_class, adapter_class = self.get_provider_and_adapter(provider_name)
                
                # Create provider instance using factory
                provider_config = {
                    "api_key": selected_key['api_key'],
                    "api_base": selected_model.get('api_base'),
                    "auth_header": selected_key.get('auth_header'),
                    "auth_format": selected_key.get('auth_format')
                }
                
                stream_provider = ProviderFactory.create_provider(provider_name, **provider_config)
                
                # Create adapter instance using factory
                stream_adapter = AdapterFactory.create_adapter(provider_name)
                
                # Adapt request
                stream_adapted_request = stream_adapter.adapt_request(processed_request, target_model)
                
                # Get streaming response
                response_generator = stream_provider.stream_chat_completion(stream_adapted_request)
                async for chunk in response_generator:
                    # Process response based on format requirements
                    if anthropic_format and provider_name == 'anthropic':
                        # Return raw response for Anthropic format
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        # Use adapter to transform response
                        adapted_chunk = stream_adapter.adapt_stream_response(chunk)
                        yield f"data: {json.dumps(adapted_chunk, ensure_ascii=False)}\n\n"
                
                yield "data: [DONE]\n\n"
                
                # Update API key statistics
                self.api_key_service.update_key_stats(selected_key['id'], success=True)
                
                # Log request
                processing_time = time.time() - start_time
                self.log_request(
                    source_model=source_model,
                    target_model=target_model,
                    provider=provider_name,
                    request_data=request_data,
                    response_data={"stream": True},
                    status_code=200,
                    error_message=None,
                    processing_time=processing_time,
                    source_api=source_api,
                    request_id=request_id
                )
                
            except Exception as e:
                logger.error(f"Streaming response generation failed: {e}")
                # Try to update statistics if key exists
                try:
                    if selected_key:
                        self.api_key_service.update_key_stats(selected_key['id'], success=False)
                except Exception:
                    pass
                
                # Return error response
                if isinstance(e, ProviderError):
                    error_response = e.to_dict()
                else:
                    error_response = {
                        "error": {
                            "message": str(e),
                            "type": "api_error",
                            "request_id": request_id
                        }
                    }
                
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    async def create_non_stream_response(
        self,
        source_model: str,
        processed_request: dict,
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Create a non-streaming response.
        
        Args:
            source_model: Source model name
            processed_request: Processed request data
            request_data: Original request data
            start_time: Request start time
            source_api: Source API endpoint (optional)
            use_transformer: Whether to use transformer mode (optional)
            provider_route_key: Provider route key (optional)
            anthropic_format: Whether to use Anthropic format (optional)
            request_id: Request ID (optional)
            
        Returns:
            Response data
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Get model configuration
        if use_transformer:
            selected_model = self.model_transformer_service.find_best_model(source_model, enable_transformer=True)
            if not selected_model:
                raise HTTPException(status_code=404, detail=f"Model '{source_model}' not found")
            
            target_model = selected_model['target_model']
            provider_name = selected_model['provider']
            
            # Get API key
            selected_key = self.model_transformer_service.get_available_api_key(provider_name)
            if not selected_key:
                raise HTTPException(status_code=503, detail=f"No available {provider_name} API key")
        else:
            # Route to specific model by provider
            models = self.model_service.get_models_by_route_key(provider_route_key)
            if not models:
                raise HTTPException(status_code=404, detail=f"No available models for route key '{provider_route_key}'")
            
            selected_model = models[0]
            target_model = selected_model['target_model']
            provider_name = selected_model['provider']
            
            # Get API key
            api_keys = self.api_key_service.get_active_keys_by_provider(provider_name)
            if not api_keys:
                raise HTTPException(status_code=503, detail=f"No available {provider_name} API key")
            selected_key = api_keys[0]
        
        # Get provider and adapter
        provider_class, adapter_class = self.get_provider_and_adapter(provider_name)
        
        # Create provider instance using factory
        provider_config = {
            "api_key": selected_key['api_key'],
            "api_base": selected_model.get('api_base'),
            "auth_header": selected_key.get('auth_header'),
            "auth_format": selected_key.get('auth_format')
        }
        
        provider = ProviderFactory.create_provider(provider_name, **provider_config)
        
        # Create adapter instance using factory
        adapter = AdapterFactory.create_adapter(provider_name)
        
        # Adapt request
        adapted_request = adapter.adapt_request(processed_request, target_model)
        
        # Call provider API
        response = await provider.chat_completion(adapted_request)
        
        # Process response based on format requirements
        if anthropic_format and provider_name == 'anthropic':
            # Return raw response for Anthropic format
            adapted_response = response
        else:
            # Use adapter to transform response
            adapted_response = adapter.adapt_response(response)
        
        # Update API key statistics
        self.api_key_service.update_key_stats(selected_key['id'], success=True)
        
        # Log request
        processing_time = time.time() - start_time
        self.log_request(
            source_model=source_model,
            target_model=target_model,
            provider=provider_name,
            request_data=request_data,
            response_data=adapted_response,
            status_code=200,
            error_message=None,
            processing_time=processing_time,
            source_api=source_api,
            request_id=request_id
        )
        
        return adapted_response
        
    async def handle_chat_completion(
        self,
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False,
        request_id: str = None
    ) -> Union[StreamingResponse, Dict[str, Any]]:
        """
        Handle a chat completion request.
        
        Args:
            request_data: Request data
            start_time: Request start time
            source_api: Source API endpoint (optional)
            use_transformer: Whether to use transformer mode (optional)
            provider_route_key: Provider route key (optional)
            anthropic_format: Whether to use Anthropic format (optional)
            request_id: Request ID (optional)
            
        Returns:
            Response data or streaming response
            
        Raises:
            HTTPException: If the request fails
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())
        
        try:
            # Get model information from request
            source_model = request_data.get('model', 'unknown')
            
            # Validate multimodal request
            if not MultimodalProcessor.validate_multimodal_request(request_data):
                raise ValidationError(
                    message="Invalid multimodal request format",
                    field="messages.content",
                    details={"request": request_data}
                )
            
            # Preprocess multimodal content
            processed_request = self.preprocess_multimodal_request(request_data)
            
            # Choose processing method based on streaming flag
            if request_data.get('stream', False):
                return await self.create_stream_response(
                    source_model=source_model,
                    processed_request=processed_request,
                    request_data=request_data,
                    start_time=start_time,
                    source_api=source_api,
                    use_transformer=use_transformer,
                    provider_route_key=provider_route_key,
                    anthropic_format=anthropic_format,
                    request_id=request_id
                )
            else:
                return await self.create_non_stream_response(
                    source_model=source_model,
                    processed_request=processed_request,
                    request_data=request_data,
                    start_time=start_time,
                    source_api=source_api,
                    use_transformer=use_transformer,
                    provider_route_key=provider_route_key,
                    anthropic_format=anthropic_format,
                    request_id=request_id
                )
                
        except ValidationError as e:
            # Convert validation errors to HTTP exceptions
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except ProviderError as e:
            # Convert provider errors to HTTP exceptions
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Chat completion request failed: {e}")
            processing_time = time.time() - start_time
            self.log_request(
                source_model=request_data.get('model', 'unknown'),
                target_model='unknown',
                provider_name='unknown',
                request_data=request_data,
                response_data=None,
                processing_time=processing_time,
                success=False,
                source_api=source_api,
                request_id=request_id
            )
            raise HTTPException(status_code=500, detail="Internal server error")