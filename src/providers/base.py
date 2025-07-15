from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator, Union
import httpx
import json
from src.utils.logging import logger

class BaseProvider(ABC):
    """API提供商基类"""
    
    def __init__(self, api_key: str, api_base: Optional[str] = None, 
                 auth_header: str = "Authorization", 
                 auth_format: str = "Bearer {api_key}"):
        self.name = self.__class__.__name__.replace('Provider', '').lower()
        self.api_key = api_key
        self.api_base = api_base
        self.auth_header = auth_header
        self.auth_format = auth_format
    
    @abstractmethod
    def get_default_endpoint(self) -> str:
        """获取默认API端点"""
        pass
    
    @abstractmethod
    def get_auth_header_name(self) -> str:
        """获取认证头名称"""
        pass
    
    @abstractmethod
    def format_auth_value(self, api_key: str) -> str:
        """格式化认证值"""
        pass
    
    @abstractmethod
    def get_endpoint_path(self) -> str:
        """获取API路径"""
        pass
    
    @abstractmethod
    async def chat_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """聊天完成API调用"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天完成API调用"""
        pass
    
    def build_url(self, api_base: Optional[str] = None) -> str:
        """构建完整的API URL"""
        base = api_base or self.api_base or self.get_default_endpoint()
        return f"{base.rstrip('/')}/{self.get_endpoint_path().lstrip('/')}"
    
    def build_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            self.auth_header: self.auth_format.format(api_key=self.api_key)
        }
        
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def make_request(self, 
                          body: Dict[str, Any], 
                          custom_headers: Optional[Dict[str, str]] = None,
                          stream: bool = False,
                          timeout: int = 30) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """发起API请求"""
        url = self.build_url()
        headers = self.build_headers(custom_headers)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if stream:
                    return self._handle_stream_response(client, url, headers, body)
                else:
                    return await self._handle_normal_response(client, url, headers, body)
        except httpx.TimeoutException as e:
            logger.error(f"请求超时: {url}")
            raise Exception(f"请求超时: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"HTTP错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"请求失败: {e}")
            raise
    
    async def _handle_normal_response(self, 
                                    client: httpx.AsyncClient, 
                                    url: str, 
                                    headers: Dict[str, str], 
                                    body: Dict[str, Any]) -> Dict[str, Any]:
        """处理普通响应"""
        try:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"API调用失败: {e.response.status_code} - {error_text}")
            raise Exception(f"API调用失败: {e.response.status_code}")
    
    async def _handle_stream_response(self, 
                                    client: httpx.AsyncClient, 
                                    url: str, 
                                    headers: Dict[str, str], 
                                    body: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """处理流式响应"""
        try:
            async with client.stream('POST', url, headers=headers, json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        if line.startswith('data: '):
                            data = line[6:].strip()
                            if data == '[DONE]':
                                break
                            try:
                                yield json.loads(data)
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"流式API调用失败: {e.response.status_code} - {error_text}")
            raise Exception(f"流式API调用失败: {e.response.status_code}")