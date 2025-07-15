# 数据库连接和初始化工具
# 注意：DuckDB不支持SQLModel/SQLAlchemy自动建表，只能用手动SQL建表

import os
from contextlib import contextmanager
from src.config import get_db_config
import duckdb
from src.utils.logging import logger

db_conf = get_db_config()
db_path = db_conf.get("path", "api_log.duckdb")


@contextmanager
def get_db_connection():
    """获取数据库连接的上下文管理器"""
    conn = None
    try:
        conn = duckdb.connect(db_path)
        yield conn
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_db():
    """FastAPI依赖注入用的数据库连接"""
    conn = None
    try:
        conn = duckdb.connect(db_path)
        yield conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()



def init_db():
    """初始化数据库"""
    from src.utils.init_db_sql import create_tables_sql
    with get_db_connection() as conn:
        try:
            # 执行建表SQL
            for sql in create_tables_sql:
                conn.execute(sql)
            logger.info(f"数据库初始化完成: {db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise


def init_default_system_configs():
    """初始化默认系统配置"""
    from src.dao.system_config_dao import SystemConfigDAO
    
    default_configs = [
        {"config_key": "server.host", "config_value": "0.0.0.0", "description": "API服务器主机地址"},
        {"config_key": "server.port", "config_value": "8082", "config_type": "int", "description": "API服务器端口"},
        {"config_key": "server.debug", "config_value": "false", "config_type": "bool", "description": "调试模式"},
        {"config_key": "auth.admin_key", "config_value": "", "description": "管理API认证密钥", "is_sensitive": True},
        {"config_key": "web.port", "config_value": "3000", "config_type": "int", "description": "Web管理界面端口"},
        {"config_key": "service.discovery_enabled", "config_value": "true", "config_type": "bool", "description": "启用服务发现"},
        {"config_key": "logging.structured", "config_value": "true", "config_type": "bool", "description": "启用结构化日志"},
        {"config_key": "logging.level", "config_value": "INFO", "description": "日志级别"},
    ]
    
    dao = SystemConfigDAO()
    for config in default_configs:
        existing = dao.get_config_by_key(config["config_key"])
        if not existing:
            dao.create_config(config)
            logger.info(f"初始化默认配置: {config['config_key']}")