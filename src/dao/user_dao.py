"""用户数据访问层"""

from datetime import datetime, timedelta
from typing import List, Optional

from src.models.user import User, UserSession
from src.utils.db import get_db_connection
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserDAO:
    """用户数据访问对象"""
    
    @staticmethod
    def create_user(user: User) -> Optional[int]:
        """创建用户
        
        Args:
            user: 用户对象
            
        Returns:
            创建的用户ID，失败返回None
        """
        try:
            with get_db_connection() as db:
                # 获取下一个ID
                result = db.execute("SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM users").fetchone()
                next_id = result[0] if result else 1
                
                db.execute(
                    """
                    INSERT INTO users (id, username, password_hash, email, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        next_id,
                        user.username,
                        user.password_hash,
                        user.email,
                        user.is_active,
                        datetime.now(),
                        datetime.now()
                    ]
                )
                return next_id
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户对象，不存在返回None
        """
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM users WHERE id = ?",
                    [user_id]
                ).fetchone()
                
                if result:
                    columns = [desc[0] for desc in db.description]
                    user_data = dict(zip(columns, result))
                    return User.from_dict(user_data)
                return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户对象，不存在返回None
        """
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM users WHERE username = ?",
                    [username]
                ).fetchone()
                
                if result:
                    columns = [desc[0] for desc in db.description]
                    user_data = dict(zip(columns, result))
                    return User.from_dict(user_data)
                return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None
    
    @staticmethod
    def update_user(user: User) -> bool:
        """更新用户信息
        
        Args:
            user: 用户对象
            
        Returns:
            是否更新成功
        """
        try:
            with get_db_connection() as db:
                db.execute(
                    """
                    UPDATE users 
                    SET username = ?, password_hash = ?, email = ?, is_active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    [
                        user.username,
                        user.password_hash,
                        user.email,
                        user.is_active,
                        datetime.now(),
                        user.id
                    ]
                )
                return True
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            with get_db_connection() as db:
                db.execute("DELETE FROM users WHERE id = ?", [user_id])
                return True
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            return False
    
    @staticmethod
    def get_all_users() -> List[User]:
        """获取所有用户
        
        Returns:
            用户列表
        """
        try:
            with get_db_connection() as db:
                results = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
                columns = [desc[0] for desc in db.description]
                
                users = []
                for result in results:
                    user_data = dict(zip(columns, result))
                    users.append(User.from_dict(user_data))
                return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []


class SessionDAO:
    """会话数据访问对象"""
    
    @staticmethod
    def create_session(session: UserSession) -> bool:
        """创建会话
        
        Args:
            session: 会话对象
            
        Returns:
            是否创建成功
        """
        try:
            with get_db_connection() as db:
                db.execute(
                    """
                    INSERT INTO user_sessions 
                    (session_id, user_id, username, login_timestamp, token_hash, expires_at, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        session.session_id,
                        session.user_id,
                        session.username,
                        session.login_timestamp,
                        session.token_hash,
                        session.expires_at,
                        session.is_active,
                        datetime.now()
                    ]
                )
                return True
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return False
    
    @staticmethod
    def get_session_by_id(session_id: str) -> Optional[UserSession]:
        """根据session ID获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话对象，不存在返回None
        """
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM user_sessions WHERE session_id = ? AND is_active = true",
                    [session_id]
                ).fetchone()
                
                if result:
                    columns = [desc[0] for desc in db.description]
                    session_data = dict(zip(columns, result))
                    return UserSession.from_dict(session_data)
                return None
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None
    
    @staticmethod
    def get_user_sessions(user_id: int) -> List[UserSession]:
        """获取用户的所有会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话列表
        """
        try:
            with get_db_connection() as db:
                results = db.execute(
                    "SELECT * FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC",
                    [user_id]
                ).fetchall()
                columns = [desc[0] for desc in db.description]
                
                sessions = []
                for result in results:
                    session_data = dict(zip(columns, result))
                    sessions.append(UserSession.from_dict(session_data))
                return sessions
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return []
    
    @staticmethod
    def update_session(session: UserSession) -> bool:
        """更新会话
        
        Args:
            session: 会话对象
            
        Returns:
            是否更新成功
        """
        try:
            with get_db_connection() as db:
                db.execute(
                    """
                    UPDATE user_sessions 
                    SET expires_at = ?, is_active = ?
                    WHERE session_id = ?
                    """,
                    [session.expires_at, session.is_active, session.session_id]
                )
                return True
        except Exception as e:
            logger.error(f"更新会话失败: {e}")
            return False
    
    @staticmethod
    def deactivate_session(session_id: str) -> bool:
        """停用会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否停用成功
        """
        try:
            with get_db_connection() as db:
                db.execute(
                    "UPDATE user_sessions SET is_active = false WHERE session_id = ?",
                    [session_id]
                )
                return True
        except Exception as e:
            logger.error(f"停用会话失败: {e}")
            return False
    
    @staticmethod
    def deactivate_user_sessions(user_id: int, exclude_session_id: Optional[str] = None) -> bool:
        """停用用户的所有会话（可排除指定会话）
        
        Args:
            user_id: 用户ID
            exclude_session_id: 要排除的会话ID
            
        Returns:
            是否停用成功
        """
        try:
            with get_db_connection() as db:
                if exclude_session_id:
                    db.execute(
                        "UPDATE user_sessions SET is_active = false WHERE user_id = ? AND session_id != ?",
                        [user_id, exclude_session_id]
                    )
                else:
                    db.execute(
                        "UPDATE user_sessions SET is_active = false WHERE user_id = ?",
                        [user_id]
                    )
                return True
        except Exception as e:
            logger.error(f"停用用户会话失败: {e}")
            return False
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """清理过期会话
        
        Returns:
            清理的会话数量
        """
        try:
            with get_db_connection() as db:
                cursor = db.execute(
                    "UPDATE user_sessions SET is_active = false WHERE expires_at < ? AND is_active = true",
                    [datetime.now()]
                )
                return cursor.rowcount
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0