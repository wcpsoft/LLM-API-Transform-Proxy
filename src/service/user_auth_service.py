"""用户认证服务"""

import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

from src.dao.user_dao import UserDAO, SessionDAO
from src.models.user import User, UserSession, LoginRequest, LoginResponse, ChangePasswordRequest, CreateUserRequest
from src.utils.crypto import SM3Crypto
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserAuthService:
    """用户认证服务"""
    
    def __init__(self):
        self.user_dao = UserDAO()
        self.session_dao = SessionDAO()
        self.crypto = SM3Crypto()
        
        # 会话配置
        self.session_duration_hours = 24  # 默认24小时过期
        self.max_login_attempts = 5  # 最大登录尝试次数
        self.lockout_duration_minutes = 30  # 锁定时长
    
    def login(self, request: LoginRequest) -> LoginResponse:
        """用户登录
        
        Args:
            request: 登录请求
            
        Returns:
            登录响应
        """
        try:
            # 验证用户凭据
            user = self.user_dao.get_user_by_username(request.username)
            if not user:
                logger.warning(f"用户不存在: {request.username}")
                return LoginResponse(
                    success=False,
                    message="用户名或密码错误"
                )
            
            if not user.is_active:
                logger.warning(f"用户已被禁用: {request.username}")
                return LoginResponse(
                    success=False,
                    message="用户账户已被禁用"
                )
            
            # 验证密码
            if not self.crypto.verify_password(request.password, user.password_hash):
                logger.warning(f"密码错误: {request.username}")
                return LoginResponse(
                    success=False,
                    message="用户名或密码错误"
                )
            
            # 创建会话
            session_result = self._create_user_session(user, request.remember_me)
            if not session_result[0]:
                return LoginResponse(
                    success=False,
                    message="创建会话失败，请重试"
                )
            
            session = session_result[1]
            logger.info(f"用户登录成功: {request.username}")
            
            return LoginResponse(
                success=True,
                message="登录成功",
                session_id=session.session_id,
                username=user.username,
                expires_at=session.expires_at.isoformat() if session.expires_at else None,
                user_info=user.to_dict()
            )
            
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return LoginResponse(
                success=False,
                message="登录失败，请重试"
            )
    
    def logout(self, session_id: str) -> bool:
        """用户退出
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否退出成功
        """
        try:
            success = self.session_dao.deactivate_session(session_id)
            if success:
                logger.info(f"用户退出成功: {session_id}")
            return success
        except Exception as e:
            logger.error(f"退出失败: {e}")
            return False
    
    def validate_session(self, session_id: str) -> Optional[UserSession]:
        """验证会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            有效的会话对象，无效返回None
        """
        try:
            session = self.session_dao.get_session_by_id(session_id)
            if not session:
                return None
            
            # 检查会话是否过期
            if session.is_expired():
                # 自动停用过期会话
                self.session_dao.deactivate_session(session_id)
                return None
            
            return session
            
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None
    
    def refresh_session(self, session_id: str) -> Optional[UserSession]:
        """刷新会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            刷新后的会话对象，失败返回None
        """
        try:
            session = self.validate_session(session_id)
            if not session:
                return None
            
            # 延长会话有效期
            session.expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
            
            if self.session_dao.update_session(session):
                logger.info(f"会话刷新成功: {session_id}")
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"刷新会话失败: {e}")
            return None
    
    def change_password(self, session_id: str, request: ChangePasswordRequest) -> Tuple[bool, str]:
        """修改密码
        
        Args:
            session_id: 会话ID
            request: 修改密码请求
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 验证会话
            session = self.validate_session(session_id)
            if not session:
                return False, "会话无效或已过期"
            
            # 获取用户
            user = self.user_dao.get_user_by_id(session.user_id)
            if not user:
                return False, "用户不存在"
            
            # 验证旧密码
            if not self.crypto.verify_password(request.old_password, user.password_hash):
                return False, "原密码错误"
            
            # 更新密码
            user.password_hash = self.crypto.hash_password(request.new_password)
            user.updated_at = datetime.now()
            
            if self.user_dao.update_user(user):
                # 停用用户的所有其他会话（强制重新登录）
                self.session_dao.deactivate_user_sessions(user.id, session_id)
                logger.info(f"用户密码修改成功: {user.username}")
                return True, "密码修改成功"
            
            return False, "密码修改失败"
            
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return False, "修改密码失败，请重试"
    
    def create_user(self, request: CreateUserRequest) -> Tuple[bool, str, Optional[User]]:
        """创建用户
        
        Args:
            request: 创建用户请求
            
        Returns:
            (是否成功, 消息, 用户对象)
        """
        try:
            # 检查用户名是否已存在
            existing_user = self.user_dao.get_user_by_username(request.username)
            if existing_user:
                return False, "用户名已存在", None
            
            # 创建用户
            user = User(
                username=request.username,
                password_hash=self.crypto.hash_password(request.password),
                email=request.email,
                is_active=request.is_active
            )
            
            user_id = self.user_dao.create_user(user)
            if user_id:
                user.id = user_id
                logger.info(f"用户创建成功: {user.username}")
                return True, "用户创建成功", user
            
            return False, "用户创建失败", None
            
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return False, "创建用户失败，请重试", None
    
    def get_user_profile(self, session_id: str) -> Optional[dict]:
        """获取用户资料
        
        Args:
            session_id: 会话ID
            
        Returns:
            用户资料字典，失败返回None
        """
        try:
            session = self.validate_session(session_id)
            if not session:
                return None
            
            user = self.user_dao.get_user_by_id(session.user_id)
            if user:
                return user.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户资料失败: {e}")
            return None
    
    def get_user_sessions(self, session_id: str) -> Optional[list]:
        """获取用户会话列表
        
        Args:
            session_id: 当前会话ID
            
        Returns:
            会话列表，失败返回None
        """
        try:
            session = self.validate_session(session_id)
            if not session:
                return None
            
            sessions = self.session_dao.get_user_sessions(session.user_id)
            return [s.to_dict() for s in sessions]
            
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话
        
        Returns:
            清理的会话数量
        """
        try:
            count = self.session_dao.cleanup_expired_sessions()
            if count > 0:
                logger.info(f"清理过期会话: {count} 个")
            return count
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
    
    def _create_user_session(self, user: User, remember_me: bool = False) -> Tuple[bool, Optional[UserSession]]:
        """创建用户会话
        
        Args:
            user: 用户对象
            remember_me: 是否记住登录
            
        Returns:
            (是否成功, 会话对象)
        """
        try:
            # 停用用户的所有现有会话（单点登录）
            self.session_dao.deactivate_user_sessions(user.id)
            
            # 生成会话信息
            session_id = self.crypto.generate_session_id()
            login_timestamp = int(time.time())
            
            # 生成认证token
            token = self.crypto.generate_token(
                user.password_hash,
                user.username,
                login_timestamp
            )
            
            # 设置过期时间
            duration_hours = 24 * 7 if remember_me else self.session_duration_hours  # 记住登录延长到7天
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            
            # 创建会话对象
            session = UserSession(
                session_id=session_id,
                user_id=user.id,
                username=user.username,
                login_timestamp=login_timestamp,
                token_hash=token,
                expires_at=expires_at,
                is_active=True
            )
            
            # 保存会话
            if self.session_dao.create_session(session):
                return True, session
            
            return False, None
            
        except Exception as e:
            logger.error(f"创建用户会话失败: {e}")
            return False, None