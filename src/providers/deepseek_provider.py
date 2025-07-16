from typing import Dict, Any, AsyncGenerator
from .base import BaseProvider

class DeepSeekProvider(BaseProvider):
    """DeepSeek API提供商"""
    
    def get_default_endpoint(self) -> str:
        return "https://api.deepseek.com"
    
    def get_auth_header_name(self) -> str:
        return "Authorization"
    
    def format_auth_value(self, api_key: str) -> str:
        return f"Bearer {api_key}"
    
    def get_endpoint_path(self) -> str:
        return "chat/completions"
    
    async def chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """DeepSeek聊天完成API调用"""
        request_body = request_data.copy()
        request_body['stream'] = False
        
        return await self.make_request(request_body, stream=False)
    
    async def stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """DeepSeek流式聊天完成API调用"""
        request_body = request_data.copy()
        request_body['stream'] = True
        
        async for chunk in await self.make_request(request_body, stream=True):
            yield chunk