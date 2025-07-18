"""
Tests for API key security enhancements
"""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.crypto import ApiKeyEncryption
from src.dao.api_key_dao import ApiKeyDAO
from src.service.api_key_service import ApiKeyService
from src.schemas import CreateApiKeyRequest


class TestApiKeyEncryption:
    """Test API key encryption functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.encryption = ApiKeyEncryption()
        self.test_key = "sk-prod-key-1234567890abcdef"
    
    def test_encrypt_decrypt_key(self):
        """Test API key encryption and decryption"""
        # Encrypt the key
        encrypted = self.encryption.encrypt_key(self.test_key)
        
        # Verify it's encrypted (different from original)
        assert encrypted != self.test_key
        assert len(encrypted) > len(self.test_key)
        
        # Decrypt and verify
        decrypted = self.encryption.decrypt_key(encrypted)
        assert decrypted == self.test_key
    
    def test_mask_key(self):
        """Test API key masking for logs"""
        masked = ApiKeyEncryption.mask_key(self.test_key)
        
        # Should show first 4 characters and mask the rest
        assert masked.startswith("sk-p")
        assert "*" in masked
        assert len(masked) == len(self.test_key)
        
        # Test with custom show_chars
        masked_custom = ApiKeyEncryption.mask_key(self.test_key, show_chars=6)
        assert masked_custom.startswith("sk-pro")
        assert "*" in masked_custom
    
    def test_validate_key_strength(self):
        """Test API key strength validation"""
        # Valid key
        is_valid, msg = ApiKeyEncryption.validate_key_strength(self.test_key)
        assert is_valid
        assert msg == ""
        
        # Empty key
        is_valid, msg = ApiKeyEncryption.validate_key_strength("")
        assert not is_valid
        assert "不能为空" in msg
        
        # Too short
        is_valid, msg = ApiKeyEncryption.validate_key_strength("short")
        assert not is_valid
        assert "长度不能少于" in msg
        
        # Contains test patterns
        is_valid, msg = ApiKeyEncryption.validate_key_strength("sk-demo-key-test")
        assert not is_valid
        assert "测试标识" in msg


class TestApiKeyDAO:
    """Test API key DAO security features"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.dao = ApiKeyDAO()
        self.test_key_data = {
            'provider': 'openai',
            'api_key': 'sk-prod-key-1234567890abcdef',
            'auth_header': 'Authorization',
            'auth_format': 'Bearer {key}',
            'is_active': True
        }
    
    @patch('src.dao.api_key_dao.get_db_connection')
    def test_create_api_key_with_encryption(self, mock_db):
        """Test API key creation with encryption"""
        # Mock database
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = [0]  # max_id
        
        # Create API key
        key_id = self.dao.create_api_key(self.test_key_data)
        
        # Verify database was called with encrypted key
        insert_call = mock_conn.execute.call_args_list[1]  # Second call is INSERT
        insert_args = insert_call[0][1]  # Arguments to INSERT
        encrypted_key = insert_args[2]  # api_key is 3rd argument
        
        # Encrypted key should be different from original
        assert encrypted_key != self.test_key_data['api_key']
        
        # Should be able to decrypt back to original
        decrypted = self.dao._encryption.decrypt_key(encrypted_key)
        assert decrypted == self.test_key_data['api_key']
    
    @patch('src.dao.api_key_dao.get_db_connection')
    def test_get_api_key_with_masking(self, mock_db):
        """Test API key retrieval with masking"""
        # Mock database response
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn
        
        # Simulate encrypted key in database
        encrypted_key = self.dao._encryption.encrypt_key(self.test_key_data['api_key'])
        mock_conn.execute.return_value.fetchone.return_value = [
            1, 'openai', encrypted_key, 'Authorization', 'Bearer {key}', True,
            0, 0, 0, '2024-01-01', '2024-01-01'
        ]
        mock_conn.description = [
            ['id'], ['provider'], ['api_key'], ['auth_header'], ['auth_format'],
            ['is_active'], ['requests_count'], ['success_count'], ['error_count'],
            ['created_at'], ['updated_at']
        ]
        
        # Get key without decryption (default behavior)
        key_data = self.dao.get_api_key_by_id(1)
        
        # Key should be masked
        assert key_data['api_key'] != self.test_key_data['api_key']
        assert key_data['api_key'] != encrypted_key
        assert "*" in key_data['api_key']
        
        # Get key with decryption
        key_data_decrypted = self.dao.get_api_key_by_id(1, decrypt_key=True)
        assert key_data_decrypted['api_key'] == self.test_key_data['api_key']
    
    def test_validate_key_strength_on_create(self):
        """Test key strength validation during creation"""
        # Test with weak key
        weak_key_data = self.test_key_data.copy()
        weak_key_data['api_key'] = 'weak'
        
        with pytest.raises(ValueError, match="长度不能少于"):
            self.dao.create_api_key(weak_key_data)
        
        # Test with demo key
        demo_key_data = self.test_key_data.copy()
        demo_key_data['api_key'] = 'sk-demo-key-replace-with-real'
        
        with pytest.raises(ValueError, match="测试标识"):
            self.dao.create_api_key(demo_key_data)


