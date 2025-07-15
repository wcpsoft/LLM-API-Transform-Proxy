from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SystemConfig(BaseModel):
    """系统配置模型"""
    id: Optional[int] = None
    config_key: str
    config_value: Optional[str] = None
    config_type: str = "string"  # string, int, bool, json
    description: Optional[str] = None
    is_sensitive: bool = False  # 是否为敏感信息（如密钥）
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True