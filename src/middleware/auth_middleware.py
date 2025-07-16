"""认证中间件"""

from fastapi import HTTPException, Depends, Header, Request
from typing import Optional, Dict, Any

from src.service.user_auth_service import UserAuthService
from src.utils.logging import get_logger

logger = get_logger(__name__)


# 创建全局认证服务实例
auth_service = UserAuthService()

# 不需要认证的路径
PUBLIC_PATHS = {
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/health',
    '/discovery',
    '/api/v1/models',  # 模型列表可能需要公开访问
}

# 不需要认证的路径前缀
PUBLIC_PREFIXES = [
    '/static/',
    '/assets/',
    '/favicon.ico',
]
def is_public_path(path: str) -> bool:
    """检查是否为公开路径
    
    Args:
        path: 请求路径
        
    Returns:
        是否为公开路径
    """
    # 检查完全匹配的公开路径
    if path in PUBLIC_PATHS:
        return True
    
    # 检查前缀匹配的公开路径
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    
    return False


def extract_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """从Authorization头中提取token
    
    Args:
        authorization: Authorization头的值
        
    Returns:
        提取的token，没有返回None
    """
    if not authorization:
        return None
    
    # 检查Bearer格式
    if not authorization.startswith('Bearer '):
        return None
    
    # 提取token
    token = authorization[7:]  # 去掉'Bearer '前缀
    return token.strip() if token else None


async def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """获取当前用户信息（需要认证）
    
    Args:
        request: FastAPI请求对象
        authorization: Authorization头
        
    Returns:
        用户信息字典
        
    Raises:
        HTTPException: 认证失败时抛出
    """
    try:
        # 检查是否为公开路径
        if is_public_path(str(request.url.path)):
            raise HTTPException(status_code=401, detail="此接口需要认证")
        
        # 提取token
        token = extract_token_from_header(authorization)
        if not token:
            raise HTTPException(status_code=401, detail="缺少认证token")
        
        # 验证会话
        session = auth_service.validate_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="无效或过期的认证token")
        
        # 获取用户信息
        user_info = auth_service.get_user_profile(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="用户信息获取失败")
        
        # 刷新会话（延长有效期）
        auth_service.refresh_session(token)
        
        # 添加session_id到用户信息中
        user_info['session_id'] = token
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"认证请求失败: {e}")
        raise HTTPException(status_code=401, detail="认证失败")


async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取当前管理员用户信息（需要管理员权限）
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        管理员用户信息字典
        
    Raises:
        HTTPException: 权限不足时抛出
    """
    # 检查管理员权限
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return current_user


async def get_optional_user(request: Request, authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """获取可选的用户信息（认证失败不会阻止访问）
    
    Args:
        request: FastAPI请求对象
        authorization: Authorization头
        
    Returns:
        用户信息字典，认证失败返回None
    """
    try:
        return await get_current_user(request, authorization)
    except HTTPException:
        return None
    except Exception as e:
        logger.error(f"可选认证失败: {e}")
        return None


# 导出依赖函数，方便使用
CurrentUser = Depends(get_current_user)
CurrentAdminUser = Depends(get_current_admin_user)
OptionalUser = Depends(get_optional_user)