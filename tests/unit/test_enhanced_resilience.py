"""
测试增强的错误处理和弹性功能
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
import tempfile
import os

from src.core.errors.enhanced_retry import EnhancedRetryHandler
from src.core.errors.graceful_degradation import fallback_handler
from src.core.errors.error_context import ErrorContext
from src.core.health.health_checker import HealthChecker
from src.config.resilience_config import ResilienceConfig


class TestEnhancedRetryHandler:
    """测试增强的重试处理器"""
    
    def setup_method(self):
        self.retry_handler = EnhancedRetryHandler()
    
    @pytest.mark.asyncio
    async def test_retry_success(self):
        """测试重试成功"""
        call_count = 0
        
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("临时错误")
            return "成功"
        
        result = await self.retry_handler.retry(
            max_retries=3,
            service_name="test_service"
        )(failing_then_success)()
        
        assert result == "成功"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """测试重试耗尽"""
        async def always_failing():
            raise ValueError("持续错误")
        
        with pytest.raises(ValueError):
            await self.retry_handler.retry(
                max_retries=2,
                service_name="test_service"
            )(always_failing)()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """测试熔断器"""
        from src.core.errors.retry_handler import CircuitBreaker
        
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1.0,
            name="test_breaker"
        )
        
        # 触发熔断
        for _ in range(3):
            try:
                await breaker.call(lambda: exec("raise ValueError('test')"))
            except ValueError:
                pass
        
        # 应该触发熔断
        with pytest.raises(Exception) as exc_info:
            await breaker.call(lambda: "should not reach")
        
        assert "Circuit breaker is open" in str(exc_info.value)


class TestGracefulDegradation:
    """测试优雅降级"""
    
    def setup_method(self):
        self.fallback_handler = fallback_handler
        self.fallback_handler.fallbacks.clear()
        self.fallback_handler.cache.clear()
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """测试成功执行"""
        async def primary_func(x):
            return x * 2
        
        result = await self.fallback_handler.execute_with_fallback(
            "test_service",
            primary_func,
            5
        )
        
        assert result["data"] == 10
        assert result["source"] == "primary"
        assert result["degraded"] is False
    
    @pytest.mark.asyncio
    async def test_fallback_execution(self):
        """测试降级执行"""
        async def failing_func(x):
            raise ValueError("服务失败")
        
        async def fallback_func(x):
            return x * 3
        
        self.fallback_handler.register_fallback(
            "test_service",
            fallback_func,
            priority=1
        )
        
        result = await self.fallback_handler.execute_with_fallback(
            "test_service",
            failing_func,
            5
        )
        
        assert result["data"] == 15
        assert result["source"] == "fallback"
        assert result["degraded"] is True
    
    @pytest.mark.asyncio
    async def test_caching(self):
        """测试缓存功能"""
        call_count = 0
        
        async def counting_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # 第一次调用
        result1 = await self.fallback_handler.execute_with_fallback(
            "test_service",
            counting_func,
            5,
            use_cache=True
        )
        
        # 第二次调用应该使用缓存
        result2 = await self.fallback_handler.execute_with_fallback(
            "test_service",
            counting_func,
            5,
            use_cache=True
        )
        
        assert result1["data"] == result2["data"]
        assert result2["cached"] is True
        assert call_count == 1


class TestHealthChecker:
    """测试健康检查器"""
    
    def setup_method(self):
        self.health_checker = HealthChecker()
    
    def test_database_health_check(self):
        """测试数据库健康检查"""
        # 模拟数据库连接
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.return_value.execute.return_value.fetchone.return_value = [1]
            
            status = self.health_checker.check_database()
            assert status["status"] == "healthy"
    
    def test_disk_space_check(self):
        """测试磁盘空间检查"""
        with patch('shutil.disk_usage') as mock_usage:
            mock_usage.return_value = Mock(free=10*1024*1024*1024, total=100*1024*1024*1024)
            
            status = self.health_checker.check_disk_space()
            assert status["status"] == "healthy"
            assert "free_gb" in status


class TestResilienceConfig:
    """测试弹性配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ResilienceConfig()
        service_config = config.get_service_config("test_service")
        
        assert service_config.retry.max_retries == 3
        assert service_config.cache.enabled is True
    
    def test_service_specific_config(self):
        """测试服务特定配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = """
services:
  test_service:
    retry:
      max_retries: 5
    cache:
      ttl: 600
"""
            f.write(yaml_content)
            f.flush()
            
            config = ResilienceConfig(f.name)
            service_config = config.get_service_config("test_service")
            
            assert service_config.retry.max_retries == 5
            assert service_config.cache.ttl == 600
            
            os.unlink(f.name)
    
    def test_config_save_load(self):
        """测试配置保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.yaml")
            config = ResilienceConfig(config_path)
            
            # 修改配置
            config.update_service_config("test_service", max_retries=10)
            config.save_config()
            
            # 重新加载
            new_config = ResilienceConfig(config_path)
            service_config = new_config.get_service_config("test_service")
            
            assert service_config.retry.max_retries == 10


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_resilience_flow(self):
        """测试完整的弹性流程"""
        from src.core.errors.enhanced_degradation import enhanced_degradation_manager
        
        call_count = 0
        
        async def primary_service(x):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("临时失败")
            return f"成功: {x}"
        
        async def fallback_service(x):
            return f"降级: {x}"
        
        result = await enhanced_degradation_manager.execute_with_full_resilience(
            service_name="integration_test",
            primary_func=primary_service,
            fallback_func=fallback_service,
            max_retries=3,
            args=(42,)
        )
        
        assert "data" in result
        assert result["data"] == "成功: 42"
        assert result["source"] == "primary"
    
    @pytest.mark.asyncio
    async def test_degradation_metrics(self):
        """测试降级指标"""
        from src.core.errors.enhanced_degradation import enhanced_degradation_manager
        
        metrics = enhanced_degradation_manager.get_service_metrics("test_service")
        
        assert isinstance(metrics, dict)
        assert "health_status" in metrics
        assert "fallbacks_registered" in metrics
        assert "cache_size" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])