from typing import Dict, Any, AsyncGenerator, Optional
from .base import BaseProvider

class GeminiProvider(BaseProvider):
    """Google Gemini API提供商"""
    
    def get_default_endpoint(self) -> str:
        return "https://generativelanguage.googleapis.com"
    
    def get_auth_header_name(self) -> str:
        return "Authorization"
    
    def format_auth_value(self, api_key: str) -> str:
        return f"Bearer {api_key}"
    
    def get_endpoint_path(self) -> str:
        return "v1beta/models/gemini-pro:generateContent"
    
    def _convert_openai_to_gemini(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """将OpenAI格式转换为Gemini格式"""
        gemini_request = {
            "contents": [],
            "generationConfig": {}
        }
        
        # 转换消息格式
        for msg in request_data.get("messages", []):
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_request["contents"].append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        # 转换生成配置
        if "temperature" in request_data:
            gemini_request["generationConfig"]["temperature"] = request_data["temperature"]
        if "max_tokens" in request_data:
            gemini_request["generationConfig"]["maxOutputTokens"] = request_data["max_tokens"]
        if "top_p" in request_data:
            gemini_request["generationConfig"]["topP"] = request_data["top_p"]
            
        return gemini_request
    
    def build_url(self, api_base: Optional[str] = None) -> str:
        """构建Gemini API URL (使用API key作为查询参数)"""
        base = api_base or self.api_base or self.get_default_endpoint()
        url = f"{base.rstrip('/')}/{self.get_endpoint_path().lstrip('/')}"
        return f"{url}?key={self.api_key}"
    
    def build_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """构建请求头 (Gemini不需要Authorization头)"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gemini聊天完成API调用"""
        gemini_request = self._convert_openai_to_gemini(request_data)
        
        return await self.make_request(gemini_request, stream=False)
    
    async def stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Gemini流式聊天完成API调用"""
        # Gemini的流式API端点不同
        original_endpoint = self.get_endpoint_path()
        self.__class__.get_endpoint_path = lambda self: "v1beta/models/gemini-pro:streamGenerateContent"
        
        try:
            gemini_request = self._convert_openai_to_gemini(request_data)
            async for chunk in self.make_request(gemini_request, stream=True):
                yield chunk
        finally:
            # 恢复原始端点
            self.__class__.get_endpoint_path = lambda self: original_endpoint