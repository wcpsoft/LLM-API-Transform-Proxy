from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger


class ModelDAO:
    """模型配置数据访问对象"""
    
    @staticmethod
    def get_all_models() -> List[Dict[str, Any]]:
        """获取所有模型配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("SELECT * FROM modelconfig ORDER BY id").fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            raise
    
    @staticmethod
    def get_model_by_id(model_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取模型配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("SELECT * FROM modelconfig WHERE id=?", [model_id]).fetchone()
                if result:
                    columns = [desc[0] for desc in db.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            raise
    
    @staticmethod
    def create_model(model_data: Dict[str, Any]) -> int:
        """创建模型配置"""
        try:
            with get_db_connection() as db:
                max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM modelconfig").fetchone()[0]
                new_id = max_id + 1
                
                db.execute("""
                    INSERT INTO modelconfig 
                    (id, route_key, target_model, provider, prompt_keywords, description, 
                     enabled, api_key, api_base, auth_header, auth_format, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    new_id, model_data['route_key'], model_data['target_model'], 
                    model_data['provider'], model_data['prompt_keywords'], 
                    model_data['description'], model_data['enabled'], 
                    model_data['api_key'], model_data['api_base'], 
                    model_data['auth_header'], model_data['auth_format'], 
                    datetime.now(), datetime.now()
                ])
                return new_id
        except Exception as e:
            logger.error(f"创建模型配置失败: {e}")
            raise
    
    @staticmethod
    def update_model(model_id: int, model_data: Dict[str, Any]) -> bool:
        """更新模型配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("""
                    UPDATE modelconfig SET 
                    route_key=?, target_model=?, provider=?, prompt_keywords=?, 
                    description=?, enabled=?, api_key=?, api_base=?, 
                    auth_header=?, auth_format=?, updated_at=?
                    WHERE id=?
                """, [
                    model_data['route_key'], model_data['target_model'], 
                    model_data['provider'], model_data['prompt_keywords'], 
                    model_data['description'], model_data['enabled'], 
                    model_data['api_key'], model_data['api_base'], 
                    model_data['auth_header'], model_data['auth_format'], 
                    datetime.now(), model_id
                ])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新模型配置失败: {e}")
            raise
    
    @staticmethod
    def delete_model(model_id: int) -> bool:
        """删除模型配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("DELETE FROM modelconfig WHERE id=?", [model_id])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"删除模型配置失败: {e}")
            raise
    
    @staticmethod
    def get_models_by_route_key(route_key: str) -> List[Dict[str, Any]]:
        """根据路由键获取模型配置"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM modelconfig WHERE route_key=? AND enabled=true ORDER BY id", 
                    [route_key]
                ).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取路由模型配置失败: {e}")
            raise