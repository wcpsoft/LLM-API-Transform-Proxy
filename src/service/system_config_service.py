from typing import List, Optional, Dict, Any
from src.dao.system_config_dao import SystemConfigDAO
from src.utils.logging import logger


class SystemConfigService:
    """系统配置管理服务"""
    
    @staticmethod
    def get_all_configs(hide_sensitive: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有系统配置"""
        try:
            configs = SystemConfigDAO.get_all_configs()
            
            if hide_sensitive:
                for config in configs:
                    if config.get('is_sensitive'):
                        config['config_value'] = '***'
            
            return {"configs": configs}
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            raise
    
    @staticmethod
    def get_config_by_key(config_key: str) -> Optional[Dict[str, Any]]:
        """根据键获取系统配置"""
        try:
            return SystemConfigDAO.get_config_by_key(config_key)
        except Exception as e:
            logger.error(f"获取系统配置失败: {e}")
            raise
    
    @staticmethod
    def get_config_value(config_key: str, default_value: Any = None) -> Any:
        """获取配置值"""
        try:
            return SystemConfigDAO.get_config_value(config_key, default_value)
        except Exception as e:
            logger.error(f"获取配置值失败: {e}")
            return default_value
    
    @staticmethod
    def update_config(config_key: str, config_value: str) -> Dict[str, str]:
        """更新系统配置"""
        try:
            # 检查配置是否存在
            existing_config = SystemConfigDAO.get_config_by_key(config_key)
            if not existing_config:
                raise ValueError("配置项不存在")
            
            # 验证配置值
            SystemConfigService._validate_config_value(
                config_key, config_value, existing_config.get('config_type', 'string')
            )
            
            success = SystemConfigDAO.update_config(config_key, config_value)
            if not success:
                raise ValueError("更新配置失败")
            
            return {"message": "配置更新成功"}
        except Exception as e:
            logger.error(f"更新系统配置失败: {e}")
            raise
    
    @staticmethod
    def create_config(config_data: Dict[str, Any]) -> Dict[str, str]:
        """创建系统配置"""
        try:
            # 检查配置是否已存在
            existing_config = SystemConfigDAO.get_config_by_key(config_data['config_key'])
            if existing_config:
                raise ValueError(f"配置项 '{config_data['config_key']}' 已存在")
            
            # 验证配置值
            SystemConfigService._validate_config_value(
                config_data['config_key'], 
                config_data['config_value'], 
                config_data.get('config_type', 'string')
            )
            
            SystemConfigDAO.create_config(config_data)
            return {"message": "配置创建成功"}
        except Exception as e:
            logger.error(f"创建系统配置失败: {e}")
            raise
    
    @staticmethod
    def delete_config(config_key: str) -> Dict[str, str]:
        """删除系统配置"""
        try:
            # 检查是否为系统核心配置
            core_configs = [
                'server_host', 'server_port', 'debug_mode', 'admin_auth_key',
                'web_port', 'service_discovery', 'structured_logging', 'log_level'
            ]
            
            if config_key in core_configs:
                raise ValueError(f"不能删除系统核心配置: {config_key}")
            
            success = SystemConfigDAO.delete_config(config_key)
            if not success:
                raise ValueError("配置项不存在")
            
            return {"message": "配置删除成功"}
        except Exception as e:
            logger.error(f"删除系统配置失败: {e}")
            raise
    
    @staticmethod
    def init_default_configs() -> None:
        """初始化默认系统配置"""
        try:
            SystemConfigDAO.init_default_configs()
            logger.info("默认系统配置初始化完成")
        except Exception as e:
            logger.error(f"初始化默认配置失败: {e}")
            raise
    
    @staticmethod
    def _validate_config_value(config_key: str, config_value: str, config_type: str) -> None:
        """验证配置值"""
        try:
            if config_type == 'boolean':
                valid_values = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']
                if config_value.lower() not in valid_values:
                    raise ValueError(f"布尔类型配置值无效: {config_value}")
            
            elif config_type == 'integer':
                try:
                    int(config_value)
                except ValueError:
                    raise ValueError(f"整数类型配置值无效: {config_value}")
            
            elif config_type == 'float':
                try:
                    float(config_value)
                except ValueError:
                    raise ValueError(f"浮点数类型配置值无效: {config_value}")
            
            elif config_type == 'json':
                try:
                    import json
                    json.loads(config_value)
                except json.JSONDecodeError:
                    raise ValueError(f"JSON类型配置值无效: {config_value}")
            
            # 特定配置项的验证
            if config_key == 'server_port' or config_key == 'web_port':
                port = int(config_value)
                if port < 1 or port > 65535:
                    raise ValueError(f"端口号必须在1-65535之间: {port}")
            
            elif config_key == 'log_level':
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if config_value.upper() not in valid_levels:
                    raise ValueError(f"日志级别无效: {config_value}")
            
        except Exception as e:
            logger.error(f"配置值验证失败: {e}")
            raise
    
    @staticmethod
    def get_server_config() -> Dict[str, Any]:
        """获取服务器配置"""
        try:
            return {
                'host': SystemConfigService.get_config_value('server_host', '0.0.0.0'),
                'port': SystemConfigService.get_config_value('server_port', 8082),
                'debug': SystemConfigService.get_config_value('debug_mode', False),
                'web_port': SystemConfigService.get_config_value('web_port', 8080),
                'service_discovery': SystemConfigService.get_config_value('service_discovery', True),
                'structured_logging': SystemConfigService.get_config_value('structured_logging', False),
                'log_level': SystemConfigService.get_config_value('log_level', 'INFO')
            }
        except Exception as e:
            logger.error(f"获取服务器配置失败: {e}")
            raise
    
    @staticmethod
    def get_admin_auth_key() -> str:
        """获取管理认证密钥"""
        try:
            return SystemConfigService.get_config_value('admin_auth_key', 'your-secret-admin-key')
        except Exception as e:
            logger.error(f"获取管理认证密钥失败: {e}")
            return 'your-secret-admin-key'