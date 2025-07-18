from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger
from src.utils.crypto import ApiKeyEncryption


class ApiKeyDAO:
    """API密钥数据访问对象"""
    
    def __init__(self):
        self._encryption = ApiKeyEncryption()
    
    def get_all_api_keys(self, provider: Optional[str] = None, decrypt_keys: bool = False) -> List[Dict[str, Any]]:
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
                keys = [dict(zip(columns, row)) for row in result]
                
                # 处理API密钥的显示
                for key in keys:
                    if decrypt_keys:
                        # 只有在明确需要时才解密
                        try:
                            key['api_key'] = self._encryption.decrypt_key(key['api_key'])
                        except:
                            # 如果解密失败，可能是未加密的旧数据
                            pass
                    else:
                        # 默认遮蔽密钥
                        key['api_key'] = self._encryption.mask_key(key['api_key'])
                
                return keys
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    def get_api_key_by_id(self, key_id: int, decrypt_key: bool = False) -> Optional[Dict[str, Any]]:
        """根据ID获取API密钥"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM api_key_pool WHERE id=?", 
                    [key_id]
                ).fetchone()
                if result:
                    columns = [desc[0] for desc in db.description]
                    key_data = dict(zip(columns, result))
                    
                    # 处理API密钥显示
                    if decrypt_key:
                        try:
                            key_data['api_key'] = self._encryption.decrypt_key(key_data['api_key'])
                        except:
                            # 如果解密失败，可能是未加密的旧数据
                            pass
                    else:
                        key_data['api_key'] = self._encryption.mask_key(key_data['api_key'])
                    
                    return key_data
                return None
        except Exception as e:
            logger.error(f"获取API密钥失败: {e}")
            raise
    
    def create_api_key(self, key_data: Dict[str, Any]) -> int:
        """创建API密钥"""
        try:
            # 验证密钥强度
            is_valid, error_msg = self._encryption.validate_key_strength(key_data['api_key'])
            if not is_valid:
                raise ValueError(error_msg)
            
            # 加密API密钥
            encrypted_key = self._encryption.encrypt_key(key_data['api_key'])
            
            with get_db_connection() as db:
                max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM api_key_pool").fetchone()[0]
                new_id = max_id + 1
                
                db.execute("""
                    INSERT INTO api_key_pool 
                    (id, provider, api_key, auth_header, auth_format, is_active, 
                     requests_count, success_count, error_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    new_id, key_data['provider'], encrypted_key, 
                    key_data['auth_header'], key_data['auth_format'], 
                    key_data['is_active'], 0, 0, 0, datetime.now(), datetime.now()
                ])
                
                logger.info(f"创建API密钥成功: provider={key_data['provider']}, key_id={new_id}")
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
    def update_key_stats(key_id: int, success: bool = True, usage_data: Optional[Dict[str, Any]] = None) -> None:
        """更新API密钥统计信息
        
        Args:
            key_id: API密钥ID
            success: 请求是否成功
            usage_data: 使用数据，包含tokens、延迟等信息
        """
        try:
            with get_db_connection() as db:
                # Check if the enhanced metrics columns exist
                try:
                    db.execute("SELECT total_tokens FROM api_key_pool LIMIT 1")
                    has_enhanced_metrics = True
                except:
                    has_enhanced_metrics = False
                    # Create enhanced metrics columns if they don't exist
                    db.execute("""
                        ALTER TABLE api_key_pool 
                        ADD COLUMN total_tokens INTEGER DEFAULT 0,
                        ADD COLUMN input_tokens INTEGER DEFAULT 0,
                        ADD COLUMN output_tokens INTEGER DEFAULT 0,
                        ADD COLUMN avg_latency REAL DEFAULT 0.0,
                        ADD COLUMN cost REAL DEFAULT 0.0,
                        ADD COLUMN last_error TEXT,
                        ADD COLUMN consecutive_errors INTEGER DEFAULT 0,
                        ADD COLUMN last_rotation TIMESTAMP,
                        ADD COLUMN requests_at_last_rotation INTEGER DEFAULT 0
                    """)
                    logger.info("Enhanced API key metrics columns added to database")
                
                # Build the update query based on available data
                update_fields = []
                params = []
                
                # Basic stats
                if success:
                    update_fields.extend([
                        "requests_count=requests_count+1", 
                        "success_count=success_count+1",
                        "consecutive_errors=0"
                    ])
                else:
                    update_fields.extend([
                        "requests_count=requests_count+1", 
                        "error_count=error_count+1",
                        "consecutive_errors=consecutive_errors+1"
                    ])
                    
                    # Add error message if available
                    if usage_data and 'error' in usage_data:
                        error_msg = str(usage_data['error'])[:255]  # Limit length
                        update_fields.append("last_error=?")
                        params.append(error_msg)
                
                # Enhanced metrics if available
                if usage_data and has_enhanced_metrics:
                    if 'total_tokens' in usage_data:
                        update_fields.append("total_tokens=total_tokens+?")
                        params.append(usage_data['total_tokens'])
                    
                    if 'input_tokens' in usage_data:
                        update_fields.append("input_tokens=input_tokens+?")
                        params.append(usage_data['input_tokens'])
                    
                    if 'output_tokens' in usage_data:
                        update_fields.append("output_tokens=output_tokens+?")
                        params.append(usage_data['output_tokens'])
                    
                    if 'latency' in usage_data:
                        # Use exponential moving average for latency
                        update_fields.append("""
                            avg_latency=CASE 
                                WHEN avg_latency = 0 THEN ? 
                                ELSE avg_latency * 0.9 + ? * 0.1 
                            END
                        """)
                        params.extend([usage_data['latency'], usage_data['latency']])
                    
                    if 'cost' in usage_data:
                        update_fields.append("cost=cost+?")
                        params.append(usage_data['cost'])
                
                # Add timestamp and key_id
                update_fields.append("updated_at=?")
                params.append(datetime.now())
                params.append(key_id)
                
                # Execute the update
                query = f"UPDATE api_key_pool SET {', '.join(update_fields)} WHERE id=?"
                db.execute(query, params)
                
        except Exception as e:
            logger.error(f"更新API密钥统计失败: {e}")
            raise
    
    @staticmethod
    def get_provider_stats() -> List[Dict[str, Any]]:
        """获取提供商统计信息"""
        try:
            with get_db_connection() as db:
                # Check if enhanced metrics columns exist
                try:
                    db.execute("SELECT total_tokens FROM api_key_pool LIMIT 1")
                    has_enhanced_metrics = True
                except:
                    has_enhanced_metrics = False
                
                # Build query based on available columns
                base_query = """
                    SELECT provider, COUNT(*) as total_keys, 
                           SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_keys,
                           SUM(requests_count) as total_requests,
                           SUM(success_count) as total_success,
                           SUM(error_count) as total_errors
                """
                
                # Add enhanced metrics if available
                if has_enhanced_metrics:
                    enhanced_metrics = """
                           , SUM(total_tokens) as total_tokens,
                           SUM(input_tokens) as input_tokens,
                           SUM(output_tokens) as output_tokens,
                           AVG(avg_latency) as avg_latency,
                           SUM(cost) as total_cost
                    """
                    base_query += enhanced_metrics
                
                base_query += " FROM api_key_pool GROUP BY provider"
                
                result = db.execute(base_query).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取提供商统计失败: {e}")
            raise
            
    @staticmethod
    def get_detailed_key_metrics(key_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取详细的API密钥指标
        
        Args:
            key_id: 可选的API密钥ID，如果提供则只返回该密钥的指标
            
        Returns:
            API密钥指标列表
        """
        try:
            with get_db_connection() as db:
                # Check if enhanced metrics columns exist
                try:
                    db.execute("SELECT total_tokens FROM api_key_pool LIMIT 1")
                    has_enhanced_metrics = True
                except:
                    has_enhanced_metrics = False
                
                # Build query based on available columns
                base_query = """
                    SELECT id, provider, is_active, 
                           requests_count, success_count, error_count,
                           CAST(CASE WHEN requests_count > 0 THEN 
                               (success_count * 100.0 / requests_count) 
                           ELSE 100 END AS REAL) as success_rate
                """
                
                # Add enhanced metrics if available
                if has_enhanced_metrics:
                    enhanced_metrics = """
                           , total_tokens, input_tokens, output_tokens,
                           avg_latency, cost,
                           CAST(CASE WHEN requests_count > 0 THEN 
                               (total_tokens * 1.0 / requests_count) 
                           ELSE 0 END AS REAL) as avg_tokens_per_request,
                           CAST(CASE WHEN requests_count > 0 THEN 
                               (cost * 1.0 / requests_count) 
                           ELSE 0 END AS REAL) as avg_cost_per_request,
                           last_error, consecutive_errors,
                           last_rotation, requests_at_last_rotation,
                           CAST(CASE WHEN last_rotation IS NOT NULL THEN 
                               (requests_count - requests_at_last_rotation) 
                           ELSE requests_count END AS INTEGER) as requests_since_rotation
                    """
                    base_query += enhanced_metrics
                
                base_query += " FROM api_key_pool"
                
                # Add filter for specific key if provided
                params = []
                if key_id is not None:
                    base_query += " WHERE id = ?"
                    params.append(key_id)
                
                base_query += " ORDER BY provider, id"
                
                result = db.execute(base_query, params).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取API密钥指标失败: {e}")
            raise
            
    @staticmethod
    def get_keys_needing_rotation() -> List[Dict[str, Any]]:
        """获取需要轮换的API密钥
        
        Returns:
            需要轮换的API密钥列表
        """
        try:
            with get_db_connection() as db:
                # Check if enhanced metrics columns exist
                try:
                    db.execute("SELECT consecutive_errors FROM api_key_pool LIMIT 1")
                except:
                    # If enhanced columns don't exist, we can't determine rotation needs
                    return []
                
                # Find keys that meet rotation criteria:
                # 1. High error rate (>20% errors)
                # 2. Consecutive errors (>3)
                # 3. High usage (>10000 requests since last rotation)
                # 4. Time-based (>7 days since last rotation)
                query = """
                    SELECT * FROM api_key_pool
                    WHERE is_active = true AND (
                        (requests_count > 10 AND error_count * 1.0 / requests_count > 0.2) OR
                        consecutive_errors >= 3 OR
                        (last_rotation IS NOT NULL AND 
                         requests_count - requests_at_last_rotation > 10000) OR
                        (last_rotation IS NOT NULL AND 
                         julianday('now') - julianday(last_rotation) > 7)
                    )
                    ORDER BY provider, id
                """
                
                result = db.execute(query).fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取需要轮换的API密钥失败: {e}")
            return []
            
    @staticmethod
    def rotate_api_key(old_key_id: int, new_key_id: int) -> bool:
        """轮换API密钥
        
        Args:
            old_key_id: 旧API密钥ID
            new_key_id: 新API密钥ID
            
        Returns:
            是否成功
        """
        try:
            with get_db_connection() as db:
                # Get current time
                now = datetime.now()
                
                # Update old key to inactive
                db.execute(
                    "UPDATE api_key_pool SET is_active=false, updated_at=? WHERE id=?",
                    [now, old_key_id]
                )
                
                # Update new key with rotation info
                db.execute("""
                    UPDATE api_key_pool 
                    SET last_rotation=?, requests_at_last_rotation=0, updated_at=? 
                    WHERE id=?
                """, [now, now, new_key_id])
                
                return True
        except Exception as e:
            logger.error(f"轮换API密钥失败: {e}")
            return False