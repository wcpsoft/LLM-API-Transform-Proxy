from typing import Dict, List, Any
from src.adapters.base import APIAdapterStrategy, register_adapter
from src.utils.multimodal import MultimodalProcessor
from src.utils.logging import logger


class OpenAIAdapter(APIAdapterStrategy):
    """OpenAI API适配器"""
    
    def supports_multimodal(self) -> bool:
        """OpenAI支持多模态"""
        return True
    
    def adapt_request(self, request: Dict[str, Any], target_model: str = None) -> Dict[str, Any]:
        """适配OpenAI请求"""
        try:
            adapted_request = request.copy()
            
            # 设置目标模型
            if target_model:
                adapted_request['model'] = target_model
            
            # 处理多模态内容
            if 'messages' in adapted_request:
                adapted_request['messages'] = self._process_messages(adapted_request['messages'])
            
            return adapted_request
            
        except Exception as e:
            logger.error(f"OpenAI请求适配失败: {e}")
            raise
    
    def adapt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """适配OpenAI响应"""
        try:
            # OpenAI响应格式已经是标准格式，直接返回
            return response
            
        except Exception as e:
            logger.error(f"OpenAI响应适配失败: {e}")
            raise
    
    def adapt_stream_response(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """适配OpenAI流式响应"""
        try:
            # OpenAI流式响应格式已经是标准格式，直接返回
            return chunk
            
        except Exception as e:
            logger.error(f"OpenAI流式响应适配失败: {e}")
            raise
    
    def _process_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理消息列表中的多模态内容"""
        processed_messages = []
        
        for message in messages:
            processed_message = message.copy()
            content = message.get('content')
            
            # 如果content是列表，处理多模态内容
            if isinstance(content, list):
                processed_content = MultimodalProcessor.process_message_content(content)
                processed_message['content'] = processed_content
            
            processed_messages.append(processed_message)
        
        return processed_messages
    
    def process_multimodal_content(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理多模态内容"""
        return MultimodalProcessor.process_message_content(content)


register_adapter('openai', OpenAIAdapter)