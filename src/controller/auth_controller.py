"""用户认证控制器"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Optional

from src.service.user_auth_service import UserAuthService
from src.models.user import LoginRequest, ChangePasswordRequest, CreateUserRequest
from src.middleware.auth_middleware import get_current_user, get_current_admin_user
from src.utils.logging import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(tags=['认证'])

# 创建服务实例
auth_service = UserAuthService()


@router.post('/login')
async def login(login_request: LoginRequest):
    """用户登录"""
    try:
        # 执行登录
        response = auth_service.login(login_request)
        
        if response.success:
            return response.to_dict()
        else:
            raise HTTPException(status_code=401, detail=response.message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录接口异常: {e}")
        raise HTTPException(status_code=500, detail="登录失败，请重试")


@router.post('/logout')
async def logout(current_user: dict = Depends(get_current_user)):
    """用户退出"""
    try:
        session_id = current_user['session_id']
        success = auth_service.logout(session_id)
        
        if success:
            return {
                'success': True,
                'message': '退出成功'
            }
        else:
            raise HTTPException(status_code=500, detail='退出失败')
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"退出接口异常: {e}")
        raise HTTPException(status_code=500, detail="退出失败，请重试")


@router.get('/profile')
async def get_profile(current_user: dict = Depends(get_current_user)):
    """获取用户资料"""
    try:
        return {
            'success': True,
            'data': current_user
        }
        
    except Exception as e:
        logger.error(f"获取用户资料异常: {e}")
        raise HTTPException(status_code=500, detail="获取用户资料失败")


@router.get('/sessions')
async def get_sessions(current_user: dict = Depends(get_current_user)):
    """获取用户会话列表"""
    try:
        session_id = current_user['session_id']
        sessions = auth_service.get_user_sessions(session_id)
        
        if sessions is not None:
            return {
                'success': True,
                'data': sessions
            }
        else:
            raise HTTPException(status_code=500, detail="获取会话列表失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话列表异常: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.post('/change-password')
async def change_password(change_request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """修改密码"""
    try:
        # 执行密码修改
        session_id = current_user['session_id']
        success, message = auth_service.change_password(session_id, change_request)
        
        if success:
            return {
                'success': True,
                'message': message
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码接口异常: {e}")
        raise HTTPException(status_code=500, detail="修改密码失败，请重试")


@router.post('/register')
async def register(create_request: CreateUserRequest, current_admin: dict = Depends(get_current_admin_user)):
    """注册新用户（管理员创建用户）"""
    try:
        # 创建用户
        success, message = auth_service.create_user(create_request)
        
        if success:
            return {
                'success': True,
                'message': message
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册接口异常: {e}")
        raise HTTPException(status_code=500, detail="注册失败，请重试")


@router.get('/validate')
async def validate_token(current_user: dict = Depends(get_current_user)):
    """验证token有效性"""
    try:
        # 如果能到达这里，说明token有效
        return {
            'success': True,
            'message': 'Token有效',
            'user': current_user
        }
        
    except Exception as e:
        logger.error(f"验证token接口异常: {e}")
        raise HTTPException(status_code=500, detail="Token验证失败")


@router.post('/refresh')
async def refresh_session(current_user: dict = Depends(get_current_user)):
    """刷新会话"""
    try:
        session_id = current_user['session_id']
        session = auth_service.refresh_session(session_id)
        
        if session:
            return {
                'success': True,
                'message': '会话刷新成功',
                'expires_at': session.expires_at.isoformat() if session.expires_at else None
            }
        else:
            raise HTTPException(status_code=400, detail="会话刷新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新会话接口异常: {e}")
        raise HTTPException(status_code=500, detail="会话刷新失败，请重试")


@router.post('/cleanup-sessions')
async def cleanup_expired_sessions(current_admin: dict = Depends(get_current_admin_user)):
    """清理过期会话（管理员功能）"""
    try:
        count = auth_service.cleanup_expired_sessions()
        return {
            'success': True,
            'message': f'清理了 {count} 个过期会话'
        }
        
    except Exception as e:
        logger.error(f"清理过期会话接口异常: {e}")
        raise HTTPException(status_code=500, detail="清理过期会话失败")