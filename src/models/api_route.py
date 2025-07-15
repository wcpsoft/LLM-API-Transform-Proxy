from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ApiRoute(BaseModel):
    id: Optional[int] = None
    path: str
    method: str
    description: str = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None