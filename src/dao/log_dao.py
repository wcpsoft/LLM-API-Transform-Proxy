from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger


class LogDAO:
    """日志数据访问对象"""
    
    @staticmethod
    def create_request_log(
        source_api: str,
        target_api: str,
        source_model: str = None,
        target_model: str = None,
        request_headers: str = None,
        request_body: str = None,
        response_body: str = None,
        status_code: int = None,
        error_message: str = None,
        processing_time: float = None
    ) -> None:
        """创建请求日志"""
        try:
            with get_db_connection() as db:
                # 首先检查表结构并添加缺失的列
                try:
                    db.execute("ALTER TABLE apirequestlog ADD COLUMN status_code INTEGER")
                except:
                    pass  # 列已存在
                try:
                    db.execute("ALTER TABLE apirequestlog ADD COLUMN error_message VARCHAR")
                except:
                    pass  # 列已存在
                try:
                    db.execute("ALTER TABLE apirequestlog ADD COLUMN processing_time DOUBLE")
                except:
                    pass  # 列已存在
                try:
                    db.execute("ALTER TABLE apirequestlog ADD COLUMN provider VARCHAR")
                except:
                    pass  # 列已存在
                
                db.execute("""
                    INSERT INTO apirequestlog 
                    (timestamp, source_api, target_api, source_model, target_model, 
                     headers, source_prompt, target_response, status_code, error_message, processing_time, provider)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    datetime.now(),
                    source_api,
                    target_api,
                    source_model,
                    target_model,
                    request_headers,
                    request_body,
                    response_body,
                    status_code,
                    error_message,
                    processing_time,
                    target_model.split('/')[0] if target_model and '/' in target_model else 'unknown'
                ])
        except Exception as e:
            logger.error(f"创建请求日志失败: {e}")
            raise
    
    @staticmethod
    def get_logs_paginated(
        page: int = 1, 
        size: int = 20,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        source_api: Optional[str] = None,
        target_api: Optional[str] = None,
        source_model: Optional[str] = None,
        target_model: Optional[str] = None,
        status_code: Optional[int] = None,
        error_only: bool = False
    ) -> Dict[str, Any]:
        """分页获取日志"""
        try:
            with get_db_connection() as db:
                # 构建查询条件
                conditions = []
                params = []
                
                if start_time:
                    conditions.append("timestamp >= ?")
                    params.append(start_time)
                if end_time:
                    conditions.append("timestamp <= ?")
                    params.append(end_time)
                if source_api:
                    conditions.append("source_api LIKE ?")
                    params.append(f"%{source_api}%")
                if target_api:
                    conditions.append("target_api LIKE ?")
                    params.append(f"%{target_api}%")
                if source_model:
                    conditions.append("source_model LIKE ?")
                    params.append(f"%{source_model}%")
                if target_model:
                    conditions.append("target_model LIKE ?")
                    params.append(f"%{target_model}%")
                if status_code:
                    conditions.append("status_code = ?")
                    params.append(status_code)
                if error_only:
                    conditions.append("status_code >= 400")
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                # 获取总数
                count_query = f"SELECT COUNT(*) FROM apirequestlog{where_clause}"
                total = db.execute(count_query, params).fetchone()[0]
                
                # 获取分页数据
                offset = (page - 1) * size
                query = f"""
                    SELECT * FROM apirequestlog{where_clause} 
                    ORDER BY timestamp DESC 
                    LIMIT ? OFFSET ?
                """
                params.extend([size, offset])
                
                result = db.execute(query, params).fetchall()
                columns = [desc[0] for desc in db.description]
                logs = [dict(zip(columns, row)) for row in result]
                
                return {
                    "items": logs,
                    "total": total,
                    "page": page,
                    "size": size
                }
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            raise
    
    @staticmethod
    def get_daily_stats(days: int = 7) -> List[Dict[str, Any]]:
        """获取每日请求统计"""
        try:
            with get_db_connection() as db:
                result = db.execute("""
                    SELECT DATE(timestamp) as date, 
                           COUNT(*) as total_requests,
                           COUNT(CASE WHEN status_code < 400 THEN 1 END) as success_requests,
                           COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests,
                           AVG(processing_time) as avg_processing_time
                    FROM apirequestlog 
                    WHERE timestamp >= CURRENT_DATE - ? * INTERVAL '1 day'
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, [days]).fetchall()
                
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取每日统计失败: {e}")
            raise
    
    @staticmethod
    def get_model_usage_stats(days: int = 7) -> List[Dict[str, Any]]:
        """获取模型使用统计"""
        try:
            with get_db_connection() as db:
                result = db.execute("""
                    SELECT target_model, provider,
                           COUNT(*) as total_requests,
                           COUNT(CASE WHEN status_code < 400 THEN 1 END) as success_requests,
                           COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests,
                           AVG(processing_time) as avg_processing_time
                    FROM apirequestlog 
                    WHERE timestamp >= CURRENT_DATE - ? * INTERVAL '1 day'
                    GROUP BY target_model, provider
                    ORDER BY total_requests DESC
                """, [days]).fetchall()
                
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取模型统计失败: {e}")
            raise
    
    @staticmethod
    def cleanup_old_logs(days: int = 30) -> int:
        """清理旧日志"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "DELETE FROM apirequestlog WHERE timestamp < CURRENT_DATE - ? * INTERVAL '1 day'",
                    [days]
                )
                return result.rowcount
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            raise