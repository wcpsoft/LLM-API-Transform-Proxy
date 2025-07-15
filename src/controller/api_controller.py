from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import duckdb
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.system_config_service import SystemConfigService
from src.service.log_service import LogService
from src.utils.logging import logger
from src.utils.multimodal import MultimodalProcessor
from src.providers.openai_provider import OpenAIProvider
from src.providers.anthropic_provider import AnthropicProvider
from src.providers.gemini_provider import GeminiProvider
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.anthropic_adapter import AnthropicAdapter
from src.adapters.gemini_adapter import GeminiAdapter
from datetime import datetime
import json
import time


router = APIRouter(prefix="/v1", tags=["api"])


def get_provider_and_adapter(provider_name: str):
    """获取提供商和适配器"""
    providers = {
        'openai': (OpenAIProvider, OpenAIAdapter),
        'anthropic': (AnthropicProvider, AnthropicAdapter),
        'gemini': (GeminiProvider, GeminiAdapter)
    }
    
    if provider_name not in providers:
        raise ValueError(f"不支持的提供商: {provider_name}")
    
    return providers[provider_name]


def log_request(source_model: str, target_model: str, provider: str, 
                request_data: dict, response_data: dict = None, 
                status_code: int = 200, error_message: str = None, 
                processing_time: float = 0):
    """记录请求日志"""
    try:
        log_service = LogService()
        log_service.create_request_log(
            timestamp=datetime.now(),
            source_model=source_model,
            target_model=target_model,
            provider=provider,
            request_data=json.dumps(request_data, ensure_ascii=False),
            response_data=json.dumps(response_data, ensure_ascii=False) if response_data else None,
            status_code=status_code,
            error_message=error_message,
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"记录请求日志失败: {e}")


def get_route_key_from_path(path: str) -> str:
    """从路径提取路由键"""
    # 移除前缀和后缀，提取模型名称
    if path.startswith('/v1/'):
        path = path[4:]
    if path.endswith('/completions'):
        path = path[:-12]
    return path


async def _preprocess_multimodal_request(request_data: dict) -> dict:
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


