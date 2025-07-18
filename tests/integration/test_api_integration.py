#!/usr/bin/env python3
"""
API集成测试 - 测试完整的请求流程
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import json
from typing import Dict, Any, List
from aiohttp import ClientSession

from src.main import app
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.log_service import LogService
from src.core.http_client_pool import HTTPClientPool
from src.core.errors.retry_handler import RetryHandler
from src.core.errors.graceful_degradation import ServiceHealthMonitor


class TestAPIIntegration:
    """API集成测试类"""
    
    @pytest.fixture
    def app(self):
        """FastAPI应用实例"""
        return app
    
    @pytest_asyncio.fixture
    async def client(self, app):
        """异步测试客户端"""
        from httpx import AsyncClient
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def mock_services(self):
        """模拟服务"""
        return {
            "model_service": Mock(spec=ModelService),
            "api_key_service": Mock(spec=ApiKeyService),
            "log_service": Mock(spec=LogService),
            "http_client_pool": Mock(spec=HTTPClientPool),
            "retry_handler": Mock(spec=RetryHandler),
            "health_monitor": Mock(spec=ServiceHealthMonitor)
        }
    
    @pytest.fixture
    def test_models(self):
        """测试模型数据"""
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
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00"
            }
        ]
    
    @pytest.fixture
    def test_api_keys(self):
        """测试API密钥数据"""
        return [
            {
                "id": 1,
                "provider": "openai",
                "api_key": "sk-test-openai-key",
                "auth_header": "Authorization",
                "auth_format": "Bearer {api_key}",
                "is_active": True,
                "requests_count": 100,
                "success_count": 95,
                "error_count": 5,
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00"
            },
            {
                "id": 2,
                "provider": "anthropic",
                "api_key": "sk-ant-test-key",
                "auth_header": "x-api-key",
                "auth_format": "{api_key}",
                "is_active": True,
                "requests_count": 50,
                "success_count": 48,
                "error_count": 2,
                "created_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-01 00:00:00"
            }
        ]
    
    class TestChatCompletion:
        """测试聊天补全API"""
        
        @pytest.mark.asyncio
        async def test_chat_completion_success(self, client, mock_services, test_models):
            """测试成功的聊天补全请求"""
            # 设置模拟响应
            mock_response = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677858242,
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20
                }
            }
            
            request_data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "model": "gpt-4",
                "max_tokens": 100
            }
            
            with patch('src.routers.chat.router.model_service') as mock_model_service, \
                 patch('src.routers.chat.router.api_key_service') as mock_api_key_service, \
                 patch('aiohttp.ClientSession.post') as mock_post:
                
                mock_model_service.get_models_by_route_key.return_value = [test_models[0]]
                mock_api_key_service.get_available_key.return_value = {
                    "provider": "openai",
                    "key": "sk-test-key"
                }
                mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
                mock_post.return_value.__aenter__.return_value.status = 200
                
                response = await client.post("/v1/chat/completions", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["choices"][0]["message"]["content"] == "Hello! How can I help you today?"
        
        @pytest.mark.asyncio
        async def test_chat_completion_model_not_found(self, client):
            """测试模型不存在"""
            request_data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "model": "non-existent-model",
                "max_tokens": 100
            }
            
            with patch('src.routers.chat.router.model_service') as mock_model_service:
                mock_model_service.get_models_by_route_key.return_value = []
                
                response = await client.post("/v1/chat/completions", json=request_data)
                
                assert response.status_code == 404
                assert "Model not found" in response.json()["detail"]
        
        @pytest.mark.asyncio
        async def test_chat_completion_no_api_key(self, client, test_models):
            """测试没有可用API密钥"""
            request_data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "model": "gpt-4",
                "max_tokens": 100
            }
            
            with patch('src.routers.chat.router.model_service') as mock_model_service, \
                 patch('src.routers.chat.router.api_key_service') as mock_api_key_service:
                
                mock_model_service.get_models_by_route_key.return_value = [test_models[0]]
                mock_api_key_service.get_available_key.return_value = None
                
                response = await client.post("/v1/chat/completions", json=request_data)
                
                assert response.status_code == 429
                assert "No available API key" in response.json()["detail"]
        
        @pytest.mark.asyncio
        async def test_chat_completion_provider_error(self, client, test_models):
            """测试提供商错误处理"""
            request_data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "model": "gpt-4",
                "max_tokens": 100
            }
            
            with patch('src.routers.chat.router.model_service') as mock_model_service, \
                 patch('src.routers.chat.router.api_key_service') as mock_api_key_service, \
                 patch('aiohttp.ClientSession.post') as mock_post:
                
                mock_model_service.get_models_by_route_key.return_value = [test_models[0]]
                mock_api_key_service.get_available_key.return_value = {
                    "provider": "openai",
                    "key": "sk-test-key"
                }
                mock_post.return_value.__aenter__.return_value.status = 500
                mock_post.return_value.__aenter__.return_value.text = AsyncMock(return_value="Internal Server Error")
                
                response = await client.post("/v1/chat/completions", json=request_data)
                
                assert response.status_code == 502
                assert "Provider error" in response.json()["detail"]
    
    class TestModelManagement:
        """测试模型管理API"""
        
        @pytest.mark.asyncio
        async def test_get_all_models(self, client, test_models):
            """测试获取所有模型"""
            with patch('src.routers.models.router.model_service') as mock_model_service:
                mock_model_service.get_all_models.return_value = test_models
                
                response = await client.get("/v1/models")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["name"] == "GPT-4"
                assert data[1]["name"] == "Claude 3 Opus"
        
        @pytest.mark.asyncio
        async def test_create_model(self, client):
            """测试创建模型"""
            model_data = {
                "provider": "openai",
                "name": "Test Model",
                "route_key": "test-model",
                "config": {
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "model": "gpt-3.5-turbo"
                },
                "cost_per_token": 0.000001,
                "performance_score": 80
            }
            
            with patch('src.routers.models.router.model_service') as mock_model_service:
                mock_model_service.create_model.return_value = {
                    "id": "new-model-id",
                    **model_data
                }
                
                response = await client.post("/v1/models", json=model_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["id"] == "new-model-id"
                assert data["name"] == "Test Model"
        
        @pytest.mark.asyncio
        async def test_update_model(self, client):
            """测试更新模型"""
            update_data = {
                "name": "Updated Model Name",
                "cost_per_token": 0.000002
            }
            
            with patch('src.routers.models.router.model_service') as mock_model_service:
                mock_model_service.update_model.return_value = {
                    "id": "test-model-1",
                    **update_data
                }
                
                response = await client.put("/v1/models/test-model-1", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "Updated Model Name"
        
        @pytest.mark.asyncio
        async def test_delete_model(self, client):
            """测试删除模型"""
            with patch('src.routers.models.router.model_service') as mock_model_service:
                mock_model_service.delete_model.return_value = True
                
                response = await client.delete("/v1/models/test-model-1")
                
                assert response.status_code == 204
    
    class TestAPIKeyManagement:
        """测试API密钥管理API"""
        
        @pytest.mark.asyncio
        async def test_get_api_keys(self, client, test_api_keys):
            """测试获取所有API密钥"""
            with patch('src.routers.keys.router.api_key_service') as mock_api_key_service:
                mock_api_key_service.get_all_api_keys.return_value = test_api_keys
                
                response = await client.get("/v1/keys")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
        
        @pytest.mark.asyncio
        async def test_create_api_key(self, client):
            """测试创建API密钥"""
            key_data = {
                "provider": "openai",
                "key": "sk-new-test-key",
                "usage_limit": 5000
            }
            
            with patch('src.routers.keys.router.api_key_service') as mock_api_key_service:
                mock_api_key_service.create_api_key.return_value = {
                    "id": "new-key-id",
                    **key_data,
                    "current_usage": 0,
                    "is_active": True
                }
                
                response = await client.post("/v1/keys", json=key_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["id"] == "new-key-id"
    
    class TestErrorHandling:
        """测试错误处理"""
        
        @pytest.mark.asyncio
        async def test_rate_limiting(self, client):
            """测试速率限制"""
            request_data = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4"
            }
            
            # 模拟大量请求触发速率限制
            with patch('src.middleware.rate_limit.RateLimitMiddleware.check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = False
                
                response = await client.post("/v1/chat/completions", json=request_data)
                
                assert response.status_code == 429
                assert "Rate limit exceeded" in response.json()["detail"]
        
        @pytest.mark.asyncio
        async def test_authentication_error(self, client):
            """测试认证错误"""
            request_data = {
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4"
            }
            
            # 发送没有认证头的请求
            response = await client.post("/v1/chat/completions", json=request_data)
            
            # 应该返回401或类似错误
            assert response.status_code in [401, 403]
    
    class TestHealthCheck:
        """测试健康检查"""
        
        @pytest.mark.asyncio
        async def test_health_check_success(self, client):
            """测试健康检查成功"""
            with patch('src.routers.health.router.health_monitor') as mock_health_monitor:
                mock_health_monitor.check_all_services.return_value = {
                    "status": "healthy",
                    "services": {
                        "database": "healthy",
                        "cache": "healthy",
                        "providers": "healthy"
                    }
                }
                
                response = await client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
        
        @pytest.mark.asyncio
        async def test_health_check_unhealthy(self, client):
            """测试健康检查失败"""
            with patch('src.routers.health.router.health_monitor') as mock_health_monitor:
                mock_health_monitor.check_all_services.return_value = {
                    "status": "unhealthy",
                    "services": {
                        "database": "healthy",
                        "cache": "unhealthy",
                        "providers": "healthy"
                    }
                }
                
                response = await client.get("/health")
                
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"


class TestConcurrentRequests:
    """测试并发请求处理"""
    
    @pytest.mark.asyncio
    async def test_concurrent_chat_requests(self, client, test_models):
        """测试并发聊天请求"""
        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "gpt-4",
            "max_tokens": 100
        }
        
        mock_response = {
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 20}
        }
        
        with patch('src.routers.chat.router.model_service') as mock_model_service, \
             patch('src.routers.chat.router.api_key_service') as mock_api_key_service, \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            mock_model_service.get_models_by_route_key.return_value = [test_models[0]]
            mock_api_key_service.get_available_key.return_value = {
                "provider": "openai",
                "key": "sk-test-key"
            }
            mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
            mock_post.return_value.__aenter__.return_value.status = 200
            
            # 并发发送10个请求
            tasks = []
            for i in range(10):
                task = client.post("/v1/chat/completions", json=request_data)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            # 所有请求都应该成功
            for response in responses:
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# 测试配置
TEST_CONFIG = {
    "database": {
        "url": "sqlite:///./test.db"
    },
    "cache": {
        "type": "memory",
        "ttl": 300
    },
    "rate_limit": {
        "requests_per_minute": 60,
        "burst_limit": 10
    },
    "providers": {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "timeout": 30
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "timeout": 30
        }
    }
}


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return TEST_CONFIG


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestPerformance:
    """性能测试"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_response_time_under_load(self, client, test_models):
        """测试高负载下的响应时间"""
        import time
        
        request_data = {
            "messages": [{"role": "user", "content": "Performance test"}],
            "model": "gpt-4",
            "max_tokens": 50
        }
        
        mock_response = {
            "id": "chatcmpl-perf",
            "choices": [{"message": {"content": "Performance response"}}],
            "usage": {"total_tokens": 25}
        }
        
        with patch('src.routers.chat.router.model_service') as mock_model_service, \
             patch('src.routers.chat.router.api_key_service') as mock_api_key_service, \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            mock_model_service.get_models_by_route_key.return_value = [test_models[0]]
            mock_api_key_service.get_available_key.return_value = {
                "provider": "openai",
                "key": "sk-test-key"
            }
            mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
            mock_post.return_value.__aenter__.return_value.status = 200
            
            start_time = time.time()
            
            # 发送50个并发请求
            tasks = [client.post("/v1/chat/completions", json=request_data) for _ in range(50)]
            responses = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 所有请求应在5秒内完成
            assert total_time < 5.0
            assert all(r.status_code == 200 for r in responses)
            
            # 平均响应时间应小于100ms
            avg_response_time = total_time / 50
            assert avg_response_time < 0.1