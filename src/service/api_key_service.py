from typing import List, Optional, Dict, Any
from src.dao.api_key_dao import ApiKeyDAO
from src.utils.logging import logger
from src.schemas import CreateApiKeyRequest, UpdateKeyStatusRequest


class ApiKeyService:
    """API密钥管理服务"""
    
    @staticmethod
    def get_all_api_keys(provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有API密钥"""
        try:
            return ApiKeyDAO.get_all_api_keys(provider)
        except Exception as e:
            logger.error(f"获取API密钥列表失败: {e}")
            raise
    
    @staticmethod
    def get_api_key_by_id(key_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取API密钥"""
        try:
            return ApiKeyDAO.get_api_key_by_id(key_id)
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    @staticmethod
    def create_api_key(request: CreateApiKeyRequest) -> Dict[str, Any]:
        """创建API密钥"""
        try:
            # 验证提供商
            valid_providers = ['openai', 'anthropic', 'gemini']
            if request.provider not in valid_providers:
                raise ValueError(f"不支持的提供商: {request.provider}")
            
            # 验证API密钥格式
            if not request.api_key or len(request.api_key.strip()) < 10:
                raise ValueError("API密钥格式无效")
            
            key_data = {
                'provider': request.provider,
                'api_key': request.api_key.strip(),
                'auth_header': request.auth_header or 'Authorization',
                'auth_format': request.auth_format or 'Bearer {api_key}',
                'is_active': request.is_active
            }
            
            new_id = ApiKeyDAO.create_api_key(key_data)
            return {"id": new_id, "message": "API密钥添加成功"}
        except Exception as e:
            logger.error(f"创建API密钥失败: {e}")
            raise
    
    @staticmethod
    def update_key_status(key_id: int, request: UpdateKeyStatusRequest) -> Dict[str, str]:
        """更新API密钥状态"""
        try:
            # 检查密钥是否存在
            existing_key = ApiKeyDAO.get_api_key_by_id(key_id)
            if not existing_key:
                raise ValueError("API密钥不存在")
            
            success = ApiKeyDAO.update_api_key_status(key_id, request.is_active)
            if not success:
                raise ValueError("更新API密钥状态失败")
            
            return {"message": "API密钥状态更新成功"}
        except Exception as e:
            logger.error(f"更新API密钥状态失败: {e}")
            raise
    
    @staticmethod
    def delete_api_key(key_id: int) -> Dict[str, str]:
        """删除API密钥"""
        try:
            success = ApiKeyDAO.delete_api_key(key_id)
            if not success:
                raise ValueError("API密钥不存在")
            
            return {"message": "API密钥删除成功"}
        except Exception as e:
            logger.error(f"删除API密钥失败: {e}")
            raise
    
    @staticmethod
    def get_active_keys_by_provider(provider: str) -> List[Dict[str, Any]]:
        """获取指定提供商的活跃密钥"""
        try:
            return ApiKeyDAO.get_active_keys_by_provider(provider)
        except Exception as e:
            logger.error(f"获取活跃API密钥失败: {e}")
            raise
    
    @staticmethod
    def update_key_stats(key_id: int, success: bool = True) -> None:
        """更新API密钥统计信息"""
        try:
            ApiKeyDAO.update_key_stats(key_id, success)
        except Exception as e:
            logger.error(f"更新API密钥统计失败: {e}")
            # 统计更新失败不应该影响主流程，只记录日志
    
    @staticmethod
    def get_provider_stats() -> List[Dict[str, Any]]:
        """获取提供商统计信息"""
        try:
            return ApiKeyDAO.get_provider_stats()
        except Exception as e:
            logger.error(f"获取提供商统计失败: {e}")
            raise
    
    @staticmethod
    def get_api_key_stats() -> Dict[str, Any]:
        """获取API密钥统计信息"""
        try:
            all_keys = ApiKeyDAO.get_all_api_keys()
            provider_stats = ApiKeyDAO.get_provider_stats()
            
            total_keys = len(all_keys)
            active_keys = len([key for key in all_keys if key.get('is_active')])
            
            return {
                'total_keys': total_keys,
                'active_keys': active_keys,
                'inactive_keys': total_keys - active_keys,
                'provider_stats': provider_stats
            }
        except Exception as e:
            logger.error(f"获取API密钥统计失败: {e}")
            raise
    
    @staticmethod
    def validate_api_key_format(provider: str, api_key: str) -> bool:
        """验证API密钥格式"""
        try:
            if not api_key or not api_key.strip():
                return False
            
            api_key = api_key.strip()
            
            # 基本长度检查
            if len(api_key) < 10:
                return False
            
            # 提供商特定的格式检查
            if provider == 'openai':
                return api_key.startswith('sk-') and len(api_key) > 20
            elif provider == 'anthropic':
                return api_key.startswith('sk-ant-') and len(api_key) > 30
            elif provider == 'gemini':
                return len(api_key) > 20  # Google API keys are typically longer
            
            return True
        except Exception as e:
            logger.error(f"验证API密钥格式失败: {e}")
            return False