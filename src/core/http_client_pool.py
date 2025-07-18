#!/usr/bin/env python3
"""
HTTP客户端连接池管理器 - 实现连接池和连接复用
"""
import asyncio
import aiohttp
import ssl
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import logging
import time
from contextlib import asynccontextmanager
import certifi

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """连接池配置"""
    total_connections: int = 100
    per_host_connections: int = 30
    connection_timeout: float = 30.0
    read_timeout: float = 30.0
    keepalive_timeout: float = 30.0
    max_keepalive_connections: int = 30
    ssl_verify: bool = True
    enable_http2: bool = True
    retry_attempts: int = 3
    retry_backoff_factor: float = 0.3


class HTTPClientPool:
    """HTTP客户端连接池管理器"""
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._ssl_context = None
        self._connector = None
        self._semaphore = None
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "active_connections": 0,
            "created_at": time.time()
        }
        self._setup_ssl_context()
    
    def _setup_ssl_context(self):
        """设置SSL上下文"""
        if self.config.ssl_verify:
            self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        else:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def start(self):
        """启动连接池"""
        if self._connector is None:
            timeout = aiohttp.ClientTimeout(
                total=self.config.connection_timeout,
                connect=self.config.connection_timeout,
                sock_read=self.config.read_timeout,
                sock_connect=self.config.connection_timeout
            )
            
            connector = aiohttp.TCPConnector(
                limit=self.config.total_connections,
                limit_per_host=self.config.per_host_connections,
                keepalive_timeout=self.config.keepalive_timeout,
                ssl=self._ssl_context,
                enable_cleanup_closed=True
            )
            
            self._connector = connector
            self._semaphore = asyncio.Semaphore(self.config.total_connections)
            
            logger.info("HTTP客户端连接池已启动")
    
    async def close(self):
        """关闭连接池"""
        for session in self._sessions.values():
            await session.close()
        
        if self._connector:
            await self._connector.close()
        
        self._sessions.clear()
        self._connector = None
        self._semaphore = None
        
        logger.info("HTTP客户端连接池已关闭")
    
    def get_session(self, name: str = "default") -> aiohttp.ClientSession:
        """获取或创建会话"""
        if name not in self._sessions:
            timeout = aiohttp.ClientTimeout(
                total=self.config.connection_timeout,
                connect=self.config.connection_timeout,
                sock_read=self.config.read_timeout,
                sock_connect=self.config.connection_timeout
            )
            
            session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                trust_env=True
            )
            
            self._sessions[name] = session
        
        return self._sessions[name]
    
    @asynccontextmanager
    async def get_connection(self, name: str = "default"):
        """获取连接上下文管理器"""
        if not self._semaphore:
            await self.start()
        
        async with self._semaphore:
            session = self.get_session(name)
            try:
                yield session
            except Exception as e:
                logger.error(f"HTTP连接错误: {e}")
                raise
    
    async def request(
        self,
        method: str,
        url: str,
        session_name: str = "default",
        **kwargs
    ) -> aiohttp.ClientResponse:
        """发送HTTP请求"""
        
        start_time = time.time()
        self._stats["total_requests"] += 1
        
        try:
            async with self.get_connection(session_name) as session:
                response = await session.request(method, url, **kwargs)
                
                # 更新统计信息
                response_time = time.time() - start_time
                self._update_stats(response_time, success=True)
                
                return response
        
        except Exception as e:
            response_time = time.time() - start_time
            self._update_stats(response_time, success=False)
            logger.error(f"HTTP请求失败: {method} {url} - {e}")
            raise
    
    def _update_stats(self, response_time: float, success: bool):
        """更新统计信息"""
        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1
        
        # 更新平均响应时间
        total = self._stats["successful_requests"] + self._stats["failed_requests"]
        if total > 1:
            self._stats["average_response_time"] = (
                (self._stats["average_response_time"] * (total - 1) + response_time) / total
            )
        else:
            self._stats["average_response_time"] = response_time
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            **self._stats,
            "uptime": time.time() - self._stats["created_at"],
            "success_rate": (
                self._stats["successful_requests"] / max(self._stats["total_requests"], 1)
            ),
            "active_sessions": len(self._sessions)
        }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        if not self._connector:
            return {}
        
        return {
            "total_connections": self._connector.limit,
            "per_host_connections": self._connector.limit_per_host,
            "active_connections": len(self._connector._acquired),
            "free_connections": len(self._connector._free),
            "keepalive_timeout": self._connector.keepalive_timeout
        }


class ProviderClientPool:
    """提供商客户端连接池"""
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.pool = HTTPClientPool(config)
        self.provider_configs: Dict[str, Dict[str, Any]] = {}
    
    def configure_provider(
        self,
        provider_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ):
        """配置提供商"""
        
        self.provider_configs[provider_name] = {
            "base_url": base_url,
            "api_key": api_key,
            "headers": headers or {},
            "timeout": timeout
        }
    
    async def provider_request(
        self,
        provider_name: str,
        method: str,
        endpoint: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """向提供商发送请求"""
        
        if provider_name not in self.provider_configs:
            raise ValueError(f"未配置的提供商: {provider_name}")
        
        config = self.provider_configs[provider_name]
        url = f"{config['base_url']}{endpoint}"
        
        # 合并headers
        headers = kwargs.pop("headers", {})
        headers.update(config["headers"])
        
        if config.get("api_key"):
            headers["Authorization"] = f"Bearer {config['api_key']}"
        
        # 设置超时
        if config.get("timeout"):
            kwargs["timeout"] = aiohttp.ClientTimeout(total=config["timeout"])
        
        return await self.pool.request(
            method,
            url,
            session_name=provider_name,
            headers=headers,
            **kwargs
        )
    
    def get_provider_stats(self, provider_name: str) -> Dict[str, Any]:
        """获取提供商统计信息"""
        stats = self.pool.get_stats()
        stats["provider_name"] = provider_name
        return stats


class ConnectionPoolManager:
    """连接池管理器 - 单例模式"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "initialized"):
            self.pool = HTTPClientPool()
            self.provider_pool = ProviderClientPool()
            self.initialized = True
    
    async def initialize(self, config: Optional[PoolConfig] = None):
        """初始化连接池"""
        async with self._lock:
            if config:
                self.pool = HTTPClientPool(config)
                self.provider_pool = ProviderClientPool(config)
            await self.pool.start()
    
    async def shutdown(self):
        """关闭连接池"""
        async with self._lock:
            await self.pool.close()
            await self.provider_pool.pool.close()
    
    @property
    def http_pool(self) -> HTTPClientPool:
        """获取HTTP连接池"""
        return self.pool
    
    @property
    def providers(self) -> ProviderClientPool:
        """获取提供商连接池"""
        return self.provider_pool


# 全局连接池管理器
pool_manager = ConnectionPoolManager()