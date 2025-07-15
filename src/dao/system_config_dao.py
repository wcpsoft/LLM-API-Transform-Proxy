from datetime import datetime
from typing import List, Optional, Dict, Any
import duckdb
from src.utils.db import get_db_connection
from src.utils.logging import logger


class SystemConfigDAO:
    """系统配置数据访问对象"""
    
    @staticmethod
    def get_all_configs() -> List[Dict[str, Any]]:
        """获取所有系统配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("SELECT * FROM system_config ORDER BY config_key").fetchall()
                columns = [desc[0] for desc in db.description]
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            raise
    
    @staticmethod
    def get_config_by_key(config_key: str) -> Optional[Dict[str, Any]]:
        """根据键获取系统配置"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "SELECT * FROM system_config WHERE config_key=?", 
                    [config_key]
                ).fetchone()
                if result:
                    columns = [desc[0] for desc in db.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            raise
    
    @staticmethod
    def get_config_value(config_key: str, default_value: Any = None) -> Any:
        """获取配置值"""
        try:
            config = SystemConfigDAO.get_config_by_key(config_key)
            if config:
                config_type = config.get('config_type', 'string')
                config_value = config.get('config_value')
                
                if config_type == 'boolean':
                    return config_value.lower() in ('true', '1', 'yes', 'on') if isinstance(config_value, str) else bool(config_value)
                elif config_type == 'integer':
                    return int(config_value)
                elif config_type == 'float':
                    return float(config_value)
                elif config_type == 'json':
                    import json
                    return json.loads(config_value) if isinstance(config_value, str) else config_value
                else:
                    return config_value
            return default_value
        except Exception as e:
            logger.error(f"获取配置值失败: {e}")
            return default_value
    
    @staticmethod
    def create_config(config_data: Dict[str, Any]) -> bool:
        """创建系统配置"""
        try:
            with get_db_connection() as db:
                db.execute("""
                    INSERT INTO system_config 
                    (config_key, config_value, config_type, description, is_sensitive, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    config_data['config_key'], config_data['config_value'], 
                    config_data.get('config_type', 'string'), 
                    config_data.get('description', ''), 
                    config_data.get('is_sensitive', False),
                    datetime.now(), datetime.now()
                ])
                return True
        except Exception as e:
            logger.error(f"创建系统配置失败: {e}")
            raise
    
    @staticmethod
    def update_config(config_key: str, config_value: str) -> bool:
        """更新系统配置"""
        try:
            with get_db_connection() as db:
                result = db.execute(
                    "UPDATE system_config SET config_value=?, updated_at=? WHERE config_key=?",
                    [config_value, datetime.now(), config_key]
                )
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新系统配置失败: {e}")
            raise
    
    @staticmethod
    def delete_config(config_key: str) -> bool:
        """删除系统配置"""
        try:
            with get_db_connection() as db:
                result = db.execute("DELETE FROM system_config WHERE config_key=?", [config_key])
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"删除系统配置失败: {e}")
            raise
    
    @staticmethod
    def init_default_configs() -> None:
        """初始化默认系统配置"""
        default_configs = [
            {
                'config_key': 'server_host',
                'config_value': '0.0.0.0',
                'config_type': 'string',
                'description': '服务器监听主机地址',
                'is_sensitive': False
            },
            {
                'config_key': 'server_port',
                'config_value': '8082',
                'config_type': 'integer',
                'description': '服务器监听端口',
                'is_sensitive': False
            },
            {
                'config_key': 'debug_mode',
                'config_value': 'false',
                'config_type': 'boolean',
                'description': '调试模式开关',
                'is_sensitive': False
            },
            {
                'config_key': 'admin_auth_key',
                'config_value': 'your-secret-admin-key',
                'config_type': 'string',
                'description': '管理API认证密钥',
                'is_sensitive': True
            },
            {
                'config_key': 'web_port',
                'config_value': '8080',
                'config_type': 'integer',
                'description': 'Web界面端口',
                'is_sensitive': False
            },
            {
                'config_key': 'service_discovery',
                'config_value': 'true',
                'config_type': 'boolean',
                'description': '服务发现功能开关',
                'is_sensitive': False
            },
            {
                'config_key': 'structured_logging',
                'config_value': 'false',
                'config_type': 'boolean',
                'description': '结构化日志开关',
                'is_sensitive': False
            },
            {
                'config_key': 'log_level',
                'config_value': 'INFO',
                'config_type': 'string',
                'description': '日志级别',
                'is_sensitive': False
            }
        ]
        
        try:
            for config in default_configs:
                existing = SystemConfigDAO.get_config_by_key(config['config_key'])
                if not existing:
                    SystemConfigDAO.create_config(config)
                    logger.info(f"初始化默认配置: {config['config_key']}")
        except Exception as e:
            logger.error(f"初始化默认配置失败: {e}")
            raise