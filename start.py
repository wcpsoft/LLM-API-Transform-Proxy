#!/usr/bin/env python3
"""
Claude Code Proxy 启动脚本
支持API代理服务和Web管理界面
"""

import argparse
import os
import subprocess
import sys
import time
import uvicorn
from src.config import get_port

def start_api_server(port=None, reload=True):
    """启动API服务器"""
    if port is None:
        port = get_port()
    
    print(f"🚀 启动API服务器 - http://0.0.0.0:{port}")
    print(f"📚 API文档地址 - http://localhost:{port}/docs")
    
    try:
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=port,
            reload=reload
        )
    except OSError as e:
        if "Address already in use" in str(e):
            fallback_port = port + 1
            print(f"⚠️  端口 {port} 被占用，尝试使用端口 {fallback_port}")
            uvicorn.run(
                "src.main:app",
                host="0.0.0.0",
                port=fallback_port,
                reload=reload
            )
        else:
            raise

def start_web_admin():
    """启动Web管理界面"""
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    
    if not os.path.exists(web_dir):
        print("❌ Web管理界面目录不存在")
        return False
    
    # 检查是否安装了依赖
    if not os.path.exists(os.path.join(web_dir, "node_modules")):
        print("📦 安装Web管理界面依赖...")
        try:
            subprocess.run(["pnpm", "install"], cwd=web_dir, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ 请先安装pnpm: npm install -g pnpm")
            return False
    
    print("🌐 启动Web管理界面 - http://localhost:3000")
    try:
        subprocess.run(["pnpm", "dev"], cwd=web_dir)
    except KeyboardInterrupt:
        print("\n👋 Web管理界面已停止")
    except FileNotFoundError:
        print("❌ 请先安装pnpm: npm install -g pnpm")
        return False
    
    return True

def start_api_server_no_reload(port=None):
    """启动API服务器（无重载模式，适用于多服务启动）"""
    if port is None:
        port = get_port()
    
    print(f"🚀 启动API服务器 - http://0.0.0.0:{port}")
    print(f"📚 API文档地址 - http://localhost:{port}/docs")
    
    try:
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=port,
            reload=False  # 在多服务模式下禁用重载
        )
    except OSError as e:
        if "Address already in use" in str(e):
            fallback_port = port + 1
            print(f"⚠️  端口 {port} 被占用，尝试使用端口 {fallback_port}")
            uvicorn.run(
                "src.main:app",
                host="0.0.0.0",
                port=fallback_port,
                reload=False
            )
        else:
            raise

def start_all_services():
    """同时启动API服务器和Web管理界面"""
    import threading
    import signal
    
    def signal_handler(sig, frame):
        print("\n👋 正在停止所有服务...")
        sys.exit(0)
    
    # 在主线程中设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 启动API服务器（在后台线程）
    api_thread = threading.Thread(
        target=start_api_server_no_reload, 
        args=(get_port(),),
        daemon=True
    )
    api_thread.start()
    
    # 等待API服务器启动
    time.sleep(2)
    
    # 启动Web管理界面（主线程）
    start_web_admin()

def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Proxy 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python start.py                    # 启动API服务器
  python start.py --web             # 启动Web管理界面
  python start.py --all             # 同时启动API和Web界面
  python start.py --port 8080       # 指定端口启动API服务器
  python start.py --no-reload       # 禁用自动重载
        """
    )
    
    parser.add_argument(
        "--web", 
        action="store_true", 
        help="启动Web管理界面"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="同时启动API服务器和Web管理界面"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        help="指定API服务器端口"
    )
    parser.add_argument(
        "--no-reload", 
        action="store_true", 
        help="禁用自动重载"
    )
    
    args = parser.parse_args()
    
    print("🎯 Claude Code Proxy")
    print("=" * 50)
    
    if args.all:
        start_all_services()
    elif args.web:
        start_web_admin()
    else:
        start_api_server(
            port=args.port, 
            reload=not args.no_reload
        )

if __name__ == "__main__":
    main()