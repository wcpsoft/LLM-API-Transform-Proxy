from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger


class RouteDAO:
    """路由数据访问对象"""
    
    @staticmethod
    def get_all_routes() -> List[Dict[str, Any]]:
        """获取所有路由"""
        try:
            with get_db_connection() as db:
                result = db.execute("SELECT * FROM apiroute ORDER BY id").fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取路由失败: {e}")
            raise
    
    @staticmethod
    def get_route_by_id(route_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取路由"""
        try:
            with get_db_connection() as db:
                result = db.execute("SELECT * FROM apiroute WHERE id=?", [route_id]).fetchone()
                if result:
                    columns = [desc[0] for desc in db.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"获取路由失败: {e}")
            raise
    
    @staticmethod
    def create_route(route_data: Dict[str, Any]) -> int:
        """创建路由"""
        try:
            with get_db_connection() as db:
                max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM apiroute").fetchone()[0]
                new_id = max_id + 1
                
                db.execute("""
                    INSERT INTO apiroute (id, path, method, description, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    new_id, route_data['path'], route_data['method'], 
                    route_data['description'], route_data['enabled'], 
                    datetime.now(), datetime.now()
                ])
                return new_id
        except Exception as e:
            logger.error(f"创建路由失败: {e}")
            raise
    
    @staticmethod
    def update_route(route_id: int, route_data: Dict[str, Any]) -> bool:
        """更新路由"""
        try:
            with get_db_connection() as db:
                result = db.execute("""
                    UPDATE apiroute SET path=?, method=?, description=?, enabled=?, updated_at=?
                    WHERE id=?
                """, [
                    route_data['path'], route_data['method'], 
                    route_data['description'], route_data['enabled'], 
                    datetime.now(), route_id
                ])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新路由失败: {e}")
            raise
    
    @staticmethod
    def delete_route(route_id: int) -> bool:
        """删除路由"""
        try:
            with get_db_connection() as db:
                result = db.execute("DELETE FROM apiroute WHERE id=?", [route_id])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"删除路由失败: {e}")
            raise
    
    @staticmethod
    def get_enabled_routes() -> List[Dict[str, Any]]:
        """获取启用的路由"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM apiroute WHERE enabled=true ORDER BY id"
                ).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取启用路由失败: {e}")
            raise