#!/usr/bin/env python3
"""
Claude Code Proxy 数据库管理CLI工具
支持对模型配置、API路由、API密钥池等进行CRUD操作
"""

import click
import duckdb
import json
from datetime import datetime
from typing import List, Optional
from src.config import get_db_config
from src.models.model import ModelConfig, ApiKeyPool, ApiKeyStats
from src.models.api_route import ApiRoute
from src.models.log import ApiRequestLog

class DatabaseManager:
    def __init__(self):
        db_config = get_db_config()
        self.db_path = db_config['path']
        
    def get_connection(self):
        return duckdb.connect(self.db_path)

    # ModelConfig CRUD
    def list_model_configs(self) -> List[dict]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM modelconfig ORDER BY id").fetchall()
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row)) for row in result]
    
    def get_model_config(self, config_id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM modelconfig WHERE id = ?", [config_id]).fetchone()
            if result:
                columns = [desc[0] for desc in conn.description]
                return dict(zip(columns, result))
            return None
    
    def create_model_config(self, config: ModelConfig) -> int:
        with self.get_connection() as conn:
            # 获取下一个ID
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM modelconfig").fetchone()[0]
            new_id = max_id + 1
            
            conn.execute("""
                INSERT INTO modelconfig 
                (id, route_key, target_model, provider, prompt_keywords, description, 
                 enabled, api_key, api_base, auth_header, auth_format, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                new_id, config.route_key, config.target_model, config.provider,
                config.prompt_keywords, config.description, config.enabled,
                config.api_key, config.api_base, config.auth_header, config.auth_format,
                datetime.now(), datetime.now()
            ])
            return new_id
    
    def update_model_config(self, config_id: int, config: ModelConfig) -> bool:
        with self.get_connection() as conn:
            result = conn.execute("""
                UPDATE modelconfig SET 
                route_key=?, target_model=?, provider=?, prompt_keywords=?, description=?,
                enabled=?, api_key=?, api_base=?, auth_header=?, auth_format=?, updated_at=?
                WHERE id=?
            """, [
                config.route_key, config.target_model, config.provider,
                config.prompt_keywords, config.description, config.enabled,
                config.api_key, config.api_base, config.auth_header, config.auth_format,
                datetime.now(), config_id
            ])
            return result.rowcount > 0
    
    def delete_model_config(self, config_id: int) -> bool:
        with self.get_connection() as conn:
            result = conn.execute("DELETE FROM modelconfig WHERE id=?", [config_id])
            return result.rowcount > 0

    # ApiKeyPool CRUD
    def list_api_keys(self, provider: Optional[str] = None) -> List[dict]:
        with self.get_connection() as conn:
            if provider:
                result = conn.execute("SELECT * FROM api_key_pool WHERE provider = ? ORDER BY id", [provider]).fetchall()
            else:
                result = conn.execute("SELECT * FROM api_key_pool ORDER BY provider, id").fetchall()
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row)) for row in result]
    
    def create_api_key(self, key_pool: ApiKeyPool) -> int:
        with self.get_connection() as conn:
            max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM api_key_pool").fetchone()[0]
            new_id = max_id + 1
            
            conn.execute("""
                INSERT INTO api_key_pool 
                (id, provider, api_key, auth_header, auth_format, is_active, 
                 requests_count, success_count, error_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                new_id, key_pool.provider, key_pool.api_key, key_pool.auth_header,
                key_pool.auth_format, key_pool.is_active, key_pool.requests_count,
                key_pool.success_count, key_pool.error_count, datetime.now(), datetime.now()
            ])
            return new_id
    
    def delete_api_key(self, key_id: int) -> bool:
        with self.get_connection() as conn:
            result = conn.execute("DELETE FROM api_key_pool WHERE id=?", [key_id])
            return result.rowcount > 0

    # ApiRoute CRUD
    def list_api_routes(self) -> List[dict]:
        with self.get_connection() as conn:
            result = conn.execute("SELECT * FROM apiroute ORDER BY id").fetchall()
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row)) for row in result]

    # 统计信息
    def get_api_stats(self, days: int = 7) -> dict:
        with self.get_connection() as conn:
            # 最近N天的请求统计
            result = conn.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as requests
                FROM apirequestlog 
                WHERE timestamp >= CURRENT_DATE - INTERVAL ? DAY
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, [days]).fetchall()
            
            daily_stats = [{'date': row[0], 'requests': row[1]} for row in result]
            
            # 提供商统计
            provider_stats = conn.execute("""
                SELECT provider, COUNT(*) as count, 
                       SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_count
                FROM api_key_pool 
                GROUP BY provider
            """).fetchall()
            
            return {
                'daily_requests': daily_stats,
                'provider_stats': [{'provider': row[0], 'total_keys': row[1], 'active_keys': row[2]} for row in provider_stats]
            }

db_manager = DatabaseManager()

@click.group()
def cli():
    """Claude Code Proxy 数据库管理工具"""
    pass

