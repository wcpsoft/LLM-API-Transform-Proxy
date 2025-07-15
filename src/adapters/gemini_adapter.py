from typing import Dict, List, Any
from src.adapters.base import APIAdapterStrategy, register_adapter
from src.utils.multimodal import MultimodalProcessor
from src.utils.logging import logger
import time


class GeminiAdapter(APIAdapterStrategy):
    """Google Gemini API适配器"""
    
    def supports_multimodal(self) -> bool:
        """Gemini支持多模态"""
        return True
    
    def adapt_request(self, request: Dict[str, Any], target_model: str = None) -> Dict[str, Any]:
        """适配Gemini请求"""
        try:
            adapted_request = {}
            
            # Gemini使用contents而不是messages
            if 'messages' in request:
                adapted_request['contents'] = self._convert_messages_to_gemini_format(request['messages'])
            
            # 处理生成配置
            generation_config = {}
            
            if 'temperature' in request:
                generation_config['temperature'] = request['temperature']
            if 'top_p' in request:
                generation_config['topP'] = request['top_p']
            if 'max_tokens' in request:
                generation_config['maxOutputTokens'] = request['max_tokens']
            
            if generation_config:
                adapted_request['generationConfig'] = generation_config
            
            # Gemini的流式参数在URL中处理，这里不需要
            
            return adapted_request
            
        except Exception as e:
            logger.error(f"Gemini请求适配失败: {e}")
            raise
    
    def adapt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """适配Gemini响应为OpenAI格式"""
        try:
            # 转换Gemini响应为OpenAI格式
            candidates = response.get('candidates', [])
            
            if not candidates:
                content = ''
                finish_reason = 'stop'
            else:
                candidate = candidates[0]
                content_parts = candidate.get('content', {}).get('parts', [])
                content = ''.join([part.get('text', '') for part in content_parts])
                finish_reason = self._convert_finish_reason(candidate.get('finishReason'))
            
            openai_response = {
                "id": f"chatcmpl-gemini-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "gemini-pro",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": finish_reason
                }],
                "usage": {
                    "prompt_tokens": response.get('usageMetadata', {}).get('promptTokenCount', 0),
                    "completion_tokens": response.get('usageMetadata', {}).get('candidatesTokenCount', 0),
                    "total_tokens": response.get('usageMetadata', {}).get('totalTokenCount', 0)
                }
            }
            
            return openai_response
            
        except Exception as e:
            logger.error(f"Gemini响应适配失败: {e}")
            raise
    
    def adapt_stream_response(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """适配Gemini流式响应为OpenAI格式"""
        try:
            candidates = chunk.get('candidates', [])
            
            if not candidates:
                delta_content = ''
                finish_reason = None
            else:
                candidate = candidates[0]
                content_parts = candidate.get('content', {}).get('parts', [])
                delta_content = ''.join([part.get('text', '') for part in content_parts])
                finish_reason = self._convert_finish_reason(candidate.get('finishReason')) if candidate.get('finishReason') else None
            
            openai_chunk = {
                "id": f"chatcmpl-gemini-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gemini-pro",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": delta_content
                    } if delta_content else {},
                    "finish_reason": finish_reason
                }]
            }
            
            return openai_chunk
            
        except Exception as e:
            logger.error(f"Gemini流式响应适配失败: {e}")
            raise
    
    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将OpenAI格式的消息转换为Gemini格式"""
        gemini_contents = []
        
        for message in messages:
            role = message.get('role')
            content = message.get('content')
            
            # 转换角色
            gemini_role = self._convert_role(role)
            if not gemini_role:
                continue  # 跳过不支持的角色
            
            gemini_content = {
                'role': gemini_role,
                'parts': self._convert_content_to_gemini_format(content)
            }
            
            gemini_contents.append(gemini_content)
        
        return gemini_contents
    
    def _convert_role(self, role: str) -> str:
        """转换角色"""
        role_mapping = {
            'user': 'user',
            'assistant': 'model',
            'system': None  # Gemini不支持system角色
        }
        return role_mapping.get(role)
    
    def _convert_content_to_gemini_format(self, content: Any) -> List[Dict[str, Any]]:
        """将内容转换为Gemini格式"""
        if isinstance(content, str):
            # 纯文本内容
            return [{
                'text': content
            }]
        elif isinstance(content, list):
            # 多模态内容
            gemini_parts = []
            
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get('type')
                    
                    if item_type == 'text':
                        gemini_parts.append({
                            'text': item.get('text', '')
                        })
                    elif item_type == 'image_url':
                        # 处理图片
                        image_url = item.get('image_url', {})
                        url = image_url.get('url', '')
                        
                        if url.startswith('data:'):
                            # 解析data URL
                            try:
                                mime_type, image_data = MultimodalProcessor.extract_base64_data(url)
                                gemini_parts.append({
                                    'inlineData': {
                                        'mimeType': mime_type,
                                        'data': url.split(',')[1]  # 获取base64数据部分
                                    }
                                })
                            except Exception as e:
                                logger.warning(f"处理图片失败: {e}")
                                # 如果处理失败，转换为文本描述
                                gemini_parts.append({
                                    'text': f'[图片: {url[:50]}...]'
                                })
                        else:
                            # 非data URL，转换为文本描述
                            gemini_parts.append({
                                'text': f'[图片: {url}]'
                            })
            
            return gemini_parts
        else:
            # 其他类型，转换为文本
            return [{
                'text': str(content)
            }]
    
    def _convert_finish_reason(self, finish_reason: str) -> str:
        """转换完成原因"""
        if not finish_reason:
            return 'stop'
            
        mapping = {
            'STOP': 'stop',
            'MAX_TOKENS': 'length',
            'SAFETY': 'content_filter',
            'RECITATION': 'content_filter',
            'OTHER': 'stop'
        }
        return mapping.get(finish_reason, 'stop')
    
    def process_multimodal_content(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理多模态内容"""
        return MultimodalProcessor.process_message_content(content)


register_adapter('gemini', GeminiAdapter)