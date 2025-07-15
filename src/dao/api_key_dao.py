from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger


class ApiKeyDAO:
    """API密钥数据访问对象"""
    
    @staticmethod
    def get_all_api_keys(provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有API密钥"""
        try:
            with get_db_connection() as db:
                if provider:
                    result = db.execute(
                        "SELECT * FROM api_key_pool WHERE provider = ? ORDER BY id", 
                        [provider]
                    ).fetchall()
                else:
                    result = db.execute(
                        "SELECT * FROM api_key_pool ORDER BY provider, id"
                    ).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    @staticmethod
    def get_api_key_by_id(key_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取API密钥"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM api_key_pool WHERE id=?", 
                    [key_id]
                ).fetchone()
                if result:
                    columns = [desc[0] for desc in db.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    @staticmethod
    def create_api_key(key_data: Dict[str, Any]) -> int:
        """创建API密钥"""
        try:
            with get_db_connection() as db:
                max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM api_key_pool").fetchone()[0]
                new_id = max_id + 1
                
                db.execute("""
                    INSERT INTO api_key_pool 
                    (id, provider, api_key, auth_header, auth_format, is_active, 
                     requests_count, success_count, error_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    new_id, key_data['provider'], key_data['api_key'], 
                    key_data['auth_header'], key_data['auth_format'], 
                    key_data['is_active'], 0, 0, 0, datetime.now(), datetime.now()
                ])
                return new_id
        except Exception as e:
            logger.error(f"创建API密钥失败: {e}")
            raise
    
    @staticmethod
    def update_api_key_status(key_id: int, is_active: bool) -> bool:
        """更新API密钥状态"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "UPDATE api_key_pool SET is_active=?, updated_at=? WHERE id=?", 
                    [is_active, datetime.now(), key_id]
                )
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新API密钥状态失败: {e}")
            raise
    
    @staticmethod
    def delete_api_key(key_id: int) -> bool:
        """删除API密钥"""
        try:
            with get_db_connection() as db:
                result = db.execute("DELETE FROM api_key_pool WHERE id=?", [key_id])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"删除API密钥失败: {e}")
            raise
    
    @staticmethod
    def get_active_keys_by_provider(provider: str) -> List[Dict[str, Any]]:
        """获取指定提供商的活跃密钥"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM api_key_pool WHERE provider=? AND is_active=true ORDER BY id", 
                    [provider]
                ).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取活跃API密钥失败: {e}")
            raise
    
    @staticmethod
    def update_key_stats(key_id: int, success: bool = True) -> None:
        """更新API密钥统计信息"""
        try:
            with get_db_connection() as db:
                if success:
                    db.execute(
                        "UPDATE api_key_pool SET requests_count=requests_count+1, success_count=success_count+1, updated_at=? WHERE id=?",
                        [datetime.now(), key_id]
                    )
                else:
                    db.execute(
                        "UPDATE api_key_pool SET requests_count=requests_count+1, error_count=error_count+1, updated_at=? WHERE id=?",
                        [datetime.now(), key_id]
                    )
        except Exception as e:
            logger.error(f"更新API密钥统计失败: {e}")
            raise
    
    @staticmethod
    def get_provider_stats() -> List[Dict[str, Any]]:
        """获取提供商统计信息"""
        try:
            with get_db_connection() as db:
                result = db.execute("""
                    SELECT provider, COUNT(*) as total_keys, 
                           SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_keys,
                           SUM(requests_count) as total_requests,
                           SUM(success_count) as total_success,
                           SUM(error_count) as total_errors
                    FROM api_key_pool 
                    GROUP BY provider
                """).fetchall()
                
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取提供商统计失败: {e}")
            raise