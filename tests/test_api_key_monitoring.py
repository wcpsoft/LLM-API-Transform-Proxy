"""
Tests for API key usage monitoring enhancements
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from src.dao.api_key_dao import ApiKeyDAO
from src.service.api_key_service import ApiKeyService
from src.core.api_key.selector import ApiKey, ApiKeySelector, RequestContext


class TestApiKeyMonitoring:
    """Test API key usage monitoring functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = ApiKeyService()
        self.selector = ApiKeySelector()
        self.test_key = ApiKey(
            id="1",
            provider="openai",
            key="sk-test-key-1234567890abcdef",
            requests_count=100,
            success_count=95,
            error_count=5
        )
    
    @patch.object(ApiKeyDAO, 'update_key_stats')
    def test_update_key_stats_with_usage_data(self, mock_update):
        """Test updating key stats with usage data"""
        # Create usage data
        usage_data = {
            'total_tokens': 1000,
            'input_tokens': 200,
            'output_tokens': 800,
            'latency': 0.5,
            'cost': 0.02,
            'request_start_time': time.time() - 0.5
        }
        
        # Update stats
        self.service.update_key_stats(1, True, usage_data)
        
        # Verify DAO was called with correct parameters
        mock_update.assert_called_once_with(1, True, usage_data)
    
    @patch.object(ApiKeyDAO, 'get_detailed_key_metrics')
    def test_get_detailed_key_metrics(self, mock_get_metrics):
        """Test getting detailed key metrics"""
        # Setup mock return value
        mock_metrics = [{
            'id': 1,
            'provider': 'openai',
            'is_active': True,
            'requests_count': 100,
            'success_count': 95,
            'error_count': 5,
            'success_rate': 95.0,
            'total_tokens': 10000,
            'input_tokens': 2000,
            'output_tokens': 8000,
            'avg_latency': 0.5,
            'cost': 0.2,
            'avg_tokens_per_request': 100.0,
            'avg_cost_per_request': 0.002
        }]
        mock_get_metrics.return_value = mock_metrics
        
        # Get metrics
        metrics = self.service.get_detailed_key_metrics()
        
        # Verify result
        assert metrics == mock_metrics
        mock_get_metrics.assert_called_once_with(None)
        
        # Test with specific key ID
        self.service.get_detailed_key_metrics(1)
        mock_get_metrics.assert_called_with(1)
    
    @patch.object(ApiKeyDAO, 'get_keys_needing_rotation')
    def test_get_keys_needing_rotation(self, mock_get_keys):
        """Test getting keys that need rotation"""
        # Setup mock return value
        mock_keys = [{
            'id': 1,
            'provider': 'openai',
            'is_active': True,
            'requests_count': 100,
            'success_count': 70,
            'error_count': 30,
            'consecutive_errors': 4
        }]
        mock_get_keys.return_value = mock_keys
        
        # Get keys needing rotation
        keys = self.service.get_keys_needing_rotation()
        
        # Verify result
        assert keys == mock_keys
        mock_get_keys.assert_called_once()
    
    @patch.object(ApiKeyDAO, 'rotate_api_key')
    @patch.object(ApiKeyDAO, 'get_api_key_by_id')
    def test_rotate_api_key(self, mock_get_key, mock_rotate):
        """Test rotating an API key"""
        # Setup mocks
        mock_get_key.side_effect = [
            {'id': 1, 'provider': 'openai', 'is_active': True},  # old key
            {'id': 2, 'provider': 'openai', 'is_active': True}   # new key
        ]
        mock_rotate.return_value = True
        
        # Rotate key
        result = self.service.rotate_api_key(1, 2)
        
        # Verify result
        assert "成功" in result['message']
        mock_rotate.assert_called_once_with(1, 2)
        
        # Test with non-existent key
        mock_get_key.side_effect = [None, None]
        with pytest.raises(ValueError, match="不存在"):
            self.service.rotate_api_key(99, 100)
        
        # Test with different providers
        mock_get_key.side_effect = [
            {'id': 1, 'provider': 'openai', 'is_active': True},
            {'id': 3, 'provider': 'anthropic', 'is_active': True}
        ]
        with pytest.raises(ValueError, match="同一提供商"):
            self.service.rotate_api_key(1, 3)
        
        # Test with inactive new key
        mock_get_key.side_effect = [
            {'id': 1, 'provider': 'openai', 'is_active': True},
            {'id': 4, 'provider': 'openai', 'is_active': False}
        ]
        with pytest.raises(ValueError, match="激活状态"):
            self.service.rotate_api_key(1, 4)
    
    @patch.object(ApiKeyDAO, 'get_keys_needing_rotation')
    @patch.object(ApiKeyDAO, 'get_active_keys_by_provider')
    @patch.object(ApiKeyDAO, 'rotate_api_key')
    def test_auto_rotate_keys(self, mock_rotate, mock_get_active, mock_get_rotation):
        """Test automatic key rotation"""
        # Setup mocks for keys needing rotation
        mock_get_rotation.return_value = [
            {'id': 1, 'provider': 'openai', 'is_active': True},
            {'id': 2, 'provider': 'openai', 'is_active': True},
            {'id': 3, 'provider': 'anthropic', 'is_active': True}
        ]
        
        # Setup mocks for active keys
        mock_get_active.side_effect = [
            # For openai
            [
                {'id': 1, 'provider': 'openai', 'is_active': True},
                {'id': 2, 'provider': 'openai', 'is_active': True},
                {'id': 4, 'provider': 'openai', 'is_active': True}
            ],
            # For anthropic
            [
                {'id': 3, 'provider': 'anthropic', 'is_active': True},
                {'id': 5, 'provider': 'anthropic', 'is_active': True}
            ]
        ]
        
        # Setup rotation success
        mock_rotate.return_value = True
        
        # Auto-rotate keys
        result = self.service.auto_rotate_keys()
        
        # Verify result
        assert result['rotated_count'] == 3
        assert result['failed_count'] == 0
        assert len(result['results']) == 3
        
        # Test with no replacement keys
        mock_get_rotation.return_value = [
            {'id': 6, 'provider': 'gemini', 'is_active': True}
        ]
        mock_get_active.side_effect = [
            # For gemini - only the key that needs rotation
            [{'id': 6, 'provider': 'gemini', 'is_active': True}]
        ]
        
        result = self.service.auto_rotate_keys()
        assert result['rotated_count'] == 0
        assert result['failed_count'] == 1
        assert "没有可用的替代密钥" in result['results'][0]['reason']
        
        # Test with no keys needing rotation
        mock_get_rotation.return_value = []
        result = self.service.auto_rotate_keys()
        assert "没有需要轮换的API密钥" in result['message']
        assert result['rotated_count'] == 0


class TestApiKeySelectorEnhanced:
    """Test enhanced API key selector functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.selector = ApiKeySelector()
        self.test_key = ApiKey(
            id="1",
            provider="openai",
            key="sk-test-key-1234567890abcdef",
            enabled=True
        )
    
    def test_update_key_stats_with_usage(self):
        """Test updating key stats with usage data"""
        # Create response data with usage information
        response_data = {
            'usage': {
                'total_tokens': 1000,
                'prompt_tokens': 200,
                'completion_tokens': 800
            },
            'model': 'gpt-4',
            'request_start_time': time.time() - 0.5
        }
        
        # Update stats
        self.selector.update_key_stats(self.test_key, True, None, response_data)
        
        # Verify stats were updated
        assert self.test_key.requests_count == 1
        assert self.test_key.success_count == 1
        assert self.test_key.total_tokens == 1000
        assert self.test_key.input_tokens == 200
        assert self.test_key.output_tokens == 800
        assert self.test_key.avg_latency > 0
        assert self.test_key.cost > 0
    
    def test_update_key_stats_with_error(self):
        """Test updating key stats with error information"""
        # Create error response
        response_data = {
            'error': 'Rate limit exceeded',
            'request_start_time': time.time() - 0.5
        }
        
        # Update stats with rate limit error
        self.selector.update_key_stats(self.test_key, False, 429, response_data)
        
        # Verify stats were updated
        assert self.test_key.requests_count == 1
        assert self.test_key.error_count == 1
        assert self.test_key.consecutive_errors == 1
        assert self.test_key.last_error == 'Rate limit exceeded'
        assert self.test_key.rate_limited_until is not None
        assert self.test_key.rate_limited_until > time.time()
        
        # Test consecutive errors
        self.selector.update_key_stats(self.test_key, False, 500, {'error': 'Server error'})
        assert self.test_key.consecutive_errors == 2
        
        # Test resetting consecutive errors
        self.selector.update_key_stats(self.test_key, True, 200, {})
        assert self.test_key.consecutive_errors == 0
    
    def test_needs_rotation_property(self):
        """Test the needs_rotation property"""
        # Test consecutive errors trigger
        key = ApiKey(id="1", provider="openai", key="test", consecutive_errors=3)
        assert key.needs_rotation is True
        
        # Test error rate trigger
        key = ApiKey(id="1", provider="openai", key="test", 
                    requests_count=100, error_count=25, success_count=75)
        assert key.needs_rotation is True
        
        # Test request count trigger
        key = ApiKey(id="1", provider="openai", key="test",
                    requests_count=15000, last_rotation=time.time() - 3600)
        # Manually set the requests_at_last_rotation attribute
        setattr(key, 'requests_at_last_rotation', 1000)
        assert key.needs_rotation is True
        
        # Test time-based trigger
        key = ApiKey(id="1", provider="openai", key="test",
                    last_rotation=time.time() - (8 * 24 * 60 * 60))  # 8 days ago
        assert key.needs_rotation is True
        
        # Test healthy key
        key = ApiKey(id="1", provider="openai", key="test",
                    requests_count=100, error_count=5, success_count=95,
                    consecutive_errors=0, last_rotation=time.time() - 3600)
        # Manually set the requests_at_last_rotation attribute
        setattr(key, 'requests_at_last_rotation', 0)
        assert key.needs_rotation is False
    
    def test_calculate_usage_cost(self):
        """Test cost calculation based on usage"""
        # Test OpenAI GPT-4
        usage = {'prompt_tokens': 1000, 'completion_tokens': 500}
        cost = self.selector._calculate_usage_cost('openai', usage, 'gpt-4')
        expected_cost = 1000 * 0.00003 + 500 * 0.00006
        assert cost == pytest.approx(expected_cost)
        
        # Test Claude
        usage = {'prompt_tokens': 1000, 'completion_tokens': 500}
        cost = self.selector._calculate_usage_cost('anthropic', usage, 'claude-3-opus')
        expected_cost = 1000 * 0.00003 + 500 * 0.00015
        assert cost == pytest.approx(expected_cost)
        
        # Test default pricing
        usage = {'prompt_tokens': 1000, 'completion_tokens': 500}
        cost = self.selector._calculate_usage_cost('unknown', usage)
        expected_cost = 1000 * 0.000005 + 500 * 0.00001
        assert cost == pytest.approx(expected_cost)


if __name__ == "__main__":
    pytest.main([__file__])