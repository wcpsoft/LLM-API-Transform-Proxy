#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Route Service - 路由管理业务逻辑层
"""

from typing import List, Optional
from src.dao.route_dao import RouteDAO
from src.models.api_route import ApiRoute
from src.utils.logging import logger


class RouteService:
    """路由管理服务"""
    
    def __init__(self):
        self.dao = RouteDAO()
    
    def get_all_routes(self) -> List[ApiRoute]:
        """获取所有路由"""
        try:
            return self.dao.get_all_routes()
        except Exception as e:
            logger.error(f"获取所有路由失败: {e}")
            raise
    
    def get_enabled_routes(self) -> List[ApiRoute]:
        """获取启用的路由"""
        try:
            return self.dao.get_enabled_routes()
        except Exception as e:
            logger.error(f"获取启用路由失败: {e}")
            raise
    
    def get_route_by_id(self, route_id: int) -> Optional[ApiRoute]:
        """根据ID获取路由"""
        try:
            return self.dao.get_route_by_id(route_id)
        except Exception as e:
            logger.error(f"获取路由失败: {e}")
            raise
    
    def create_route(self, path: str, method: str, description: str = None, enabled: bool = True) -> ApiRoute:
        """创建路由"""
        try:
            # 验证路径格式
            if not path.startswith('/'):
                raise ValueError("路径必须以/开头")
            
            # 验证HTTP方法
            valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
            if method.upper() not in valid_methods:
                raise ValueError(f"无效的HTTP方法: {method}")
            
            route_data = {
                'path': path,
                'method': method.upper(),
                'description': description,
                'enabled': enabled
            }
            route_id = self.dao.create_route(route_data)
            return self.dao.get_route_by_id(route_id)
        except Exception as e:
            logger.error(f"创建路由失败: {e}")
            raise
    
    def update_route(self, route_id: int, **kwargs) -> Optional[ApiRoute]:
        """更新路由"""
        try:
            # 验证路径格式（如果提供）
            if 'path' in kwargs and not kwargs['path'].startswith('/'):
                raise ValueError("路径必须以/开头")
            
            # 验证HTTP方法（如果提供）
            if 'method' in kwargs:
                valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
                if kwargs['method'].upper() not in valid_methods:
                    raise ValueError(f"无效的HTTP方法: {kwargs['method']}")
                kwargs['method'] = kwargs['method'].upper()
            
            success = self.dao.update_route(route_id, kwargs)
            if success:
                return self.dao.get_route_by_id(route_id)
            return None
        except Exception as e:
            logger.error(f"更新路由失败: {e}")
            raise
    
    def delete_route(self, route_id: int) -> bool:
        """删除路由"""
        try:
            return self.dao.delete_route(route_id)
        except Exception as e:
            logger.error(f"删除路由失败: {e}")
            raise
    
    def validate_route_path(self, path: str) -> bool:
        """验证路由路径格式"""
        if not path or not isinstance(path, str):
            return False
        
        if not path.startswith('/'):
            return False
        
        # 检查是否包含非法字符
        import re
        if not re.match(r'^[a-zA-Z0-9/_-]+$', path):
            return False
        
        return True
    
    def get_route_by_path_method(self, path: str, method: str) -> Optional[ApiRoute]:
        """根据路径和方法获取路由"""
        try:
            routes = self.dao.get_all_routes()
            for route in routes:
                if route.path == path and route.method.upper() == method.upper():
                    return route
            return None
        except Exception as e:
            logger.error(f"根据路径和方法获取路由失败: {e}")
            raise