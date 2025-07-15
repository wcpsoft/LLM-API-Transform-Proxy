from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ModelConfig(BaseModel):
    id: Optional[int] = None
    route_key: str
    target_model: str
    provider: str
    prompt_keywords: str = None  # 逗号分隔或JSON
    description: str = None
    enabled: bool = True
    api_key: str = None
    api_base: str = None
    auth_header: str = None
    auth_format: str = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ApiKeyPool(BaseModel):
    id: Optional[int] = None
    provider: str
    api_key: str
    auth_header: str = "Authorization"
    auth_format: str = "Bearer {key}"
    is_active: bool = True
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_used_at: Optional[datetime] = None
    rate_limit_reset_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ApiKeyStats(BaseModel):
    id: Optional[int] = None
    provider: str
    api_key: str
    date: str  # YYYY-MM-DD格式
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    status_codes: str = None  # JSON格式
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None