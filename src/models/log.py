from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ApiRequestLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime = None
    source_api: str = None
    target_api: str = None
    source_model: str = None
    target_model: str = None
    source_prompt: str = None
    target_prompt: str = None
    source_params: str = None
    target_params: str = None
    source_response: str = None
    target_response: str = None
    headers: Optional[str] = None 