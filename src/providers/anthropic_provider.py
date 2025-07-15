from typing import Dict, Any, AsyncGenerator
from .base import BaseProvider

class AnthropicProvider(BaseProvider):
    """Anthropic API提供商"""
    
    def get_default_endpoint(self) -> str:
        return "https://api.anthropic.com"
    
    def get_auth_header_name(self) -> str:
        return "x-api-key"
    
    def format_auth_value(self, api_key: str) -> str:
        return api_key
    
    def get_endpoint_path(self) -> str:
        return "v1/messages"
    
    def _convert_openai_to_anthropic(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """将OpenAI格式转换为Anthropic格式"""
        anthropic_request = {
            "model": request_data.get("model", "claude-3-sonnet-20240229"),
            "max_tokens": request_data.get("max_tokens", 1024),
            "messages": []
        }
        
        # 转换消息格式
        for msg in request_data.get("messages", []):
            if msg["role"] == "system":
                anthropic_request["system"] = msg["content"]
            else:
                anthropic_request["messages"].append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 添加其他参数
        if "temperature" in request_data:
            anthropic_request["temperature"] = request_data["temperature"]
        if "top_p" in request_data:
            anthropic_request["top_p"] = request_data["top_p"]
        if "stream" in request_data:
            anthropic_request["stream"] = request_data["stream"]
            
        return anthropic_request
    
    async def chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anthropic聊天完成API调用"""
        anthropic_request = self._convert_openai_to_anthropic(request_data)
        anthropic_request['stream'] = False
        
        # 添加Anthropic特有的头部
        custom_headers = {
            "anthropic-version": "2023-06-01"
        }
        
        return await self.make_request(anthropic_request, custom_headers=custom_headers, stream=False)
    
    async def stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Anthropic流式聊天完成API调用"""
        anthropic_request = self._convert_openai_to_anthropic(request_data)
        anthropic_request['stream'] = True
        
        # 添加Anthropic特有的头部
        custom_headers = {
            "anthropic-version": "2023-06-01"
        }
        
        async for chunk in self.make_request(anthropic_request, custom_headers=custom_headers, stream=True):
            yield chunk