# Model Config 命令组
@cli.group()
def model():
    """模型配置管理"""
    pass

@model.command('list')
def list_models():
    """列出所有模型配置"""
    configs = db_manager.list_model_configs()
    if not configs:
        click.echo("没有找到模型配置")
        return
    
    click.echo(f"{'ID':<5} {'路由键':<15} {'目标模型':<20} {'提供商':<10} {'启用':<5}")
    click.echo("-" * 60)
    for config in configs:
        click.echo(f"{config['id']:<5} {config['route_key']:<15} {config['target_model']:<20} {config['provider']:<10} {'是' if config['enabled'] else '否':<5}")

@model.command('show')
@click.argument('config_id', type=int)
def show_model(config_id):
    """显示模型配置详情"""
    config = db_manager.get_model_config(config_id)
    if not config:
        click.echo(f"未找到ID为 {config_id} 的模型配置")
        return
    
    for key, value in config.items():
        click.echo(f"{key}: {value}")

@model.command('create')
@click.option('--route-key', required=True, help='路由键')
@click.option('--target-model', required=True, help='目标模型')
@click.option('--provider', required=True, help='提供商')
@click.option('--keywords', help='提示关键词')
@click.option('--description', help='描述')
@click.option('--api-key', help='API密钥')
@click.option('--api-base', help='API基础URL')
def create_model(route_key, target_model, provider, keywords, description, api_key, api_base):
    """创建模型配置"""
    config = ModelConfig(
        route_key=route_key,
        target_model=target_model,
        provider=provider,
        prompt_keywords=keywords,
        description=description,
        api_key=api_key,
        api_base=api_base
    )
    
    config_id = db_manager.create_model_config(config)
    click.echo(f"模型配置创建成功，ID: {config_id}")

@model.command('delete')
@click.argument('config_id', type=int)
@click.confirmation_option(prompt='确定要删除这个模型配置吗？')
def delete_model(config_id):
    """删除模型配置"""
    if db_manager.delete_model_config(config_id):
        click.echo(f"模型配置 {config_id} 删除成功")
    else:
        click.echo(f"未找到ID为 {config_id} 的模型配置")

# API Key 命令组
@cli.group()
def apikey():
    """API密钥管理"""
    pass

@apikey.command('list')
@click.option('--provider', help='过滤指定提供商')
def list_keys(provider):
    """列出API密钥"""
    keys = db_manager.list_api_keys(provider)
    if not keys:
        click.echo("没有找到API密钥")
        return
    
    click.echo(f"{'ID':<5} {'提供商':<12} {'密钥':<20} {'状态':<6} {'请求数':<8} {'成功率':<8}")
    click.echo("-" * 70)
    for key in keys:
        masked_key = key['api_key'][:10] + '...' if len(key['api_key']) > 10 else key['api_key']
        success_rate = f"{key['success_count']/(key['requests_count'] or 1)*100:.1f}%" if key['requests_count'] > 0 else "N/A"
        status = "活跃" if key['is_active'] else "禁用"
        click.echo(f"{key['id']:<5} {key['provider']:<12} {masked_key:<20} {status:<6} {key['requests_count']:<8} {success_rate:<8}")

@apikey.command('add')
@click.option('--provider', required=True, help='提供商')
@click.option('--key', required=True, help='API密钥')
@click.option('--auth-header', default='Authorization', help='认证头')
@click.option('--auth-format', default='Bearer {key}', help='认证格式')
def add_key(provider, key, auth_header, auth_format):
    """添加API密钥"""
    key_pool = ApiKeyPool(
        provider=provider,
        api_key=key,
        auth_header=auth_header,
        auth_format=auth_format
    )
    
    try:
        key_id = db_manager.create_api_key(key_pool)
        click.echo(f"API密钥添加成功，ID: {key_id}")
    except Exception as e:
        click.echo(f"添加失败: {e}")

@apikey.command('remove')
@click.argument('key_id', type=int)
@click.confirmation_option(prompt='确定要删除这个API密钥吗？')
def remove_key(key_id):
    """删除API密钥"""
    if db_manager.delete_api_key(key_id):
        click.echo(f"API密钥 {key_id} 删除成功")
    else:
        click.echo(f"未找到ID为 {key_id} 的API密钥")

# 统计命令
@cli.command()
@click.option('--days', default=7, help='统计天数')
def stats(days):
    """显示统计信息"""
    stats_data = db_manager.get_api_stats(days)
    
    click.echo(f"\n最近 {days} 天请求统计:")
    click.echo("-" * 30)
    for stat in stats_data['daily_requests']:
        click.echo(f"{stat['date']}: {stat['requests']} 请求")
    
    click.echo("\n提供商密钥统计:")
    click.echo("-" * 30)
    for stat in stats_data['provider_stats']:
        click.echo(f"{stat['provider']}: {stat['active_keys']}/{stat['total_keys']} 活跃密钥")

if __name__ == '__main__':
    cli()