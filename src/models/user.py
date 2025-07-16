"""用户相关数据模型"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    email: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建用户对象"""
        def parse_datetime(dt_value):
            if not dt_value:
                return None
            if isinstance(dt_value, str):
                return datetime.fromisoformat(dt_value)
            elif isinstance(dt_value, datetime):
                return dt_value
            return None
        
        return cls(
            id=data.get('id'),
            username=data.get('username', ''),
            password_hash=data.get('password_hash', ''),
            email=data.get('email'),
            is_active=data.get('is_active', True),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at'))
        )


@dataclass
class UserSession:
    """用户会话模型"""
    session_id: str = ""
    user_id: Optional[int] = None
    username: str = ""
    login_timestamp: int = 0
    token_hash: str = ""
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'username': self.username,
            'login_timestamp': self.login_timestamp,
            'token_hash': self.token_hash,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserSession':
        """从字典创建会话对象"""
        def parse_datetime(dt_value):
            if not dt_value:
                return None
            if isinstance(dt_value, str):
                return datetime.fromisoformat(dt_value)
            elif isinstance(dt_value, datetime):
                return dt_value
            return None
        
        return cls(
            session_id=data.get('session_id', ''),
            user_id=data.get('user_id'),
            username=data.get('username', ''),
            login_timestamp=data.get('login_timestamp', 0),
            token_hash=data.get('token_hash', ''),
            expires_at=parse_datetime(data.get('expires_at')),
            is_active=data.get('is_active', True),
            created_at=parse_datetime(data.get('created_at'))
        )
    
    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if not self.expires_at:
            return True
        return datetime.now() > self.expires_at


@dataclass
class LoginRequest:
    """登录请求模型"""
    username: str
    password: str
    remember_me: bool = False


@dataclass
class LoginResponse:
    """登录响应模型"""
    success: bool
    message: str
    session_id: Optional[str] = None
    username: Optional[str] = None
    expires_at: Optional[str] = None
    user_info: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'success': self.success,
            'message': self.message,
            'data': {
                'session_id': self.session_id,
                'username': self.username,
                'expires_at': self.expires_at,
                'user': self.user_info,
                'token': self.session_id  # 前端期望的token字段
            } if self.success else None
        }


@dataclass
class ChangePasswordRequest:
    """修改密码请求模型"""
    old_password: str
    new_password: str


@dataclass
class CreateUserRequest:
    """创建用户请求模型"""
    username: str
    password: str
    email: Optional[str] = None
    is_active: bool = True