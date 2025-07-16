#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化管理员用户脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.db import init_db
from src.service.user_auth_service import UserAuthService
from src.models.user import CreateUserRequest
from src.utils.logging import logger

def init_admin_user():
    """初始化管理员用户"""
    try:
        # 初始化数据库
        init_db()
        logger.info("数据库初始化完成")
        
        # 创建认证服务实例
        auth_service = UserAuthService()
        
        # 检查是否已存在管理员用户
        existing_admin = auth_service.user_dao.get_user_by_username("admin")
        if existing_admin:
            logger.info("管理员用户已存在，跳过创建")
            print("管理员用户已存在")
            return
        
        # 创建管理员用户
        admin_request = CreateUserRequest(
            username="admin",
            password="admin123",
            email="admin@example.com",
            is_active=True
        )
        
        success, message, user = auth_service.create_user(admin_request)
        
        if success:
            logger.info("管理员用户创建成功")
            print("管理员用户创建成功！")
            print("用户名: admin")
            print("密码: admin123")
            print("请登录后及时修改密码")
        else:
            logger.error(f"管理员用户创建失败: {message}")
            print(f"管理员用户创建失败: {message}")
            
    except Exception as e:
        logger.error(f"初始化管理员用户异常: {e}")
        print(f"初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_admin_user()