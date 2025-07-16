"""加密工具模块

提供SM3哈希算法和其他加密相关功能
"""

import hashlib
import secrets
import string
from typing import Optional


class SM3Crypto:
    """SM3加密工具类"""
    
    @staticmethod
    def hash(data: str) -> str:
        """计算字符串的SM3哈希值
        
        Args:
            data: 要哈希的字符串
            
        Returns:
            64位十六进制哈希值
        """
        # 由于Python标准库不包含SM3，这里使用SHA256作为替代
        # 在生产环境中应该使用真正的SM3实现，如gmssl库
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_session_id() -> str:
        """生成安全的session ID
        
        Returns:
            64位十六进制session ID
        """
        return secrets.token_hex(32)
    
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """生成安全的随机密码
        
        Args:
            length: 密码长度，默认12位
            
        Returns:
            随机密码字符串
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_token(password_hash: str, username: str, timestamp: int) -> str:
        """生成认证token
        
        Token生成公式: SM3(password_hash + username + timestamp)
        
        Args:
            password_hash: 用户密码的SM3哈希值
            username: 用户名
            timestamp: 登录时间戳
            
        Returns:
            64位十六进制token
        """
        combined = f"{password_hash}{username}{timestamp}"
        return SM3Crypto.hash(combined)
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码
        
        Args:
            password: 明文密码
            password_hash: 存储的密码哈希
            
        Returns:
            密码是否正确
        """
        return SM3Crypto.hash(password) == password_hash
    
    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行哈希
        
        Args:
            password: 明文密码
            
        Returns:
            密码哈希值
        """
        return SM3Crypto.hash(password)


def install_sm3_library():
    """安装真正的SM3库的提示函数"""
    print("""
    注意：当前使用SHA256作为SM3的替代实现。
    如需使用真正的SM3算法，请安装gmssl库：
    
    pip install gmssl
    
    然后修改SM3Crypto类使用真正的SM3实现。
    """)


if __name__ == "__main__":
    # 测试加密功能
    crypto = SM3Crypto()
    
    # 测试密码哈希
    password = "admin123"
    password_hash = crypto.hash_password(password)
    print(f"密码: {password}")
    print(f"哈希: {password_hash}")
    print(f"验证: {crypto.verify_password(password, password_hash)}")
    
    # 测试token生成
    username = "admin"
    timestamp = 1703123456789
    token = crypto.generate_token(password_hash, username, timestamp)
    print(f"\nToken: {token}")
    
    # 测试session ID生成
    session_id = crypto.generate_session_id()
    print(f"Session ID: {session_id}")
    
    install_sm3_library()