@router.post("/chat/completions")
async def chat_completions(request: Request):
    """统一聊天完成接口"""
    start_time = time.time()
    request_data = await request.json()
    
    try:
        # 从请求中获取模型信息
        source_model = request_data.get('model', 'unknown')
        
        # 验证多模态请求
        if not MultimodalProcessor.validate_multimodal_request(request_data):
            raise HTTPException(status_code=400, detail="无效的多模态请求格式")
        
        # 预处理多模态内容
        processed_request = await _preprocess_multimodal_request(request_data)
        
        # 根据关键词路由到具体模型
        models = ModelService.get_models_by_route_key('chat')
        if not models:
            raise HTTPException(status_code=404, detail="未找到可用的聊天模型")
        
        # 选择第一个可用模型（可以后续优化为负载均衡）
        selected_model = models[0]
        target_model = selected_model['target_model']
        provider_name = selected_model['provider']
        
        # 获取提供商和适配器
        provider_class, adapter_class = get_provider_and_adapter(provider_name)
        
        # 获取API密钥
        api_keys = ApiKeyService.get_active_keys_by_provider(provider_name)
        if not api_keys:
            raise HTTPException(status_code=503, detail=f"没有可用的{provider_name}密钥")
        
        # 选择API密钥（简单轮询，可以后续优化）
        selected_key = api_keys[0]
        
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
        if request_data.get('stream', False):
            # 流式响应
            response_generator = provider.stream_chat_completion(adapted_request)
            
            async def generate_response():
                try:
                    async for chunk in response_generator:
                        adapted_chunk = adapter.adapt_stream_response(chunk)
                        yield f"data: {json.dumps(adapted_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                    # 更新API密钥统计
                    ApiKeyService.update_key_stats(selected_key['id'], success=True)
                    
                    # 记录日志
                    processing_time = time.time() - start_time
                    log_request(source_model, target_model, provider_name, 
                               request_data, {"stream": True}, 200, None, processing_time)
                except Exception as e:
                    logger.error(f"流式响应生成失败: {e}")
                    ApiKeyService.update_key_stats(selected_key['id'], success=False)
                    error_response = {"error": {"message": str(e), "type": "api_error"}}
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                generate_response(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 非流式响应
            response = await provider.chat_completion(adapted_request)
            adapted_response = adapter.adapt_response(response)
            
            # 更新API密钥统计
            ApiKeyService.update_key_stats(selected_key['id'], success=True)
            
            # 记录日志
            processing_time = time.time() - start_time
            log_request(source_model, target_model, provider_name, 
                       request_data, adapted_response, 200, None, processing_time)
            
            return adapted_response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天完成请求失败: {e}")
        processing_time = time.time() - start_time
        log_request(source_model, 'unknown', 'unknown', 
                   request_data, None, 500, str(e), processing_time)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{provider}/completions")
async def provider_completions(provider: str, request: Request):
    """特定提供商的完成接口"""
    start_time = time.time()
    request_data = await request.json()
    
    try:
        source_model = request_data.get('model', 'unknown')
        
        # 验证多模态请求
        if not MultimodalProcessor.validate_multimodal_request(request_data):
            raise HTTPException(status_code=400, detail="无效的多模态请求格式")
        
        # 预处理多模态内容
        processed_request = await _preprocess_multimodal_request(request_data)
        
        # 根据提供商路由到具体模型
        models = ModelService.get_models_by_route_key(provider)
        if not models:
            raise HTTPException(status_code=404, detail=f"未找到可用的{provider}模型")
        
        # 选择第一个可用模型
        selected_model = models[0]
        target_model = selected_model['target_model']
        provider_name = selected_model['provider']
        
        # 获取提供商和适配器
        provider_class, adapter_class = get_provider_and_adapter(provider_name)
        
        # 获取API密钥
        api_keys = ApiKeyService.get_active_keys_by_provider(provider_name)
        if not api_keys:
            raise HTTPException(status_code=503, detail=f"没有可用的{provider_name}密钥")
        
        selected_key = api_keys[0]
        
        # 创建提供商实例
        provider_instance = provider_class(
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
        if request_data.get('stream', False):
            # 流式响应
            response_generator = provider_instance.stream_chat_completion(adapted_request)
            
            async def generate_response():
                try:
                    async for chunk in response_generator:
                        adapted_chunk = adapter.adapt_stream_response(chunk)
                        yield f"data: {json.dumps(adapted_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                    ApiKeyService.update_key_stats(selected_key['id'], success=True)
                    processing_time = time.time() - start_time
                    log_request(source_model, target_model, provider_name, 
                               request_data, {"stream": True}, 200, None, processing_time)
                except Exception as e:
                    logger.error(f"流式响应生成失败: {e}")
                    ApiKeyService.update_key_stats(selected_key['id'], success=False)
                    error_response = {"error": {"message": str(e), "type": "api_error"}}
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                generate_response(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 非流式响应
            response = await provider_instance.chat_completion(adapted_request)
            adapted_response = adapter.adapt_response(response)
            
            ApiKeyService.update_key_stats(selected_key['id'], success=True)
            processing_time = time.time() - start_time
            log_request(source_model, target_model, provider_name, 
                       request_data, adapted_response, 200, None, processing_time)
            
            return adapted_response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{provider}完成请求失败: {e}")
        processing_time = time.time() - start_time
        log_request(source_model, 'unknown', provider, 
                   request_data, None, 500, str(e), processing_time)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/models")
async def list_models():
    """列出所有可用模型"""
    try:
        models_and_providers = ModelService.get_all_models_and_providers()
        
        # 转换为OpenAI格式的模型列表
        models = []
        for provider, provider_models in models_and_providers.items():
            for model in provider_models:
                models.append({
                    "id": model,
                    "object": "model",
                    "created": int(datetime.now().timestamp()),
                    "owned_by": provider
                })
        
        return {"object": "list", "data": models}
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")


@router.get("/api-keys/stats")
async def get_api_key_stats():
    """获取API密钥统计信息"""
    try:
        stats = ApiKeyService.get_api_key_stats()
        return stats
    except Exception as e:
        logger.error(f"获取API密钥统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取API密钥统计失败")