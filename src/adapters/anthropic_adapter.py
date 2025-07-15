from typing import Dict, List, Any
from src.adapters.base import APIAdapterStrategy, register_adapter
from src.utils.multimodal import MultimodalProcessor
from src.utils.logging import logger


class AnthropicAdapter(APIAdapterStrategy):
    """Anthropic Claude API适配器"""
    
    def supports_multimodal(self) -> bool:
        """Claude支持多模态"""
        return True
    
    def adapt_request(self, request: Dict[str, Any], target_model: str = None) -> Dict[str, Any]:
        """适配Anthropic请求"""
        try:
            adapted_request = {}
            
            # 设置模型
            adapted_request['model'] = target_model or request.get('model', 'claude-3-sonnet-20240229')
            
            # 设置最大tokens
            adapted_request['max_tokens'] = request.get('max_tokens', 4096)
            
            # 处理消息
            if 'messages' in request:
                adapted_request['messages'] = self._convert_messages_to_claude_format(request['messages'])
            
            # 处理其他参数
            if 'temperature' in request:
                adapted_request['temperature'] = request['temperature']
            if 'top_p' in request:
                adapted_request['top_p'] = request['top_p']
            if 'stream' in request:
                adapted_request['stream'] = request['stream']
            
            return adapted_request
            
        except Exception as e:
            logger.error(f"Anthropic请求适配失败: {e}")
            raise
    
    def adapt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """适配Anthropic响应为OpenAI格式"""
        try:
            # 转换Claude响应为OpenAI格式
            openai_response = {
                "id": response.get('id', 'chatcmpl-anthropic'),
                "object": "chat.completion",
                "created": response.get('created', 0),
                "model": response.get('model', 'claude-3-sonnet-20240229'),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.get('content', [{}])[0].get('text', '') if response.get('content') else ''
                    },
                    "finish_reason": self._convert_stop_reason(response.get('stop_reason'))
                }],
                "usage": {
                    "prompt_tokens": response.get('usage', {}).get('input_tokens', 0),
                    "completion_tokens": response.get('usage', {}).get('output_tokens', 0),
                    "total_tokens": response.get('usage', {}).get('input_tokens', 0) + response.get('usage', {}).get('output_tokens', 0)
                }
            }
            
            return openai_response
            
        except Exception as e:
            logger.error(f"Anthropic响应适配失败: {e}")
            raise
    
    def adapt_stream_response(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """适配Anthropic流式响应为OpenAI格式"""
        try:
            # 转换Claude流式响应为OpenAI格式
            if chunk.get('type') == 'content_block_delta':
                return {
                    "id": "chatcmpl-anthropic",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "claude-3-sonnet-20240229",
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": chunk.get('delta', {}).get('text', '')
                        },
                        "finish_reason": None
                    }]
                }
            elif chunk.get('type') == 'message_stop':
                return {
                    "id": "chatcmpl-anthropic",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "claude-3-sonnet-20240229",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
            else:
                # 其他类型的chunk，返回空的delta
                return {
                    "id": "chatcmpl-anthropic",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": "claude-3-sonnet-20240229",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }]
                }
            
        except Exception as e:
            logger.error(f"Anthropic流式响应适配失败: {e}")
            raise
    
    def _convert_messages_to_claude_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将OpenAI格式的消息转换为Claude格式"""
        claude_messages = []
        
        for message in messages:
            role = message.get('role')
            content = message.get('content')
            
            # 跳过system消息，Claude在messages中不支持system角色
            if role == 'system':
                continue
            
            claude_message = {
                'role': role,
                'content': self._convert_content_to_claude_format(content)
            }
            
            claude_messages.append(claude_message)
        
        return claude_messages
    
    def _convert_content_to_claude_format(self, content: Any) -> List[Dict[str, Any]]:
        """将内容转换为Claude格式"""
        if isinstance(content, str):
            # 纯文本内容
            return [{
                'type': 'text',
                'text': content
            }]
        elif isinstance(content, list):
            # 多模态内容
            claude_content = []
            
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get('type')
                    
                    if item_type == 'text':
                        claude_content.append({
                            'type': 'text',
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
                                claude_content.append({
                                    'type': 'image',
                                    'source': {
                                        'type': 'base64',
                                        'media_type': mime_type,
                                        'data': url.split(',')[1]  # 获取base64数据部分
                                    }
                                })
                            except Exception as e:
                                logger.warning(f"处理图片失败: {e}")
                                # 如果处理失败，转换为文本描述
                                claude_content.append({
                                    'type': 'text',
                                    'text': f'[图片: {url[:50]}...]'
                                })
                        else:
                            # 非data URL，转换为文本描述
                            claude_content.append({
                                'type': 'text',
                                'text': f'[图片: {url}]'
                            })
            
            return claude_content
        else:
            # 其他类型，转换为文本
            return [{
                'type': 'text',
                'text': str(content)
            }]
    
    def _convert_stop_reason(self, stop_reason: str) -> str:
        """转换停止原因"""
        mapping = {
            'end_turn': 'stop',
            'max_tokens': 'length',
            'stop_sequence': 'stop'
        }
        return mapping.get(stop_reason, 'stop')
    
    def process_multimodal_content(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理多模态内容"""
        return MultimodalProcessor.process_message_content(content)


register_adapter('anthropic', AnthropicAdapter)