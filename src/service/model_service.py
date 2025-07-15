from typing import List, Optional, Dict, Any
from src.dao.model_dao import ModelDAO
from src.utils.logging import logger
from src.schemas import CreateModelRequest, UpdateModelRequest


class ModelService:
    """模型管理服务"""
    
    @staticmethod
    def get_all_models() -> List[Dict[str, Any]]:
        """获取所有模型配置"""
        try:
            return ModelDAO.get_all_models()
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            raise
    
    @staticmethod
    def get_model_by_id(model_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取模型配置"""
        try:
            return ModelDAO.get_model_by_id(model_id)
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            raise
    
    @staticmethod
    def create_model(request: CreateModelRequest) -> Dict[str, Any]:
        """创建模型配置"""
        try:
            # 验证路由键唯一性
            existing_models = ModelDAO.get_models_by_route_key(request.route_key)
            if existing_models:
                raise ValueError(f"路由键 '{request.route_key}' 已存在")
            
            model_data = {
                'route_key': request.route_key,
                'target_model': request.target_model,
                'provider': request.provider,
                'prompt_keywords': request.prompt_keywords,
                'description': request.description,
                'enabled': request.enabled,
                'api_key': request.api_key,
                'api_base': request.api_base,
                'auth_header': request.auth_header,
                'auth_format': request.auth_format
            }
            
            new_id = ModelDAO.create_model(model_data)
            return {"id": new_id, "message": "模型配置创建成功"}
        except Exception as e:
            logger.error(f"创建模型配置失败: {e}")
            raise
    
    @staticmethod
    def update_model(model_id: int, request: UpdateModelRequest) -> Dict[str, str]:
        """更新模型配置"""
        try:
            # 检查模型是否存在
            existing_model = ModelDAO.get_model_by_id(model_id)
            if not existing_model:
                raise ValueError("模型配置不存在")
            
            # 如果更新路由键，检查唯一性
            if request.route_key != existing_model['route_key']:
                existing_models = ModelDAO.get_models_by_route_key(request.route_key)
                if existing_models:
                    raise ValueError(f"路由键 '{request.route_key}' 已存在")
            
            model_data = {
                'route_key': request.route_key,
                'target_model': request.target_model,
                'provider': request.provider,
                'prompt_keywords': request.prompt_keywords,
                'description': request.description,
                'enabled': request.enabled,
                'api_key': request.api_key,
                'api_base': request.api_base,
                'auth_header': request.auth_header,
                'auth_format': request.auth_format
            }
            
            success = ModelDAO.update_model(model_id, model_data)
            if not success:
                raise ValueError("更新模型配置失败")
            
            return {"message": "模型配置更新成功"}
        except Exception as e:
            logger.error(f"更新模型配置失败: {e}")
            raise
    
    @staticmethod
    def delete_model(model_id: int) -> Dict[str, str]:
        """删除模型配置"""
        try:
            success = ModelDAO.delete_model(model_id)
            if not success:
                raise ValueError("模型配置不存在")
            
            return {"message": "模型配置删除成功"}
        except Exception as e:
            logger.error(f"删除模型配置失败: {e}")
            raise
    
    @staticmethod
    def get_models_by_route_key(route_key: str) -> List[Dict[str, Any]]:
        """根据路由键获取模型配置"""
        try:
            return ModelDAO.get_models_by_route_key(route_key)
        except Exception as e:
            logger.error(f"获取路由模型配置失败: {e}")
            raise
    
    @staticmethod
    def get_all_models_and_providers() -> Dict[str, List[str]]:
        """获取所有模型和提供商信息"""
        try:
            models = ModelDAO.get_all_models()
            result = {}
            
            for model in models:
                provider = model['provider']
                target_model = model['target_model']
                
                if provider not in result:
                    result[provider] = []
                
                if target_model not in result[provider]:
                    result[provider].append(target_model)
            
            return result
        except Exception as e:
            logger.error(f"获取模型和提供商信息失败: {e}")
            raise
    
    @staticmethod
    def validate_model_config(model_data: Dict[str, Any]) -> bool:
        """验证模型配置"""
        required_fields = ['route_key', 'target_model', 'provider']
        
        for field in required_fields:
            if not model_data.get(field):
                raise ValueError(f"缺少必需字段: {field}")
        
        # 验证提供商
        valid_providers = ['openai', 'anthropic', 'gemini']
        if model_data['provider'] not in valid_providers:
            raise ValueError(f"不支持的提供商: {model_data['provider']}")
        
        return True