from typing import List, Optional, Dict, Any
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import asyncio
from datetime import datetime, timedelta
from src.dao.model_dao import ModelDAO
from src.utils.logging import logger
from src.schemas import CreateModelRequest, UpdateModelRequest
from src.service.interfaces import IModelService


class ModelService(IModelService):
    """模型管理服务 - 支持缓存和智能模型选择"""
    
    def __init__(self, model_dao: ModelDAO = None, cache_ttl: int = 300):
        """Initialize ModelService with dependency injection and caching."""
        self.model_dao = model_dao or ModelDAO()
        self._cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}
        self._lock = asyncio.Lock()
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache or key not in self._cache_timestamps:
            return False
        return datetime.now() - self._cache_timestamps[key] < timedelta(seconds=self._cache_ttl)
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any) -> None:
        """设置缓存数据"""
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
    
    def _invalidate_cache(self, pattern: str = None) -> None:
        """使缓存失效"""
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """获取所有模型配置（带缓存）"""
        cache_key = "all_models"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
            
        try:
            result = self.model_dao.get_all_models()
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            raise
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取模型配置（带缓存）"""
        cache_key = f"model_{model_id}"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
            
        try:
            result = self.model_dao.get_model_by_id(model_id)
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取模型失败: {e}")
            raise
    
    def select_best_model(self, route_key: str, criteria: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """智能选择最佳模型
        
        Args:
            route_key: 路由键
            criteria: 选择标准，如优先级、成本、性能等
            
        Returns:
            最佳模型配置或None
        """
        try:
            models = self.get_models_by_route_key(route_key)
            if not models:
                return None
            
            # 默认选择标准
            if not criteria:
                criteria = {"priority": "performance", "max_cost": None}
            
            # 过滤可用模型
            available_models = [
                model for model in models
                if model.get("enabled", True) and 
                (not criteria.get("max_cost") or model.get("cost_per_token", 0) <= criteria["max_cost"])
            ]
            
            if not available_models:
                return None
            
            # 根据优先级排序
            priority = criteria.get("priority", "performance")
            if priority == "cost":
                # 按成本升序排序
                available_models.sort(key=lambda x: x.get("cost_per_token", float("inf")))
            elif priority == "performance":
                # 按性能评分降序排序
                available_models.sort(key=lambda x: x.get("performance_score", 0), reverse=True)
            elif priority == "balanced":
                # 平衡成本和性能
                available_models.sort(key=lambda x: (
                    x.get("cost_per_token", float("inf")),
                    -x.get("performance_score", 0)
                ))
            
            return available_models[0] if available_models else None
            
        except Exception as e:
            logger.error(f"选择最佳模型失败: {e}")
            return None

    def create_model(self, request: CreateModelRequest) -> Dict[str, Any]:
        """创建模型配置"""
        try:
            # 验证模型配置
            if not self.validate_model_config(request.model_dump()):
                raise ValueError("模型配置验证失败")
            
            # 验证路由键唯一性
            existing_models = self.model_dao.get_models_by_route_key(request.route_key)
            if existing_models:
                raise ValueError(f"路由键 '{request.route_key}' 已存在")
            
            model_data = {
                'route_key': request.route_key,
                'target_model': request.target_model,
                'provider': request.provider,
                'name': request.name,
                'description': request.description,
                'enabled': request.enabled,
                'api_base': request.api_base
            }
            
            new_id = self.model_dao.create_model(model_data)
            
            # 使相关缓存失效
            self._invalidate_cache("all_models")
            self._invalidate_cache(f"route_key_{request.route_key}")
            
            return {"id": new_id, "message": "模型配置创建成功"}
        except Exception as e:
            logger.error(f"创建模型配置失败: {e}")
            raise
    
    def update_model(self, model_id: int, request: UpdateModelRequest) -> Dict[str, str]:
        """更新模型配置"""
        try:
            # 检查模型是否存在
            existing_model = self.model_dao.get_model_by_id(model_id)
            if not existing_model:
                raise ValueError("模型配置不存在")
            
            # 验证更新后的配置
            updated_data = {**existing_model, **request.model_dump(exclude_unset=True)}
            if not self.validate_model_config(updated_data):
                raise ValueError("更新后的模型配置验证失败")
            
            # 如果更新路由键，检查唯一性
            old_route_key = existing_model.get('route_key')
            new_route_key = request.route_key
            
            if new_route_key and new_route_key != old_route_key:
                existing_by_route = self.model_dao.get_models_by_route_key(new_route_key)
                if existing_by_route:
                    raise ValueError(f"路由键 '{new_route_key}' 已存在")
            
            model_data = request.model_dump(exclude_unset=True)
            success = self.model_dao.update_model(model_id, model_data)
            if not success:
                raise ValueError("更新模型配置失败")
            
            # 使相关缓存失效
            self._invalidate_cache("all_models")
            self._invalidate_cache(f"model_{model_id}")
            self._invalidate_cache(f"route_key_{old_route_key}")
            if new_route_key and new_route_key != old_route_key:
                self._invalidate_cache(f"route_key_{new_route_key}")
            
            return {"message": "模型配置更新成功"}
        except Exception as e:
            logger.error(f"更新模型配置失败: {e}")
            raise
    
    def delete_model(self, model_id: int) -> Dict[str, str]:
        """删除模型配置"""
        try:
            # 获取模型信息用于缓存清理
            model = self.model_dao.get_model_by_id(model_id)
            if not model:
                raise ValueError("模型配置不存在")
            
            route_key = model.get('route_key')
            
            success = self.model_dao.delete_model(model_id)
            if not success:
                raise ValueError("删除模型配置失败")
            
            # 使相关缓存失效
            self._invalidate_cache("all_models")
            self._invalidate_cache(f"model_{model_id}")
            self._invalidate_cache(f"route_key_{route_key}")
            
            return {"message": "模型配置删除成功"}
        except Exception as e:
            logger.error(f"删除模型配置失败: {e}")
            raise
    
    def get_models_by_route_key(self, route_key: str) -> List[Dict[str, Any]]:
        """根据路由键获取模型配置（带缓存）"""
        cache_key = f"route_key_{route_key}"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
            
        try:
            result = self.model_dao.get_models_by_route_key(route_key)
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取路由模型配置失败: {e}")
            raise
    
    def get_all_models_and_providers(self) -> Dict[str, List[str]]:
        """获取所有模型和提供商信息（带缓存）"""
        cache_key = "all_models_and_providers"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result is not None:
            return cached_result
            
        try:
            models = self.model_dao.get_all_models()
            result = {}
            
            for model in models:
                provider = model['provider']
                target_model = model['target_model']
                
                if provider not in result:
                    result[provider] = []
                
                if target_model not in result[provider]:
                    result[provider].append(target_model)
            
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"获取模型和提供商信息失败: {e}")
            raise
    
    def validate_model_config(self, model_data: Dict[str, Any]) -> bool:
        """验证模型配置"""
        required_fields = ["route_key", "target_model", "provider"]
        
        # 检查必填字段
        if not all(field in model_data and model_data[field] for field in required_fields):
            return False
        
        # 验证路由键格式
        route_key = model_data.get("route_key", "")
        if not route_key or len(route_key) < 3 or len(route_key) > 50:
            return False
        
        # 验证提供者
        valid_providers = ["openai", "anthropic", "google", "azure", "local"]
        provider = model_data.get("provider", "").lower()
        if provider not in valid_providers:
            return False
        
        # 验证目标模型名称
        target_model = model_data.get("target_model", "")
        if not target_model or len(target_model) > 100:
            return False
        
        # 验证成本参数
        cost_per_token = model_data.get("cost_per_token", 0)
        if not isinstance(cost_per_token, (int, float)) or cost_per_token < 0:
            return False
        
        # 验证性能评分
        performance_score = model_data.get("performance_score", 0)
        if not isinstance(performance_score, (int, float)) or performance_score < 0:
            return False
        
        return True