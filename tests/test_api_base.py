import pytest
from unittest.mock import patch, AsyncMock
from src.main import _call_model_api_nostream

@pytest.mark.asyncio
async def test_api_base_custom_endpoint():
    """测试自定义api_base端点"""
    with patch("src.main.list_model_configs") as mock_list_configs, \
         patch("src.main.list_model_configs") as mock_list_configs, \
         patch("src.main.get_provider") as mock_get_provider, \
         patch("src.main.api_key_manager") as mock_key_manager, \
         patch("src.main.get_api_key_config") as mock_get_api_config:
        
        # 模拟路由配置
        mock_get_route.return_value = {
            "claude_to_custom": {
                "provider": "openai",
                "target_model": "custom-model",
                "api_base": "https://custom-api.com/v1",
                "prompt_keywords": ["claude"]
            }
        }
        
        mock_list_configs.return_value = []
        
        # 模拟API密钥管理器
        from unittest.mock import MagicMock
        mock_key_manager.get_next_key.return_value = "test-api-key"
        mock_key_manager.record_request = MagicMock()
        
        # 模拟API配置
        mock_get_api_config.return_value = {
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}"
        }
        
        # 模拟提供商
        mock_provider = MagicMock()
        mock_provider.get_auth_header_name.return_value = "Authorization"
        mock_provider.make_request = AsyncMock(return_value={"result": "success"})
        mock_get_provider.return_value = mock_provider
        
        # 设置环境变量
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test-api-key"
            
            # 调用函数
            result = await _call_model_api_nostream("openai", "custom-model", {"messages": []})
            
            # 验证结果
            assert result["result"] == "success"
            
            # 验证提供商的make_request被调用
            mock_provider.make_request.assert_called_once()
            call_args = mock_provider.make_request.call_args
            assert call_args[1]["api_base"] == "https://custom-api.com/v1"
            assert call_args[1]["stream"] == False

@pytest.mark.asyncio
async def test_api_base_default_endpoint():
    """测试没有api_base配置时使用默认端点"""
    with patch("src.main.list_model_configs") as mock_list_configs, \
         patch("src.main.list_model_configs") as mock_list_configs, \
         patch("src.main.get_provider") as mock_get_provider, \
         patch("src.main.api_key_manager") as mock_key_manager, \
         patch("src.main.get_api_key_config") as mock_get_api_config:
        
        # 模拟配置 - 没有api_base
        mock_get_route.return_value = {
            "openai_default": {
                "provider": "openai",
                "target_model": "gpt-4",
                "prompt_keywords": ["openai"]
            }
        }
        
        mock_list_configs.return_value = []
        
        # 模拟API密钥管理器
        from unittest.mock import MagicMock
        mock_key_manager.get_next_key.return_value = "test-api-key"
        mock_key_manager.record_request = MagicMock()
        
        # 模拟API配置
        mock_get_api_config.return_value = {
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}"
        }
        
        # 模拟提供商
        mock_provider = MagicMock()
        mock_provider.get_auth_header_name.return_value = "Authorization"
        mock_provider.make_request = AsyncMock(return_value={"result": "success"})
        mock_get_provider.return_value = mock_provider
        
        # 设置环境变量
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = "test-api-key"
            
            # 调用函数
            result = await _call_model_api_nostream("openai", "gpt-4", {"messages": []})
            
            # 验证结果
            assert result["result"] == "success"
            
            # 验证提供商的make_request被调用
            mock_provider.make_request.assert_called_once()
            call_args = mock_provider.make_request.call_args
            # 验证没有自定义api_base时使用默认值
            assert "api_base" not in call_args[1] or call_args[1]["api_base"] is None
            assert call_args[1]["stream"] == False