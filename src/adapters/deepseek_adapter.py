from typing import Dict, List, Any
import time
from src.adapters.base import APIAdapterStrategy, register_adapter
from src.utils.multimodal import MultimodalProcessor
from src.utils.logging import logger


class DeepSeekAdapter(APIAdapterStrategy):
    """DeepSeek API适配器 - 将OpenAI格式转换为Claude格式"""
    
    def __init__(self):
        super().__init__()
        self.original_model = None  # 保存原始请求的模型名称
    
    def supports_multimodal(self) -> bool:
        """DeepSeek支持多模态"""
        return True
    
    def adapt_request(self, request: Dict[str, Any], target_model: str = None) -> Dict[str, Any]:
        """适配DeepSeek请求 - 将OpenAI格式转换为Claude格式"""
        try:
            adapted_request = {}
            
            # 模型映射：根据claude-4关键词决定使用哪个模型
            model = target_model or request.get('model', 'deepseek-chat')
            self.original_model = model  # 保存原始模型名称
            if 'claude' in model.lower():
                adapted_request['model'] = 'deepseek-reasoner'
            else:
                adapted_request['model'] = 'deepseek-reasoner'
            
            max_tokens = request.get('max_tokens', 4096)
            adapted_request['max_tokens'] = max_tokens
            
            # 处理消息 - 转换为Claude格式
            if 'messages' in request:
                adapted_request['messages'] = self._convert_messages_to_claude_format(request['messages'])
            
            # 处理其他参数
            if 'temperature' in request:
                adapted_request['temperature'] = request['temperature']
            
            if 'top_p' in request:
                adapted_request['top_p'] = request['top_p']
            
            if 'stream' in request:
                adapted_request['stream'] = request['stream']
            
            # 处理stop参数
            if 'stop' in request:
                adapted_request['stop_sequences'] = request['stop'] if isinstance(request['stop'], list) else [request['stop']]
            
            return adapted_request
            
        except Exception as e:
            logger.error(f"DeepSeek请求适配失败: {e}")
            raise
    
    def adapt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """适配DeepSeek响应为OpenAI格式"""
        try:
            logger.info(f"DeepSeek API响应: {response}")
            
            # 检查是否已经是Claude格式，需要转换为OpenAI格式
            if response.get('type') == 'message' and 'content' in response:
                # 是Claude格式，转换为OpenAI格式
                logger.info("DeepSeek响应是Claude格式，转换为OpenAI格式")
                
                # 提取文本内容
                content_text = ""
                if isinstance(response.get('content'), list):
                    for item in response['content']:
                        if item.get('type') == 'text':
                            content_text += item.get('text', '')
                
                # 转换为OpenAI格式
                openai_response = {
                    "id": response.get('id', 'chatcmpl-deepseek'),
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": self.original_model or response.get('model', 'deepseek-chat'),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content_text
                        },
                        "finish_reason": self._convert_stop_reason_from_claude(response.get('stop_reason'))
                    }],
                    "usage": {
                        "prompt_tokens": response.get('usage', {}).get('input_tokens', 0),
                        "completion_tokens": response.get('usage', {}).get('output_tokens', 0),
                        "total_tokens": response.get('usage', {}).get('input_tokens', 0) + response.get('usage', {}).get('output_tokens', 0)
                    }
                }
                
                logger.info(f"转换后的OpenAI格式响应: {openai_response}")
                return openai_response
            
            # 如果是OpenAI格式，检查是否需要处理reasoning_content
            choices = response.get('choices', [])
            if choices:
                logger.info("DeepSeek响应已经是OpenAI格式")
                
                # 检查是否有reasoning_content需要处理
                choice = choices[0]
                message = choice.get('message', {})
                content = message.get('content', '')
                reasoning_content = message.get('reasoning_content', '')
                
                # 如果content为空但有reasoning_content，使用reasoning_content
                if not content and reasoning_content:
                    logger.info("将reasoning_content作为content返回")
                    adapted_response = response.copy()
                    adapted_response['choices'] = [{
                        **choice,
                        'message': {
                            **message,
                            'content': reasoning_content,
                            'reasoning_content': None  # 清除reasoning_content
                        }
                    }]
                    return adapted_response
                
                return response
            
            # 异常情况，创建默认响应
            logger.warning("DeepSeek响应格式异常")
            return {
                "id": response.get('id', 'chatcmpl-deepseek'),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self.original_model or response.get('model', 'deepseek-chat'),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": "error"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            
        except Exception as e:
            logger.error(f"DeepSeek响应适配失败: {e}")
            raise
    
    def adapt_stream_response(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """适配DeepSeek流式响应为OpenAI格式"""
        # DeepSeek-reasoner模型有两个阶段：
        # 1. 推理阶段：content为null，reasoning_content包含推理过程
        # 2. 输出阶段：reasoning_content为null，content包含最终回答
        # 我们需要将reasoning_content也作为有效内容返回
        
        if 'choices' in chunk and len(chunk['choices']) > 0:
            choice = chunk['choices'][0]
            delta = choice.get('delta', {})
            
            # 如果有reasoning_content但content为null，使用reasoning_content
            if delta.get('content') is None and delta.get('reasoning_content'):
                # 创建新的chunk，将reasoning_content作为content返回
                adapted_chunk = chunk.copy()
                adapted_chunk['choices'] = [{
                    **choice,
                    'delta': {
                        **delta,
                        'content': delta.get('reasoning_content'),
                        'reasoning_content': None  # 清除reasoning_content避免重复
                    }
                }]
                return adapted_chunk
        
        # 其他情况直接返回原始chunk
        return chunk
    
    def _convert_messages_to_claude_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将OpenAI消息格式转换为Claude格式"""
        claude_messages = []
        system_message = None
        
        for message in messages:
            role = message.get('role')
            content = message.get('content')
            
            if role == 'system':
                # Claude将system消息单独处理
                system_message = content
            elif role in ['user', 'assistant']:
                claude_message = {
                    'role': role,
                    'content': self._convert_content_to_claude_format(content)
                }
                claude_messages.append(claude_message)
        
        # 如果有system消息，添加到第一个用户消息前
        if system_message and claude_messages:
            if claude_messages[0]['role'] == 'user':
                # 将system消息合并到第一个user消息中
                first_content = claude_messages[0]['content']
                if isinstance(first_content, list) and first_content and first_content[0].get('type') == 'text':
                    first_content[0]['text'] = f"{system_message}\n\n{first_content[0]['text']}"
                elif isinstance(first_content, str):
                    claude_messages[0]['content'] = [{
                        'type': 'text',
                        'text': f"{system_message}\n\n{first_content}"
                    }]
        
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
                    if item.get('type') == 'text':
                        claude_content.append({
                            'type': 'text',
                            'text': item.get('text', '')
                        })
                    elif item.get('type') == 'image_url':
                        # 处理图片
                        image_url = item.get('image_url', {})
                        if isinstance(image_url, dict):
                            url = image_url.get('url', '')
                            if url.startswith('data:'):
                                # base64图片
                                data_info = MultimodalProcessor.extract_data_from_data_url(url)
                                if data_info:
                                    claude_content.append({
                                        'type': 'image',
                                        'source': {
                                            'type': 'base64',
                                            'media_type': data_info['mime_type'],
                                            'data': data_info['data']
                                        }
                                    })
                            else:
                                # URL图片
                                claude_content.append({
                                    'type': 'image',
                                    'source': {
                                        'type': 'url',
                                        'url': url
                                    }
                                })
            return claude_content
        else:
            # 其他类型，转为文本
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
    
    def _convert_stop_reason_to_claude(self, finish_reason: str) -> str:
        """将OpenAI格式的finish_reason转换为Claude格式的stop_reason"""
        mapping = {
            'stop': 'end_turn',
            'length': 'max_tokens',
            'content_filter': 'stop_sequence',
            'function_call': 'end_turn',
            'tool_calls': 'end_turn'
        }
        return mapping.get(finish_reason, 'end_turn')
    
    def _convert_stop_reason_from_claude(self, stop_reason: str) -> str:
        """将Claude格式的stop_reason转换为OpenAI格式的finish_reason"""
        mapping = {
            'end_turn': 'stop',
            'max_tokens': 'length',
            'stop_sequence': 'stop'
        }
        return mapping.get(stop_reason, 'stop')


# 注册适配器
register_adapter('deepseek', DeepSeekAdapter)