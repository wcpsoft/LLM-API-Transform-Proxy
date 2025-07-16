#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code Proxy - 主应用入口
重构后的简洁版本，使用MVC架构
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.config import get_config
from src.utils.db import init_db, init_default_system_configs
from src.utils.logging import logger
from src.controller.api_controller import router as api_router
from src.controller.admin_controller import router as admin_router
from src.controller.auth_controller import router as auth_router
from src.service.system_config_service import SystemConfigService
from src.middleware.exception_handler import ExceptionHandlerMiddleware, setup_exception_handlers
from src.middleware.monitoring import setup_monitoring


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    try:
        init_db()
        init_default_system_configs()
        logger.info("应用启动完成")
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Claude Code Proxy",
    description="AI模型代理服务",
    version="2.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理中间件
app.add_middleware(ExceptionHandlerMiddleware)

# 设置自定义异常处理器
setup_exception_handlers(app)

# 设置监控功能
setup_monitoring(app)


# API认证依赖
from fastapi import Header, Query
from typing import Optional

async def verify_admin_key(
    admin_key: Optional[str] = Query(None, alias="admin_key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """验证管理API密钥"""
    # 从查询参数或请求头获取密钥
    key = admin_key or x_admin_key
    
    if not key:
        raise HTTPException(status_code=401, detail="缺少认证密钥")
    
    config_service = SystemConfigService()
    stored_key = config_service.get_config_value("auth.admin_key")
    
    # 如果没有设置admin_key，使用默认值
    if not stored_key:
        stored_key = "admin123"
    
    if key != stored_key:
        raise HTTPException(status_code=401, detail="认证密钥无效")
    
    return True


# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(api_router, prefix="")
app.include_router(admin_router, prefix="/v1/admin", dependencies=[Depends(verify_admin_key)])
app.include_router(auth_router, prefix="/v1/auth")

# 为前端添加/api前缀的路由
app.include_router(api_router, prefix="/api")
app.include_router(admin_router, prefix="/api/v1/admin", dependencies=[Depends(verify_admin_key)])
app.include_router(auth_router, prefix="/api/v1/auth")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "claude-code-proxy"}


# 服务发现
@app.get("/discovery")
async def service_discovery():
    """服务发现接口"""
    config_service = SystemConfigService()
    return {
        "service": "claude-code-proxy",
        "version": "2.0.0",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health",
            "admin": "/v1/admin"
        },
        "discovery_enabled": config_service.get_config_value("service.discovery_enabled", "true") == "true"
    }


if __name__ == "__main__":
    # 从系统配置获取服务器配置
    try:
        config_service = SystemConfigService()
        host = config_service.get_config_value("server.host", "0.0.0.0")
        port = int(config_service.get_config_value("server.port", "8082"))
        debug = config_service.get_config_value("server.debug", "false") == "true"
    except Exception:
        # 如果配置服务不可用，使用默认值
        from src.config import get_host, get_port, get_debug
        host = get_host()
        port = get_port()
        debug = get_debug()
    
    logger.info(f"启动服务器: {host}:{port}")
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )