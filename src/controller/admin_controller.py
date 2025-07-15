from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
import duckdb
from src.service.model_service import ModelService
from src.service.api_key_service import ApiKeyService
from src.service.system_config_service import SystemConfigService
from src.service.route_service import RouteService
from src.service.log_service import LogService
from src.schemas import (
    CreateModelRequest, UpdateModelRequest,
    CreateApiKeyRequest, UpdateKeyStatusRequest,
    CreateRouteRequest, UpdateRouteRequest
)
from src.utils.logging import logger


router = APIRouter(tags=["admin"])

# 服务实例
route_service = RouteService()
log_service = LogService()


# 模型管理
@router.get("/models")
async def get_models():
    """获取所有模型配置"""
    try:
        models = ModelService.get_all_models()
        return models
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型配置失败")


@router.post("/models")
async def create_model(request: CreateModelRequest):
    """创建模型配置"""
    try:
        result = ModelService.create_model(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="创建模型配置失败")


@router.put("/models/{model_id}")
async def update_model(model_id: int, request: UpdateModelRequest):
    """更新模型配置"""
    try:
        result = ModelService.update_model(model_id, request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新模型配置失败")


@router.delete("/models/{model_id}")
async def delete_model(model_id: int):
    """删除模型配置"""
    try:
        result = ModelService.delete_model(model_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="删除模型配置失败")


# API密钥管理
@router.get("/api-keys")
async def get_api_keys(provider: Optional[str] = None):
    """获取API密钥列表"""
    try:
        keys = ApiKeyService.get_all_api_keys(provider)
        return keys
    except Exception as e:
        logger.error(f"获取API密钥失败: {e}")
        raise HTTPException(status_code=500, detail="获取API密钥失败")


@router.post("/api-keys")
async def add_api_key(request: CreateApiKeyRequest):
    """添加API密钥"""
    try:
        result = ApiKeyService.create_api_key(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加API密钥失败: {e}")
        raise HTTPException(status_code=500, detail="添加API密钥失败")


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int):
    """删除API密钥"""
    try:
        result = ApiKeyService.delete_api_key(key_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除API密钥失败: {e}")
        raise HTTPException(status_code=500, detail="删除API密钥失败")


@router.patch("/api-keys/{key_id}/status")
async def update_key_status(key_id: int, request: UpdateKeyStatusRequest):
    """更新API密钥状态"""
    try:
        result = ApiKeyService.update_key_status(key_id, request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新API密钥状态失败: {e}")
        raise HTTPException(status_code=500, detail="更新API密钥状态失败")


# 路由管理
@router.get("/routes")
async def get_routes():
    """获取所有路由"""
    try:
        routes = route_service.get_all_routes()
        return routes
    except Exception as e:
        logger.error(f"获取路由失败: {e}")
        raise HTTPException(status_code=500, detail="获取路由失败")


@router.post("/routes")
async def create_route(request: CreateRouteRequest):
    """创建路由"""
    try:
        route = route_service.create_route(
            path=request.path,
            method=request.method,
            description=request.description,
            enabled=request.enabled
        )
        return {"id": route.id, "message": "路由创建成功"}
    except Exception as e:
        logger.error(f"创建路由失败: {e}")
        raise HTTPException(status_code=500, detail="创建路由失败")


@router.put("/routes/{route_id}")
async def update_route(route_id: int, request: UpdateRouteRequest):
    """更新路由"""
    try:
        route = route_service.update_route(
            route_id,
            path=request.path,
            method=request.method,
            description=request.description,
            enabled=request.enabled
        )
        if not route:
            raise HTTPException(status_code=404, detail="路由不存在")
        return {"message": "路由更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新路由失败: {e}")
        raise HTTPException(status_code=500, detail="更新路由失败")


@router.delete("/routes/{route_id}")
async def delete_route(route_id: int):
    """删除路由"""
    try:
        success = route_service.delete_route(route_id)
        if not success:
            raise HTTPException(status_code=404, detail="路由不存在")
        return {"message": "路由删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除路由失败: {e}")
        raise HTTPException(status_code=500, detail="删除路由失败")


# 系统配置管理
@router.get("/system-configs")
async def get_system_configs():
    """获取所有系统配置"""
    try:
        configs = SystemConfigService.get_all_configs(hide_sensitive=True)
        return configs
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统配置失败")


@router.put("/system-configs/{config_key}")
async def update_system_config(config_key: str, request: dict):
    """更新系统配置"""
    try:
        config_value = request.get('config_value')
        if not config_value:
            raise HTTPException(status_code=400, detail="配置值不能为空")
        
        result = SystemConfigService.update_config(config_key, config_value)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新系统配置失败")


# 日志和统计
@router.get("/logs")
async def get_logs(
    page: int = 1,
    size: int = 20,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    source_model: Optional[str] = None,
    target_model: Optional[str] = None,
    status: Optional[str] = None
):
    """获取请求日志"""
    try:
        result = log_service.get_logs_paginated(
            page=page, size=size, start_time=start_time, end_time=end_time,
            source_model=source_model, target_model=target_model, status_code=status
        )
        return result
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志失败")


@router.get("/stats")
async def get_stats(days: int = 7):
    """获取统计数据"""
    try:
        daily_stats = log_service.get_daily_stats(days)
        model_stats = log_service.get_model_usage_stats(days)
        error_stats = log_service.get_error_stats(days)
        performance_stats = log_service.get_api_performance_stats(days)
        
        return {
            'daily_requests': daily_stats,
            'model_usage': model_stats,
            'error_stats': error_stats,
            'api_performance': performance_stats
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")


# 安全管理
@router.post("/security/rotate-admin-key")
async def rotate_admin_key():
    """轮换管理密钥"""
    try:
        import secrets
        import string
        
        # 生成新的32位随机密钥
        alphabet = string.ascii_letters + string.digits
        new_key = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        # 更新系统配置
        config_service = SystemConfigService()
        old_key = config_service.get_config_value("auth.admin_key")
        config_service.update_config("auth.admin_key", new_key)
        
        logger.info(f"管理密钥已轮换")
        
        return {
            "message": "管理密钥轮换成功",
            "new_key": new_key,
            "old_key_masked": f"{old_key[:4]}****{old_key[-4:]}" if old_key and len(old_key) > 8 else "****",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"轮换管理密钥失败: {e}")
        raise HTTPException(status_code=500, detail="轮换管理密钥失败")


@router.get("/security/key-info")
async def get_admin_key_info():
    """获取管理密钥信息（脱敏）"""
    try:
        config_service = SystemConfigService()
        admin_key = config_service.get_config_value("auth.admin_key")
        
        if not admin_key:
            return {
                "status": "not_set",
                "message": "管理密钥未设置"
            }
        
        # 脱敏显示
        masked_key = f"{admin_key[:4]}****{admin_key[-4:]}" if len(admin_key) > 8 else "****"
        
        return {
            "status": "active",
            "masked_key": masked_key,
            "key_length": len(admin_key),
            "last_updated": "未知"  # 可以从system_config表的updated_at字段获取
        }
    except Exception as e:
        logger.error(f"获取管理密钥信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取管理密钥信息失败")


@router.post("/security/validate-key")
async def validate_admin_key(request: dict):
    """验证管理密钥"""
    try:
        test_key = request.get('key')
        if not test_key:
            raise HTTPException(status_code=400, detail="密钥不能为空")
        
        config_service = SystemConfigService()
        stored_key = config_service.get_config_value("auth.admin_key")
        
        is_valid = test_key == stored_key
        
        return {
            "valid": is_valid,
            "message": "密钥有效" if is_valid else "密钥无效"
        }
    except Exception as e:
        logger.error(f"验证管理密钥失败: {e}")
        raise HTTPException(status_code=500, detail="验证管理密钥失败")