class TestApiKeyService:
    """Test API key service security features"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = ApiKeyService()
        self.test_request = CreateApiKeyRequest(
            name='prod-key-1',
            provider='openai',
            api_key='sk-prod-key-1234567890abcdef',
            auth_header='Authorization',
            auth_format='Bearer {api_key}',
            enabled=True
        )
    
    @patch.object(ApiKeyDAO, 'create_api_key')
    def test_create_api_key_validation(self, mock_create):
        """Test API key creation with validation"""
        mock_create.return_value = 1
        
        # Valid request should succeed
        result = self.service.create_api_key(self.test_request)
        assert result['id'] == 1
        assert "成功" in result['message']
        
        # Invalid provider should fail
        invalid_request = CreateApiKeyRequest(
            name='invalid-provider-key',
            provider='invalid',
            api_key='sk-prod-key-1234567890abcdef',
            enabled=True
        )
        
        with pytest.raises(ValueError, match="不支持的提供商"):
            self.service.create_api_key(invalid_request)
        
        # Invalid key format should fail
        invalid_key_request = CreateApiKeyRequest(
            name='short-key',
            provider='openai',
            api_key='short',
            enabled=True
        )
        
        with pytest.raises(ValueError, match="API密钥格式无效"):
            self.service.create_api_key(invalid_key_request)
    
    def test_validate_api_key_format(self):
        """Test API key format validation"""
        # OpenAI keys
        assert ApiKeyService.validate_api_key_format('openai', 'sk-1234567890abcdef1234567890')
        assert not ApiKeyService.validate_api_key_format('openai', 'invalid-key')
        assert not ApiKeyService.validate_api_key_format('openai', 'sk-short')
        
        # Anthropic keys
        assert ApiKeyService.validate_api_key_format('anthropic', 'sk-ant-1234567890abcdef1234567890abcdef')
        assert not ApiKeyService.validate_api_key_format('anthropic', 'sk-1234567890abcdef')
        
        # Gemini keys
        assert ApiKeyService.validate_api_key_format('gemini', 'AIzaSyD1234567890abcdef1234567890')
        assert not ApiKeyService.validate_api_key_format('gemini', 'short')
        
        # DeepSeek keys
        assert ApiKeyService.validate_api_key_format('deepseek', 'sk-1234567890abcdef1234567890')
        assert not ApiKeyService.validate_api_key_format('deepseek', 'invalid-key')


class TestSecurityIntegration:
    """Integration tests for security features"""
    
    def test_end_to_end_key_security(self):
        """Test complete key security flow"""
        encryption = ApiKeyEncryption()
        original_key = "sk-prod-integration-key-1234567890"
        
        # 1. Validate key strength
        is_valid, msg = encryption.validate_key_strength(original_key)
        assert is_valid
        
        # 2. Encrypt for storage
        encrypted_key = encryption.encrypt_key(original_key)
        assert encrypted_key != original_key
        
        # 3. Mask for logging
        masked_key = encryption.mask_key(original_key)
        assert masked_key != original_key
        assert masked_key.startswith("sk-p")
        assert "*" in masked_key
        
        # 4. Decrypt for use
        decrypted_key = encryption.decrypt_key(encrypted_key)
        assert decrypted_key == original_key
        
        # 5. Verify masking doesn't affect functionality
        masked_encrypted = encryption.mask_key(encrypted_key)
        assert masked_encrypted != encrypted_key
        assert "*" in masked_encrypted


if __name__ == "__main__":
    pytest.main([__file__])