#!/usr/bin/env python3
"""
初始化默认数据脚本
创建默认的模型配置和API密钥配置，确保系统可以正常使用
"""

import os
import sys
from datetime import datetime
from src.utils.db import init_db, get_db_connection
from src.service.system_config_service import SystemConfigService
from src.utils.logging import logger

def init_default_models():
    """初始化默认模型配置"""
    print("\n=== 初始化默认模型配置 ===")
    
    default_models = [
        {
            "route_key": "chat",
            "target_model": "gpt-3.5-turbo",
            "provider": "openai",
            "prompt_keywords": "chat,对话,聊天",
            "description": "OpenAI GPT-3.5 Turbo 模型，适用于日常对话",
            "enabled": True,
            "api_key": None
        },
        {
            "route_key": "gpt-4",
            "target_model": "gpt-4",
            "provider": "openai",
            "prompt_keywords": "gpt-4,高级,复杂",
            "description": "OpenAI GPT-4 模型，适用于复杂任务",
            "enabled": True,
            "api_key": None
        },
        {
            "route_key": "claude",
            "target_model": "claude-3-sonnet-20240229",
            "provider": "anthropic",
            "prompt_keywords": "claude,anthropic,分析",
            "description": "Anthropic Claude 3 Sonnet 模型，适用于分析任务",
            "enabled": True,
            "api_key": None
        },
        {
            "route_key": "gemini",
            "target_model": "gemini-pro",
            "provider": "gemini",
            "prompt_keywords": "gemini,google,多模态",
            "description": "Google Gemini Pro 模型，支持多模态",
            "enabled": True,
            "api_key": None
        },
        {
            "route_key": "deepseek",
            "target_model": "deepseek-chat",
            "provider": "deepseek",
            "prompt_keywords": "deepseek,推理,分析",
            "description": "DeepSeek V3 模型，适用于推理和分析任务",
            "enabled": True,
            "api_key": None
        },
        {
            "route_key": "deepseek-reasoner",
            "target_model": "deepseek-reasoner",
            "provider": "deepseek",
            "prompt_keywords": "claude-4,推理,复杂分析",
            "description": "DeepSeek R1 模型，适用于复杂推理任务",
            "enabled": True,
            "api_key": None
        }
    ]
    
    try:
        with get_db_connection() as db:
            # 检查是否已有模型配置
            existing_count = db.execute("SELECT COUNT(*) FROM modelconfig").fetchone()[0]
            if existing_count > 0:
                print(f"已存在 {existing_count} 个模型配置，跳过初始化")
                return
            
            # 创建默认模型配置
            for i, model_data in enumerate(default_models, 1):
                try:
                    db.execute("""
                        INSERT INTO modelconfig 
                        (id, route_key, target_model, provider, prompt_keywords, description, enabled, api_key)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        i, model_data['route_key'], model_data['target_model'], 
                        model_data['provider'], model_data['prompt_keywords'], 
                        model_data['description'], model_data['enabled'], 
                        model_data['api_key']
                    ])
                    print(f"✅ 创建模型配置: {model_data['route_key']} -> {model_data['target_model']}")
                except Exception as e:
                    print(f"❌ 创建模型配置失败 {model_data['route_key']}: {e}")
        
        print(f"默认模型配置初始化完成")
        
    except Exception as e:
        print(f"❌ 初始化默认模型配置失败: {e}")

def init_demo_api_keys():
    """初始化演示用的API密钥配置"""
    print("\n=== 初始化演示API密钥 ===")
    
    demo_keys = [
        {
            "provider": "openai",
            "api_key": "sk-demo-openai-key-replace-with-real-key",
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}",
            "is_active": False
        },
        {
            "provider": "anthropic",
            "api_key": "sk-ant-demo-anthropic-key-replace-with-real-key",
            "auth_header": "x-api-key",
            "auth_format": "{key}",
            "is_active": False
        },
        {
            "provider": "gemini",
            "api_key": "demo-gemini-key-replace-with-real-key",
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}",
            "is_active": False
        },
        {
            "provider": "deepseek",
            "api_key": "sk-demo-deepseek-key-replace-with-real-key",
            "auth_header": "Authorization",
            "auth_format": "Bearer {key}",
            "is_active": False
        }
    ]
    
    try:
        with get_db_connection() as db:
            # 检查是否已有API密钥
            existing_count = db.execute("SELECT COUNT(*) FROM api_key_pool").fetchone()[0]
            if existing_count > 0:
                print(f"已存在 {existing_count} 个API密钥，跳过初始化")
                return
            
            # 创建演示API密钥
            for i, key_data in enumerate(demo_keys, 1):
                try:
                    db.execute("""
                        INSERT INTO api_key_pool 
                        (id, provider, api_key, auth_header, auth_format, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        i, key_data['provider'], key_data['api_key'],
                        key_data['auth_header'], key_data['auth_format'], key_data['is_active'],
                        datetime.now(), datetime.now()
                    ])
                    print(f"✅ 创建演示密钥: {key_data['provider']} (未激活)")
                except Exception as e:
                    print(f"❌ 创建演示密钥失败 {key_data['provider']}: {e}")
        
        print("演示API密钥初始化完成")
        print("⚠️  请在管理界面中配置真实的API密钥并激活")
        
    except Exception as e:
        print(f"❌ 初始化演示API密钥失败: {e}")

def init_system_configs():
    """初始化系统配置"""
    print("\n=== 初始化系统配置 ===")
    
    default_configs = [
        ("auth.admin_key", "admin123", "管理API认证密钥"),
        ("server.host", "0.0.0.0", "服务器主机地址"),
        ("server.port", "8082", "服务器端口"),
        ("server.debug", "false", "调试模式"),
        ("service.discovery_enabled", "true", "服务发现启用状态"),
        ("logging.level", "INFO", "日志级别"),
        ("logging.structured", "true", "结构化日志")
    ]
    
    try:
        config_service = SystemConfigService()
        
        for key, value, description in default_configs:
            try:
                existing = config_service.get_config_value(key)
                if existing is None:
                    config_service.set_config_value(key, value, description)
                    print(f"✅ 设置配置: {key} = {value}")
                else:
                    print(f"⏭️  配置已存在: {key} = {existing}")
            except Exception as e:
                print(f"❌ 设置配置失败 {key}: {e}")
        
        print("系统配置初始化完成")
        
    except Exception as e:
        print(f"❌ 初始化系统配置失败: {e}")

def show_usage_info():
    """显示使用说明"""
    print("\n=== 使用说明 ===")
    print("1. 启动服务器:")
    print("   python -m src.main")
    print("")
    print("2. 访问管理界面:")
    print("   http://localhost:8082/v1/admin/models?admin_key=admin123")
    print("")
    print("3. 配置真实API密钥:")
    print("   - 在API密钥管理页面替换演示密钥")
    print("   - 激活需要使用的密钥")
    print("")
    print("4. 测试API调用:")
    print("   curl -X POST http://localhost:8082/v1/chat/completions \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"model\": \"gpt-3.5-turbo\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'")
    print("")
    print("5. 前端开发:")
    print("   cd web && npm install && npm run dev")

def main():
    """主函数"""
    print("Claude Code Proxy - 默认数据初始化")
    print("=" * 50)
    
    try:
        # 初始化数据库
        print("初始化数据库...")
        init_db()
        print("✅ 数据库初始化完成")
        
        # 初始化各种默认数据
        init_system_configs()
        init_default_models()
        init_demo_api_keys()
        
        print("\n🎉 默认数据初始化完成！")
        show_usage_info()
        
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()