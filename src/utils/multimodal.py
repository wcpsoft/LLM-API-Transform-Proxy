"""多模态内容处理工具模块"""

import base64
import mimetypes
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import re
from urllib.parse import urlparse
import httpx
from src.utils.logging import logger


class MultimodalProcessor:
    """多模态内容处理器"""
    
    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
        'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml'
    }
    
    # 支持的文档格式
    SUPPORTED_DOCUMENT_FORMATS = {
        'application/pdf', 'text/plain', 'text/markdown',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    @staticmethod
    def is_base64_image(content: str) -> bool:
        """检查内容是否为base64编码的图片"""
        if not content:
            return False
            
        # 检查是否有data URL前缀
        if content.startswith('data:image/'):
            return True
            
        # 检查是否为纯base64字符串
        try:
            # 移除可能的换行符和空格
            clean_content = re.sub(r'\s+', '', content)
            
            # 检查base64字符集
            if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', clean_content):
                return False
            
            # 检查是否为有效的base64
            decoded = base64.b64decode(clean_content, validate=True)
            
            # 检查是否为图片格式（通过文件头）
            image_signatures = [
                b'\xff\xd8\xff',  # JPEG
                b'\x89PNG\r\n\x1a\n',  # PNG
                b'GIF87a',  # GIF87a
                b'GIF89a',  # GIF89a
                b'RIFF',  # WebP (需要进一步检查)
                b'BM',  # BMP
                b'<svg',  # SVG
            ]
            
            for signature in image_signatures:
                if decoded.startswith(signature):
                    return True
            
            # 检查WebP格式
            if decoded.startswith(b'RIFF') and b'WEBP' in decoded[:12]:
                return True
                
            return len(clean_content) > 100  # 假设图片至少100字符
        except Exception:
            return False
    
    @staticmethod
    def encode_image_to_base64(image_path: Union[str, Path]) -> str:
        """将图片文件编码为base64字符串"""
        try:
            path = Path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type not in MultimodalProcessor.SUPPORTED_IMAGE_FORMATS:
                raise ValueError(f"不支持的图片格式: {mime_type}")
            
            # 读取并编码
            if mime_type == 'image/svg+xml':
                # SVG文件使用文本模式读取
                with open(path, 'r', encoding='utf-8') as f:
                    image_data = f.read().encode('utf-8')
            else:
                # 其他图片格式使用二进制模式读取
                with open(path, 'rb') as f:
                    image_data = f.read()
            
            encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
            
        except Exception as e:
            logger.error(f"图片编码失败: {e}")
            raise
    
    @staticmethod
    async def download_and_encode_image(url: str) -> str:
        """下载网络图片并编码为base64"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                
                # 获取内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise ValueError(f"URL不是图片: {content_type}")
                
                if content_type not in MultimodalProcessor.SUPPORTED_IMAGE_FORMATS:
                    raise ValueError(f"不支持的图片格式: {content_type}")
                
                # 编码图片数据
                encoded = base64.b64encode(response.content).decode('utf-8')
                return f"data:{content_type};base64,{encoded}"
                
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
            raise
    
    @staticmethod
    def extract_base64_data(data_url: str) -> tuple[str, bytes]:
        """从data URL中提取MIME类型和二进制数据"""
        try:
            if not data_url.startswith('data:'):
                raise ValueError("不是有效的data URL")
            
            # 解析data URL格式: data:mime_type;base64,data
            header, data = data_url.split(',', 1)
            mime_info = header.split(';')[0].split(':')[1]
            
            # 解码base64数据
            binary_data = base64.b64decode(data)
            
            return mime_info, binary_data
            
        except Exception as e:
            logger.error(f"解析data URL失败: {e}")
            raise
    
    @staticmethod
    def extract_data_from_data_url(data_url: str) -> dict:
        """从data URL中提取数据"""
        try:
            if not data_url.startswith('data:'):
                return None
            
            # 解析data URL格式: data:[<mediatype>][;base64],<data>
            header, data = data_url.split(',', 1)
            
            # 提取MIME类型
            if ';base64' in header:
                mime_type = header.replace('data:', '').replace(';base64', '')
                is_base64 = True
            else:
                mime_type = header.replace('data:', '')
                is_base64 = False
            
            if not mime_type:
                mime_type = 'text/plain'
            
            return {
                'mime_type': mime_type,
                'data': data,
                'is_base64': is_base64
            }
            
        except Exception as e:
            logger.error(f"解析data URL失败: {e}")
            return None
    
    @staticmethod
    def process_message_content(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理消息内容中的多模态元素"""
        processed_content = []
        
        for item in content:
            if isinstance(item, dict):
                item_type = item.get('type')
                
                if item_type == 'text':
                    # 文本内容直接保留
                    processed_content.append(item)
                    
                elif item_type == 'image_url':
                    # 处理图片URL
                    image_url = item.get('image_url', {})
                    url = image_url.get('url', '')
                    
                    if url.startswith('data:'):
                        # 已经是base64编码，直接保留
                        processed_content.append(item)
                    elif url.startswith(('http://', 'https://')):
                        # 网络图片，标记需要下载
                        processed_item = item.copy()
                        processed_item['_needs_download'] = True
                        processed_content.append(processed_item)
                    elif Path(url).exists():
                        # 本地文件路径，编码为base64
                        try:
                            encoded_url = MultimodalProcessor.encode_image_to_base64(url)
                            processed_item = item.copy()
                            processed_item['image_url']['url'] = encoded_url
                            processed_content.append(processed_item)
                        except Exception as e:
                            logger.warning(f"处理本地图片失败: {e}")
                            processed_content.append(item)
                    else:
                        # 其他情况直接保留
                        processed_content.append(item)
                        
                else:
                    # 其他类型直接保留
                    processed_content.append(item)
            else:
                # 非字典类型直接保留
                processed_content.append(item)
        
        return processed_content
    
    @staticmethod
    async def download_pending_images(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """下载待处理的图片"""
        processed_content = []
        
        for item in content:
            # 检查是否需要下载（_needs_download可能在item级别或image_url级别）
            needs_download = (item.get('_needs_download') or 
                            item.get('image_url', {}).get('_needs_download'))
            
            if item.get('type') == 'image_url' and needs_download:
                try:
                    url = item['image_url']['url']
                    # 下载并转换为base64
                    data_url = await MultimodalProcessor.download_and_encode_image(url)
                    
                    # 创建新的item，移除下载标记
                    new_item = {}
                    for key, value in item.items():
                        if key != '_needs_download':
                            new_item[key] = value
                    
                    # 处理image_url对象
                    new_item['image_url'] = {}
                    for key, value in item['image_url'].items():
                        if key == 'url':
                            new_item['image_url'][key] = data_url
                        elif key != '_needs_download':
                            new_item['image_url'][key] = value
                    
                    processed_content.append(new_item)
                    
                except Exception as e:
                    logger.warning(f"下载图片失败，保持原URL: {e}")
                    # 保持原URL，但移除下载标记
                    new_item = {}
                    for key, value in item.items():
                        if key != '_needs_download':
                            new_item[key] = value
                    
                    # 处理image_url对象，移除下载标记
                    new_item['image_url'] = {}
                    for key, value in item['image_url'].items():
                        if key != '_needs_download':
                            new_item['image_url'][key] = value
                    
                    processed_content.append(new_item)
            else:
                # 对于不需要下载的item，直接复制（但移除可能存在的下载标记）
                new_item = {}
                for key, value in item.items():
                    if key != '_needs_download':
                        new_item[key] = value
                
                # 如果有image_url，也要处理其中的下载标记
                if 'image_url' in new_item and isinstance(new_item['image_url'], dict):
                    clean_image_url = {}
                    for key, value in new_item['image_url'].items():
                        if key != '_needs_download':
                            clean_image_url[key] = value
                    new_item['image_url'] = clean_image_url
                
                processed_content.append(new_item)
        
        return processed_content
    
    @staticmethod
    def validate_multimodal_request(request_data: Dict[str, Any]) -> bool:
        """验证多模态请求的有效性"""
        try:
            messages = request_data.get('messages', [])
            
            for message in messages:
                content = message.get('content')
                
                # 如果content是列表，检查多模态内容
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            item_type = item.get('type')
                            
                            if item_type == 'image_url':
                                image_url = item.get('image_url', {})
                                url = image_url.get('url', '')
                                
                                if not url:
                                    logger.warning("发现空的图片URL")
                                    return False
                                
                                # 检查URL格式
                                if not (url.startswith(('data:', 'http://', 'https://')) or Path(url).exists()):
                                    logger.warning(f"无效的图片URL格式: {url}")
                                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证多模态请求失败: {e}")
            return False