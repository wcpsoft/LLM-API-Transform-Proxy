from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import json
import time
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.model_transformer_service import ModelTransformerService
from src.utils.logging import logger
from src.utils.multimodal import MultimodalProcessor


class ChatCompletionService:
    """聊天完成服务 - 抽象通用的聊天完成逻辑"""
    
    @staticmethod
    def get_provider_and_adapter(provider_name: str):
        """获取提供商和适配器"""
        from src.providers.openai_provider import OpenAIProvider
        from src.providers.anthropic_provider import AnthropicProvider
        from src.providers.gemini_provider import GeminiProvider
        from src.providers.deepseek_provider import DeepSeekProvider
        from src.adapters.openai_adapter import OpenAIAdapter
        from src.adapters.anthropic_adapter import AnthropicAdapter
        from src.adapters.gemini_adapter import GeminiAdapter
        from src.adapters.deepseek_adapter import DeepSeekAdapter
        
        providers = {
            'openai': (OpenAIProvider, OpenAIAdapter),
            'anthropic': (AnthropicProvider, AnthropicAdapter),
            'gemini': (GeminiProvider, GeminiAdapter),
            'deepseek': (DeepSeekProvider, DeepSeekAdapter)
        }
        
        if provider_name not in providers:
            raise ValueError(f"不支持的提供商: {provider_name}")
        
        return providers[provider_name]
    
    @staticmethod
    async def preprocess_multimodal_request(request_data: dict) -> dict:
        """预处理多模态请求"""
        try:
            processed_request = request_data.copy()
            
            # 处理消息中的多模态内容
            if 'messages' in processed_request:
                processed_messages = []
                
                for message in processed_request['messages']:
                    processed_message = message.copy()
                    content = message.get('content')
                    
                    # 如果content是列表，处理多模态内容
                    if isinstance(content, list):
                        # 先处理本地文件和标记需要下载的图片
                        processed_content = MultimodalProcessor.process_message_content(content)
                        # 下载需要下载的图片
                        processed_content = await MultimodalProcessor.download_pending_images(processed_content)
                        processed_message['content'] = processed_content
                    
                    processed_messages.append(processed_message)
                
                processed_request['messages'] = processed_messages
            
            return processed_request
            
        except Exception as e:
            logger.error(f"多模态请求预处理失败: {e}")
            raise HTTPException(status_code=400, detail=f"多模态内容处理失败: {str(e)}")
    
    @staticmethod
    def log_request(source_model: str, target_model: str, provider: str, 
                    request_data: dict, response_data: dict = None, 
                    status_code: int = 200, error_message: str = None, 
                    processing_time: float = 0, source_api: str = "/v1/chat/completions"):
        """记录请求日志到文件和DuckDB"""
        try:
            # 记录到文件系统
            from src.utils.logging import log_api_request
            target_api = f"/{provider}/chat/completions"
            log_api_request(
                source_api=source_api,
                target_api=target_api,
                request_data=request_data,
                response_data=response_data,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time
            )
            
            # 记录到DuckDB
            from src.service.log_service import LogService
            log_service = LogService()
            log_service.create_request_log(
                source_api=source_api,
                target_api=target_api,
                source_model=source_model,
                target_model=target_model,
                provider=provider,
                request_body=json.dumps(request_data, ensure_ascii=False),
                response_body=json.dumps(response_data, ensure_ascii=False) if response_data else None,
                status_code=status_code,
                error_message=error_message,
                processing_time=processing_time
            )
        except Exception as e:
            logger.error(f"记录请求日志失败: {e}")
    
    @staticmethod
    async def create_stream_response(
        source_model: str,
        processed_request: dict,
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False
    ) -> StreamingResponse:
        """创建流式响应"""
        
        async def generate_response() -> AsyncGenerator[str, None]:
            try:
                # 获取模型配置
                if use_transformer:
                    selected_model = ModelTransformerService.find_best_model(source_model, enable_transformer=True)
                    if not selected_model:
                        raise Exception(f"未找到模型 '{source_model}' 的配置")
                    
                    target_model = selected_model['target_model']
                    provider_name = selected_model['provider']
                    
                    # 获取API密钥
                    selected_key = ModelTransformerService.get_available_api_key(provider_name)
                    if not selected_key:
                        raise Exception(f"没有可用的{provider_name}密钥")
                else:
                    # 根据提供商路由到具体模型
                    models = ModelService.get_models_by_route_key(provider_route_key)
                    if not models:
                        raise Exception(f"未找到可用的{provider_route_key}模型")
                    
                    selected_model = models[0]
                    target_model = selected_model['target_model']
                    provider_name = selected_model['provider']
                    
                    # 获取API密钥
                    api_keys = ApiKeyService.get_active_keys_by_provider(provider_name)
                    if not api_keys:
                        raise Exception(f"没有可用的{provider_name}密钥")
                    selected_key = api_keys[0]
                
                # 获取提供商和适配器
                provider_class, adapter_class = ChatCompletionService.get_provider_and_adapter(provider_name)
                
                # 创建provider实例
                stream_provider = provider_class(
                    api_key=selected_key['api_key'],
                    api_base=selected_model.get('api_base'),
                    auth_header=selected_key.get('auth_header', 'Authorization'),
                    auth_format=selected_key.get('auth_format', 'Bearer {api_key}')
                )
                
                # 创建适配器实例
                stream_adapter = adapter_class()
                
                # 适配请求
                stream_adapted_request = stream_adapter.adapt_request(processed_request, target_model)
                
                # 获取流式响应
                response_generator = stream_provider.stream_chat_completion(stream_adapted_request)
                async for chunk in response_generator:
                    # 根据格式要求处理响应
                    if anthropic_format and provider_name == 'anthropic':
                        # Anthropic格式直接返回原始响应
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        # 使用适配器转换
                        adapted_chunk = stream_adapter.adapt_stream_response(chunk)
                        yield f"data: {json.dumps(adapted_chunk, ensure_ascii=False)}\n\n"
                
                yield "data: [DONE]\n\n"
                
                # 更新API密钥统计
                ApiKeyService.update_key_stats(selected_key['id'], success=True)
                
                # 记录日志
                processing_time = time.time() - start_time
                ChatCompletionService.log_request(
                    source_model, target_model, provider_name, 
                    request_data, {"stream": True}, 200, None, processing_time, source_api
                )
                
            except Exception as e:
                logger.error(f"流式响应生成失败: {e}")
                # 尝试更新统计，但如果key不存在就跳过
                try:
                    if 'selected_key' in locals():
                        ApiKeyService.update_key_stats(selected_key['id'], success=False)
                except:
                    pass
                error_response = {"error": {"message": str(e), "type": "api_error"}}
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    @staticmethod
    async def create_non_stream_response(
        source_model: str,
        processed_request: dict,
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False
    ) -> Dict[str, Any]:
        """创建非流式响应"""
        
        # 获取模型配置
        if use_transformer:
            selected_model = ModelTransformerService.find_best_model(source_model, enable_transformer=True)
            if not selected_model:
                raise HTTPException(status_code=404, detail=f"未找到模型 '{source_model}' 的配置")
            
            target_model = selected_model['target_model']
            provider_name = selected_model['provider']
            
            # 获取API密钥
            selected_key = ModelTransformerService.get_available_api_key(provider_name)
            if not selected_key:
                raise HTTPException(status_code=503, detail=f"没有可用的{provider_name}密钥")
        else:
            # 根据提供商路由到具体模型
            models = ModelService.get_models_by_route_key(provider_route_key)
            if not models:
                raise HTTPException(status_code=404, detail=f"未找到可用的{provider_route_key}模型")
            
            selected_model = models[0]
            target_model = selected_model['target_model']
            provider_name = selected_model['provider']
            
            # 获取API密钥
            api_keys = ApiKeyService.get_active_keys_by_provider(provider_name)
            if not api_keys:
                raise HTTPException(status_code=503, detail=f"没有可用的{provider_name}密钥")
            selected_key = api_keys[0]
        
        # 获取提供商和适配器
        provider_class, adapter_class = ChatCompletionService.get_provider_and_adapter(provider_name)
        
        # 创建提供商实例
        provider = provider_class(
            api_key=selected_key['api_key'],
            api_base=selected_model.get('api_base'),
            auth_header=selected_key.get('auth_header', 'Authorization'),
            auth_format=selected_key.get('auth_format', 'Bearer {api_key}')
        )
        
        # 创建适配器实例
        adapter = adapter_class()
        
        # 适配请求
        adapted_request = adapter.adapt_request(processed_request, target_model)
        
        # 调用提供商API
        response = await provider.chat_completion(adapted_request)
        
        # 根据格式要求处理响应
        if anthropic_format and provider_name == 'anthropic':
            # Anthropic格式直接返回原始响应
            adapted_response = response
        else:
            # 使用适配器转换
            adapted_response = adapter.adapt_response(response)
        
        # 更新API密钥统计
        ApiKeyService.update_key_stats(selected_key['id'], success=True)
        
        # 记录日志
        processing_time = time.time() - start_time
        ChatCompletionService.log_request(
            source_model, target_model, provider_name, 
            request_data, adapted_response, 200, None, processing_time, source_api
        )
        
        return adapted_response
    
    @staticmethod
    async def handle_chat_completion(
        request_data: dict,
        start_time: float,
        source_api: str = "/v1/chat/completions",
        use_transformer: bool = True,
        provider_route_key: Optional[str] = None,
        anthropic_format: bool = False
    ):
        """处理聊天完成请求的通用逻辑"""
        
        try:
            # 从请求中获取模型信息
            source_model = request_data.get('model', 'unknown')
            
            # 验证多模态请求
            if not MultimodalProcessor.validate_multimodal_request(request_data):
                raise HTTPException(status_code=400, detail="无效的多模态请求格式")
            
            # 预处理多模态内容
            processed_request = await ChatCompletionService.preprocess_multimodal_request(request_data)
            
            # 根据是否流式响应选择处理方式
            if request_data.get('stream', False):
                return await ChatCompletionService.create_stream_response(
                    source_model=source_model,
                    processed_request=processed_request,
                    request_data=request_data,
                    start_time=start_time,
                    source_api=source_api,
                    use_transformer=use_transformer,
                    provider_route_key=provider_route_key,
                    anthropic_format=anthropic_format
                )
            else:
                return await ChatCompletionService.create_non_stream_response(
                    source_model=source_model,
                    processed_request=processed_request,
                    request_data=request_data,
                    start_time=start_time,
                    source_api=source_api,
                    use_transformer=use_transformer,
                    provider_route_key=provider_route_key,
                    anthropic_format=anthropic_format
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"聊天完成请求失败: {e}")
            processing_time = time.time() - start_time
            ChatCompletionService.log_request(
                source_model, 'unknown', 'unknown', 
                request_data, None, 500, str(e), processing_time, source_api
            )
            raise HTTPException(status_code=500, detail="内部服务器错误")