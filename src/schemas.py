from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union, Literal

class SystemContent(BaseModel):
    type: Literal["text"]
    text: str

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[Any]]

class Tool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]

class ThinkingConfig(BaseModel):
    enabled: bool

class MessagesRequest(BaseModel):
    model: str
    max_tokens: int
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    thinking: Optional[ThinkingConfig] = None
    original_model: Optional[str] = None

class TokenCountRequest(BaseModel):
    model: str
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    tools: Optional[List[Tool]] = None
    thinking: Optional[ThinkingConfig] = None
    tool_choice: Optional[Dict[str, Any]] = None
    original_model: Optional[str] = None

class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

class MessagesResponse(BaseModel):
    id: str
    model: str
    role: Literal["assistant"] = "assistant"
    content: List[Any]
    type: Literal["message"] = "message"
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Usage

class TokenCountResponse(BaseModel):
    input_tokens: int

# 模型管理相关的Schema
class CreateModelRequest(BaseModel):
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商")
    target_model: str = Field(..., description="目标模型")
    route_key: str = Field(..., description="路由键")
    api_base: Optional[str] = Field(None, description="API基础URL")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

class UpdateModelRequest(BaseModel):
    name: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="提供商")
    target_model: Optional[str] = Field(None, description="目标模型")
    route_key: Optional[str] = Field(None, description="路由键")
    api_base: Optional[str] = Field(None, description="API基础URL")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

# API密钥管理相关的Schema
class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., description="密钥名称")
    provider: str = Field(..., description="提供商")
    api_key: str = Field(..., description="API密钥")
    auth_header: str = Field("Authorization", description="认证头")
    auth_format: str = Field("Bearer {api_key}", description="认证格式")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

class UpdateApiKeyRequest(BaseModel):
    name: Optional[str] = Field(None, description="密钥名称")
    provider: Optional[str] = Field(None, description="提供商")
    api_key: Optional[str] = Field(None, description="API密钥")
    auth_header: Optional[str] = Field(None, description="认证头")
    auth_format: Optional[str] = Field(None, description="认证格式")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

class UpdateKeyStatusRequest(BaseModel):
    enabled: bool = Field(..., description="是否启用")

# 路由管理相关的Schema
class CreateRouteRequest(BaseModel):
    path: str = Field(..., description="路由路径")
    method: str = Field(..., description="HTTP方法")
    target_url: str = Field(..., description="目标URL")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

class UpdateRouteRequest(BaseModel):
    path: Optional[str] = Field(None, description="路由路径")
    method: Optional[str] = Field(None, description="HTTP方法")
    target_url: Optional[str] = Field(None, description="目标URL")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="描述")

# 系统配置相关的Schema
class CreateSystemConfigRequest(BaseModel):
    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="描述")

class UpdateSystemConfigRequest(BaseModel):
    value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="描述")