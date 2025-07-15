import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from threading import Lock
import logging

logger = logging.getLogger(__name__)

@dataclass
class ApiKeyStats:
    """API密钥统计信息"""
    key: str
    requests_count: int = 0
    last_request_time: float = 0
    rate_limit_reset_time: float = 0
    is_rate_limited: bool = False
    error_count: int = 0
    success_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.requests_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def requests_per_minute(self) -> float:
        """计算每分钟请求数"""
        current_time = time.time()
        time_diff = current_time - self.last_request_time
        if time_diff < 60:  # 1分钟内
            return self.requests_count / (time_diff / 60) if time_diff > 0 else 0
        return 0

class ApiKeyManager:
    """API密钥管理器 - 支持密钥池、自动切换和速率统计"""
    
    def __init__(self):
        self._key_stats: Dict[str, Dict[str, ApiKeyStats]] = {}  # provider -> {key: stats}
        self._lock = Lock()
    
    def add_keys(self, provider: str, keys: List[str]):
        """添加API密钥到池中"""
        with self._lock:
            if provider not in self._key_stats:
                self._key_stats[provider] = {}
            
            for key in keys:
                if key not in self._key_stats[provider]:
                    self._key_stats[provider][key] = ApiKeyStats(key=key)
    
    def get_best_key(self, provider: str) -> Optional[str]:
        """获取最佳可用密钥"""
        with self._lock:
            if provider not in self._key_stats or not self._key_stats[provider]:
                return None
            
            current_time = time.time()
            available_keys = []
            
            for key, stats in self._key_stats[provider].items():
                # 检查是否超出速率限制
                if stats.is_rate_limited and current_time < stats.rate_limit_reset_time:
                    continue
                elif stats.is_rate_limited and current_time >= stats.rate_limit_reset_time:
                    # 重置速率限制状态
                    stats.is_rate_limited = False
                    stats.rate_limit_reset_time = 0
                
                available_keys.append((key, stats))
            
            if not available_keys:
                return None
            
            # 选择成功率最高且请求数最少的密钥
            best_key = min(available_keys, 
                         key=lambda x: (-x[1].success_rate, x[1].requests_count))[0]
            
            return best_key
    
    def get_next_key(self, provider: str, custom_keys: Optional[List[str]] = None) -> Optional[str]:
        """获取下一个可用密钥"""
        if custom_keys:
            # 使用自定义密钥列表
            for key in custom_keys:
                # 简单轮询，可以后续优化为更智能的选择
                return key
            return None
        else:
            # 使用密钥池
            return self.get_best_key(provider)
    
    def record_request(self, provider: str, key: str, success: bool = True, 
                      status_code: Optional[int] = None):
        """记录API请求结果"""
        with self._lock:
            if provider not in self._key_stats or key not in self._key_stats[provider]:
                return
            
            stats = self._key_stats[provider][key]
            stats.requests_count += 1
            stats.last_request_time = time.time()
            
            if success:
                stats.success_count += 1
            else:
                stats.error_count += 1
                
                # 处理429错误（速率限制）
                if status_code == 429:
                    stats.is_rate_limited = True
                    # 设置重置时间（默认1分钟后重试）
                    stats.rate_limit_reset_time = time.time() + 60
                    logger.warning(f"API key rate limited for provider {provider}: {key[:10]}...")
    
    def get_stats(self, provider: Optional[str] = None) -> Dict:
        """获取统计信息"""
        with self._lock:
            if provider:
                if provider not in self._key_stats:
                    return {}
                
                return {
                    key: {
                        'requests_count': stats.requests_count,
                        'success_rate': stats.success_rate,
                        'requests_per_minute': stats.requests_per_minute,
                        'is_rate_limited': stats.is_rate_limited,
                        'error_count': stats.error_count,
                        'success_count': stats.success_count
                    }
                    for key, stats in self._key_stats[provider].items()
                }
            
            # 返回所有provider的统计
            return {
                prov: {
                    key: {
                        'requests_count': stats.requests_count,
                        'success_rate': stats.success_rate,
                        'requests_per_minute': stats.requests_per_minute,
                        'is_rate_limited': stats.is_rate_limited,
                        'error_count': stats.error_count,
                        'success_count': stats.success_count
                    }
                    for key, stats in keys.items()
                }
                for prov, keys in self._key_stats.items()
            }

# 全局API密钥管理器实例
api_key_manager = ApiKeyManager()