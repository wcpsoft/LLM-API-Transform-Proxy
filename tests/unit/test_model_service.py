#!/usr/bin/env python3
"""
ModelService 单元测试
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from src.service.model_service import ModelService
from src.dao.model_dao import ModelDAO
from src.models.model import ModelConfig
from src.schemas import CreateModelRequest, UpdateModelRequest

class TestModelService:
    """ModelService 测试类"""
    
    @pytest.fixture
    def model_dao_mock(self):
        """ModelDAO 模拟对象"""
        return Mock(spec=ModelDAO)
    
    @pytest.fixture
    def model_service(self, model_dao_mock):
        """ModelService 实例"""
        return ModelService(model_dao=model_dao_mock)

    @pytest.fixture
    def sample_model_data(self):
        """示例模型数据"""
        return {
            "id": 1,
            "route_key": "test-gpt-4",
            "target_model": "gpt-4",
            "provider": "openai",
            "prompt_keywords": "test,gpt4",
            "description": "Test GPT-4 model",
            "enabled": True,
            "api_key": "test-key",
            "api_base": "https://api.openai.com/v1",
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}",
            "created_at": "2024-01-01 00:00:00",
            "updated_at": "2024-01-01 00:00:00"
        }

    @pytest.fixture
    def sample_models(self):
        """示例模型列表"""
        return [
            {
                "id": 1,
                "route_key": "gpt-4",
                "target_model": "gpt-4",
                "provider": "openai",
                "prompt_keywords": "gpt4,openai",
                "description": "GPT-4 model",
                "enabled": True,
                "api_key": "test-key-1",
                "api_base": "https://api.openai.com/v1",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "cost_per_token": 0.00003,
                "performance_score": 85,
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00"
            },
            {
                "id": 2,
                "route_key": "claude-opus",
                "target_model": "claude-3-opus-20240229",
                "provider": "anthropic",
                "prompt_keywords": "claude,anthropic",
                "description": "Claude 3 Opus model",
                "enabled": True,
                "api_key": "test-key-2",
                "api_base": "https://api.anthropic.com",
                "auth_header": "x-api-key",
                "auth_format": "{key}",
                "cost_per_token": 0.000075,
                "performance_score": 90,
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00"
            }
        ]
    
    class TestGetAllModels:
        """测试 get_all_models 方法"""
        
        def test_get_all_models_success(self, model_service, model_dao_mock, sample_models):
            """测试成功获取所有模型"""
            model_dao_mock.get_all_models.return_value = sample_models
            
            result = model_service.get_all_models()
            
            assert len(result) == 2
            assert result[0]["route_key"] == "gpt-4"
            assert result[1]["route_key"] == "claude-opus"
            model_dao_mock.get_all_models.assert_called_once()
        
        def test_get_all_models_empty(self, model_service, model_dao_mock):
            """测试获取空模型列表"""
            model_dao_mock.get_all_models.return_value = []
            
            result = model_service.get_all_models()
            
            assert result == []
            model_dao_mock.get_all_models.assert_called_once()
        
        def test_get_all_models_with_cache(self, model_service, model_dao_mock, sample_models):
            """测试缓存机制"""
            model_dao_mock.get_all_models.return_value = sample_models
            
            # 第一次调用
            result1 = model_service.get_all_models()
            # 第二次调用应该使用缓存
            result2 = model_service.get_all_models()
            
            assert result1 == result2
            model_dao_mock.get_all_models.assert_called_once()  # 只调用一次
    
    class TestGetModelById:
        """测试 get_model_by_id 方法"""
        
        def test_get_model_by_id_success(self, model_service, model_dao_mock, sample_model_data):
            """测试成功获取模型"""
            model = ModelConfig(**sample_model_data)
            model_dao_mock.get_model_by_id.return_value = model
            
            result = model_service.get_model_by_id(1)
            
            assert result is not None
            assert result.id == 1
            assert result.route_key == "test-gpt-4"
            model_dao_mock.get_model_by_id.assert_called_once_with(1)
        
        def test_get_model_by_id_not_found(self, model_service, model_dao_mock):
            """测试模型不存在"""
            model_dao_mock.get_model_by_id.return_value = None
            
            result = model_service.get_model_by_id(999)
            
            assert result is None
            model_dao_mock.get_model_by_id.assert_called_once_with(999)
    
    class TestCreateModel:
        """测试 create_model 方法"""
        
        def test_create_model_success(self, model_service, model_dao_mock, sample_model_data):
            """测试成功创建模型"""
            new_model = CreateModelRequest(
                name="Test GPT-4",
                route_key="test-gpt-4",
                target_model="gpt-4",
                provider="openai",
                description="Test GPT-4 model",
                enabled=True,
                api_base="https://api.openai.com/v1"
            )
            model_dao_mock.get_models_by_route_key.return_value = []
            created_model = sample_model_data.copy()
            created_model["id"] = 1
            model_dao_mock.create_model.return_value = 1
            
            result = model_service.create_model(new_model)
            
            assert result is not None
            assert result["id"] == 1
            assert result["message"] == "模型配置创建成功"
            model_dao_mock.get_models_by_route_key.assert_called_once_with("test-gpt-4")
            model_dao_mock.create_model.assert_called_once()
        
        def test_create_model_duplicate_route_key(self, model_service, model_dao_mock, sample_model_data):
            """测试重复路由键"""
            existing_model = sample_model_data
            model_dao_mock.get_models_by_route_key.return_value = [existing_model]
            
            duplicate_model = CreateModelRequest(
                name="Duplicate GPT-4",
                route_key="test-gpt-4",
                target_model="gpt-4",
                provider="openai",
                description="Duplicate GPT-4 model",
                enabled=True,
                api_base="https://api.openai.com/v1"
            )
            
            with pytest.raises(ValueError):
                model_service.create_model(duplicate_model)
            
            model_dao_mock.get_models_by_route_key.assert_called_once_with("test-gpt-4")
            model_dao_mock.create_model.assert_not_called()
        
        def test_create_model_invalid_config(self, model_service, model_dao_mock):
            """测试无效配置"""
            invalid_model = CreateModelRequest(
                name="Invalid Model",
                route_key="test-model",
                target_model="gpt-4",
                provider="invalid-provider",
                cost_per_token=-1,  # 负成本
                performance_score=150  # 超出范围
            )
            
            with pytest.raises(ValueError):
                model_service.create_model(invalid_model)
            
            model_dao_mock.create_model.assert_not_called()
    
    class TestUpdateModel:
        """测试 update_model 方法"""
        
        def test_update_model_success(self, model_service, model_dao_mock, sample_model_data):
            """测试成功更新模型"""
            model_id = 1
            update_data = UpdateModelRequest(description="Updated model description")
            
            existing_model = sample_model_data.copy()
            existing_model["id"] = model_id
            updated_model = {**existing_model, "description": "Updated description"}
            
            model_dao_mock.get_model_by_id.return_value = existing_model
            model_dao_mock.update_model.return_value = updated_model
            
            result = model_service.update_model(model_id, update_data)
            
            assert result["message"] == "模型配置更新成功"
            model_dao_mock.get_model_by_id.assert_called_once_with(model_id)
            model_dao_mock.update_model.assert_called_once_with(model_id, update_data.model_dump(exclude_unset=True))
        
        def test_update_model_not_found(self, model_service, model_dao_mock):
            """测试模型不存在"""
            model_id = 999
            update_data = {"description": "Updated description"}
            
            model_dao_mock.get_model_by_id.return_value = None
            
            with pytest.raises(ValueError, match="模型配置不存在"):
                model_service.update_model(model_id, update_data)
            
            model_dao_mock.update_model.assert_not_called()
    
    class TestDeleteModel:
        """测试 delete_model 方法"""
        
        def test_delete_model_success(self, model_service, model_dao_mock):
            """测试成功删除模型"""
            model_id = 1
            existing_model = {
                "id": model_id,
                "route_key": "gpt-4"
            }
            
            model_dao_mock.get_model_by_id.return_value = existing_model
            model_dao_mock.delete_model.return_value = True
            
            result = model_service.delete_model(model_id)
            
            assert result["message"] == "模型配置删除成功"
            model_dao_mock.get_model_by_id.assert_called_once_with(model_id)
            model_dao_mock.delete_model.assert_called_once_with(model_id)
        
        def test_delete_model_not_found(self, model_service, model_dao_mock):
            """测试删除不存在的模型"""
            model_id = 999
            
            model_dao_mock.get_model_by_id.return_value = None
            
            with pytest.raises(ValueError, match="模型配置不存在"):
                model_service.delete_model(model_id)
    
    class TestGetModelsByRouteKey:
        """测试 get_models_by_route_key 方法"""
        
        def test_get_models_by_route_key_success(self, model_service, model_dao_mock, sample_models):
            """测试成功按路由键获取模型"""
            filtered_models = [m for m in sample_models if m["route_key"] == "gpt-4"]
            model_dao_mock.get_models_by_route_key.return_value = filtered_models
            
            result = model_service.get_models_by_route_key("gpt-4")
            
            assert len(result) == 1
            assert result[0]["route_key"] == "gpt-4"
            model_dao_mock.get_models_by_route_key.assert_called_once_with("gpt-4")
    
    class TestSelectBestModel:
        """测试 select_best_model 方法"""
        
        def test_select_best_model_by_cost(self, model_service, sample_models):
            """测试按成本选择最佳模型"""
            with patch.object(model_service.model_dao, 'get_models_by_route_key') as mock_get:
                mock_get.return_value = sample_models
                
                best_model = model_service.select_best_model("test-route", criteria={"priority": "cost"})
                
                assert best_model is not None
                assert best_model["cost_per_token"] == min(m["cost_per_token"] for m in sample_models)
        
        def test_select_best_model_by_performance(self, model_service, sample_models):
            """测试按性能选择最佳模型"""
            with patch.object(model_service.model_dao, 'get_models_by_route_key') as mock_get:
                mock_get.return_value = sample_models
                
                best_model = model_service.select_best_model("test-route", criteria={"priority": "performance"})
                
                assert best_model is not None
                assert best_model["performance_score"] == max(m["performance_score"] for m in sample_models)
        
        def test_select_best_model_by_balance(self, model_service, sample_models):
            """测试平衡选择模型"""
            with patch.object(model_service.model_dao, 'get_models_by_route_key') as mock_get:
                mock_get.return_value = sample_models
                
                best_model = model_service.select_best_model("test-route", criteria={"priority": "balanced"})
                
                assert best_model is not None
        
        def test_select_best_model_empty_list(self, model_service):
            """测试空模型列表"""
            with patch.object(model_service.model_dao, 'get_models_by_route_key') as mock_get:
                mock_get.return_value = []
                
                best_model = model_service.select_best_model("test-route")
                
                assert best_model is None
    
    class TestValidateModelConfig:
        """测试 validate_model_config 方法"""
        
        def test_validate_valid_config(self, model_service):
            """测试有效配置"""
            valid_config = {
                "provider": "openai",
                "route_key": "valid-route-key",
                "target_model": "gpt-4",
                "cost_per_token": 0.00001,
                "performance_score": 85
            }
            
            result = model_service.validate_model_config(valid_config)
            
            assert result is True
            
        def test_validate_invalid_provider(self, model_service):
            """测试无效提供商"""
            invalid_config = {
                "provider": "invalid-provider",
                "route_key": "test-key",
                "target_model": "gpt-4"
            }
            
            result = model_service.validate_model_config(invalid_config)
            assert result is False
            
        def test_validate_invalid_route_key(self, model_service):
            """测试无效路由键"""
            invalid_config = {
                "provider": "openai",
                "route_key": "",  # 空路由键
                "target_model": "gpt-4"
            }
            
            result = model_service.validate_model_config(invalid_config)
            assert result is False
            
        def test_validate_invalid_cost(self, model_service):
            """测试无效成本值"""
            invalid_config = {
                "provider": "openai",
                "route_key": "test-key",
                "target_model": "gpt-4",
                "cost_per_token": -0.1  # 负数成本
            }
            
            result = model_service.validate_model_config(invalid_config)
            assert result is False
    
    class TestCacheInvalidation:
        """测试缓存失效"""
        
        def test_cache_invalidation_on_create(self, model_service, model_dao_mock):
            """测试创建模型时缓存失效"""
            # 先获取所有模型，建立缓存
            model_dao_mock.get_all_models.return_value = []
            model_service.get_all_models()
            
            # 创建新模型
            new_model = CreateModelRequest(
                name="New Model",
                route_key="new-model",
                target_model="gpt-4",
                provider="openai",
                description="New model",
                enabled=True,
                api_base="https://api.openai.com/v1"
            )
            
            created_model = {
                "id": 1,
                "route_key": "new-model",
                "target_model": "gpt-4",
                "provider": "openai",
                "cost_per_token": 0.002,
                "performance_score": 0.9,
                "enabled": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            model_dao_mock.get_models_by_route_key.return_value = []
            model_dao_mock.create_model.return_value = created_model
            
            # 创建模型应该使缓存失效
            model_service.create_model(new_model)
            
            # 验证缓存已失效，会重新查询数据库
            model_dao_mock.get_all_models.return_value = [created_model]
            result = model_service.get_all_models()
            
            assert len(result) == 1
            assert result[0]["route_key"] == "new-model"
        
        def test_cache_invalidation_on_update(self, model_service, model_dao_mock):
            """测试更新模型时缓存失效"""
            # 先获取所有模型，建立缓存
            original_model = {
                "id": 1,
                "route_key": "original-model",
                "target_model": "gpt-4",
                "provider": "openai",
                "cost_per_token": 0.002,
                "performance_score": 0.9,
                "enabled": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            model_dao_mock.get_all_models.return_value = [original_model]
            model_service.get_all_models()
            
            # 更新模型
            update_data = UpdateModelRequest(route_key="updated-model-cache-test")
            updated_model = original_model.copy()
            updated_model["route_key"] = "updated-model-cache-test"
            
            model_dao_mock.get_model_by_id.return_value = original_model
            model_dao_mock.get_models_by_route_key.return_value = []
            model_dao_mock.update_model.return_value = updated_model
            
            # 更新模型应该使缓存失效
            model_service.update_model(1, update_data)
            
            # 验证缓存已失效，会重新查询数据库
            model_dao_mock.get_all_models.return_value = [updated_model]
            result = model_service.get_all_models()
            
            assert len(result) == 1
            assert result[0]["route_key"] == "updated-model-cache-test"
        
        def test_cache_invalidation_on_delete(self, model_service, model_dao_mock):
            """测试删除模型时缓存失效"""
            # 先获取所有模型，建立缓存
            model = {
                "id": 1,
                "route_key": "test-model",
                "target_model": "gpt-4",
                "provider": "openai",
                "cost_per_token": 0.002,
                "performance_score": 0.9,
                "enabled": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            model_dao_mock.get_all_models.return_value = [model]
            model_service.get_all_models()
            
            # 删除模型
            model_dao_mock.delete_model.return_value = True
            model_service.delete_model(1)
            
            # 验证缓存已失效，会重新查询数据库
            model_dao_mock.get_all_models.return_value = []
            result = model_service.get_all_models()
            
            assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])