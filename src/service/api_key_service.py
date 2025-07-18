from typing import List, Optional, Dict, Any
from src.dao.api_key_dao import ApiKeyDAO
from src.utils.logging import logger
from src.schemas import CreateApiKeyRequest, UpdateKeyStatusRequest


class ApiKeyService:
    """API密钥管理服务"""
    
    def __init__(self):
        self._dao = ApiKeyDAO()
    
    def get_all_api_keys(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有API密钥"""
        try:
            return self._dao.get_all_api_keys(provider)
        except Exception as e:
            logger.error(f"获取API密钥列表失败: {e}")
            raise
    
    def get_api_key_by_id(self, key_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取API密钥"""
        try:
            return self._dao.get_api_key_by_id(key_id)
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    def create_api_key(self, request: CreateApiKeyRequest) -> Dict[str, Any]:
        """创建API密钥"""
        try:
            # 验证提供商
            valid_providers = ['openai', 'anthropic', 'gemini', 'deepseek']
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
                'is_active': request.enabled
            }
            
            new_id = self._dao.create_api_key(key_data)
            return {"id": new_id, "message": "API密钥添加成功"}
        except Exception as e:
            logger.error(f"创建API密钥失败: {e}")
            raise
    
    def update_key_status(self, key_id: int, request: UpdateKeyStatusRequest) -> Dict[str, str]:
        """更新API密钥状态"""
        try:
            # 检查密钥是否存在
            existing_key = self._dao.get_api_key_by_id(key_id)
            if not existing_key:
                raise ValueError("API密钥不存在")
            
            success = ApiKeyDAO.update_api_key_status(key_id, request.enabled)
            if not success:
                raise ValueError("更新API密钥状态失败")
            
            return {"message": "API密钥状态更新成功"}
        except Exception as e:
            logger.error(f"更新API密钥状态失败: {e}")
            raise
    
    def delete_api_key(self, key_id: int) -> Dict[str, str]:
        """删除API密钥"""
        try:
            success = ApiKeyDAO.delete_api_key(key_id)
            if not success:
                raise ValueError("API密钥不存在")
            
            return {"message": "API密钥删除成功"}
        except Exception as e:
            logger.error(f"删除API密钥失败: {e}")
            raise
    
    def get_active_keys_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """获取指定提供商的活跃密钥"""
        try:
            return ApiKeyDAO.get_active_keys_by_provider(provider)
        except Exception as e:
            logger.error(f"获取活跃API密钥失败: {e}")
            raise
    
    def update_key_stats(self, key_id: int, success: bool = True, usage_data: Optional[Dict[str, Any]] = None) -> None:
        """更新API密钥统计信息
        
        Args:
            key_id: API密钥ID
            success: 请求是否成功
            usage_data: 使用数据，包含tokens、延迟等信息
        """
        try:
            ApiKeyDAO.update_key_stats(key_id, success, usage_data)
        except Exception as e:
            logger.error(f"更新API密钥统计失败: {e}")
            # 统计更新失败不应该影响主流程，只记录日志
    
    def get_provider_stats(self) -> List[Dict[str, Any]]:
        """获取提供商统计信息"""
        try:
            return ApiKeyDAO.get_provider_stats()
        except Exception as e:
            logger.error(f"获取提供商统计失败: {e}")
            raise
    
    def get_api_key_stats(self) -> Dict[str, Any]:
        """获取API密钥统计信息"""
        try:
            all_keys = self._dao.get_all_api_keys()
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
            
    def get_detailed_key_metrics(self, key_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取详细的API密钥指标
        
        Args:
            key_id: 可选的API密钥ID，如果提供则只返回该密钥的指标
            
        Returns:
            API密钥指标列表
        """
        try:
            return ApiKeyDAO.get_detailed_key_metrics(key_id)
        except Exception as e:
            logger.error(f"获取API密钥详细指标失败: {e}")
            raise
            
    def get_keys_needing_rotation(self) -> List[Dict[str, Any]]:
        """获取需要轮换的API密钥
        
        Returns:
            需要轮换的API密钥列表
        """
        try:
            return ApiKeyDAO.get_keys_needing_rotation()
        except Exception as e:
            logger.error(f"获取需要轮换的API密钥失败: {e}")
            return []
            
    def rotate_api_key(self, old_key_id: int, new_key_id: int) -> Dict[str, str]:
        """轮换API密钥
        
        Args:
            old_key_id: 旧API密钥ID
            new_key_id: 新API密钥ID
            
        Returns:
            操作结果
        """
        try:
            # 验证两个密钥是否存在
            old_key = self._dao.get_api_key_by_id(old_key_id)
            new_key = self._dao.get_api_key_by_id(new_key_id)
            
            if not old_key:
                raise ValueError(f"旧API密钥不存在: {old_key_id}")
                
            if not new_key:
                raise ValueError(f"新API密钥不存在: {new_key_id}")
                
            # 验证两个密钥是否属于同一提供商
            if old_key['provider'] != new_key['provider']:
                raise ValueError(f"API密钥必须属于同一提供商: {old_key['provider']} != {new_key['provider']}")
                
            # 验证新密钥是否已激活
            if not new_key['is_active']:
                raise ValueError(f"新API密钥必须处于激活状态")
                
            # 执行轮换
            success = ApiKeyDAO.rotate_api_key(old_key_id, new_key_id)
            
            if not success:
                raise ValueError("API密钥轮换失败")
                
            return {"message": "API密钥轮换成功"}
        except Exception as e:
            logger.error(f"轮换API密钥失败: {e}")
            raise
            
    def auto_rotate_keys(self) -> Dict[str, Any]:
        """自动轮换需要轮换的API密钥
        
        Returns:
            轮换结果统计
        """
        try:
            # 获取需要轮换的密钥
            keys_to_rotate = self.get_keys_needing_rotation()
            
            if not keys_to_rotate:
                return {"message": "没有需要轮换的API密钥", "rotated_count": 0}
                
            rotated_count = 0
            failed_count = 0
            results = []
            
            # 按提供商分组
            keys_by_provider = {}
            for key in keys_to_rotate:
                provider = key['provider']
                if provider not in keys_by_provider:
                    keys_by_provider[provider] = []
                keys_by_provider[provider].append(key)
                
            # 对每个提供商，查找可用的替代密钥
            for provider, keys in keys_by_provider.items():
                # 获取该提供商的所有活跃密钥
                active_keys = ApiKeyDAO.get_active_keys_by_provider(provider)
                
                # 过滤掉需要轮换的密钥
                rotation_key_ids = [k['id'] for k in keys]
                replacement_keys = [k for k in active_keys if k['id'] not in rotation_key_ids]
                
                if not replacement_keys:
                    logger.warning(f"提供商 {provider} 没有可用的替代密钥")
                    for key in keys:
                        results.append({
                            "old_key_id": key['id'],
                            "provider": provider,
                            "status": "failed",
                            "reason": "没有可用的替代密钥"
                        })
                    failed_count += len(keys)
                    continue
                    
                # 为每个需要轮换的密钥分配一个替代密钥
                for i, key in enumerate(keys):
                    # 循环使用替代密钥
                    replacement_key = replacement_keys[i % len(replacement_keys)]
                    
                    try:
                        # 执行轮换
                        success = ApiKeyDAO.rotate_api_key(key['id'], replacement_key['id'])
                        
                        if success:
                            results.append({
                                "old_key_id": key['id'],
                                "new_key_id": replacement_key['id'],
                                "provider": provider,
                                "status": "success"
                            })
                            rotated_count += 1
                        else:
                            results.append({
                                "old_key_id": key['id'],
                                "new_key_id": replacement_key['id'],
                                "provider": provider,
                                "status": "failed",
                                "reason": "轮换操作失败"
                            })
                            failed_count += 1
                    except Exception as e:
                        results.append({
                            "old_key_id": key['id'],
                            "new_key_id": replacement_key['id'],
                            "provider": provider,
                            "status": "failed",
                            "reason": str(e)
                        })
                        failed_count += 1
                        logger.error(f"轮换API密钥失败: {e}")
            
            return {
                "message": f"API密钥轮换完成: {rotated_count} 成功, {failed_count} 失败",
                "rotated_count": rotated_count,
                "failed_count": failed_count,
                "results": results
            }
        except Exception as e:
            logger.error(f"自动轮换API密钥失败: {e}")
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
            elif provider == 'deepseek':
                return api_key.startswith('sk-') and len(api_key) > 20  # DeepSeek uses similar format to OpenAI
            
            return True
        except Exception as e:
            logger.error(f"验证API密钥格式失败: {e}")
            return False