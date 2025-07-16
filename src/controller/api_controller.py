from fastapi import APIRouter, HTTPException, Request
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.chat_completion_service import ChatCompletionService
from src.utils.logging import logger
from datetime import datetime
import time


router = APIRouter(prefix="/v1", tags=["api"])



@router.post("/chat/completions")
async def chat_completions(request: Request):
    """统一聊天完成接口"""
    start_time = time.time()
    logger.info("收到聊天完成请求")
    request_data = await request.json()
    logger.info(f"请求数据: {request_data}")
    
    return await ChatCompletionService.handle_chat_completion(
        request_data=request_data,
        start_time=start_time,
        source_api="/v1/chat/completions",
        use_transformer=True
    )


@router.post("/provider/{provider_name}/completions")
async def provider_completions(provider_name: str, request: Request):
    """特定提供商的聊天完成接口"""
    start_time = time.time()
    logger.info(f"收到{provider_name}聊天完成请求")
    request_data = await request.json()
    logger.info(f"请求数据: {request_data}")
    
    return await ChatCompletionService.handle_chat_completion(
        request_data=request_data,
        start_time=start_time,
        source_api=f"/v1/provider/{provider_name}/completions",
        use_transformer=False,
        provider_filter=provider_name
    )


@router.post("/messages")
async def anthropic_messages(request: Request):
    """Anthropic Messages API兼容接口"""
    start_time = time.time()
    logger.info("收到Anthropic Messages请求")
    request_data = await request.json()
    logger.info(f"请求数据: {request_data}")
    
    # 为Anthropic Messages API设置默认模型
    if 'model' not in request_data:
        request_data['model'] = 'claude-3-sonnet-20240229'
    
    return await ChatCompletionService.handle_chat_completion(
        request_data=request_data,
        start_time=start_time,
        source_api="/v1/messages",
        use_transformer=True
    )


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