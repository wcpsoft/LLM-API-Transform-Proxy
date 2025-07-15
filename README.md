# 大模型 API 互转代理（OpenAI / Claude / Gemini）

本项目实现了一个支持 OpenAI、Anthropic Claude、Google Gemini 等主流大模型 API 互转的代理服务。通过灵活配置，用户可用任意一种 API 客户端无缝调用其他厂商模型，支持多模型智能分流、直连与流式响应。

---

## 目录

1. 项目简介
2. API 互转关系总览
3. 配置方法
4. 启动服务
5. curl 测试示例
6. 常见问题
7. 进阶用法

---

## 1. 项目简介

- 兼容 OpenAI、Claude、Gemini 标准 API。
- 支持 API 互转、智能分流、日志记录。
- 适合大模型混合部署、平滑切换、统一调用入口。

---

## 2. API 互转关系总览

| 客户端请求 | 代理入口路径              | 后端实际调用         | 说明                                             |
| ---------- | ------------------------- | -------------------- | ------------------------------------------------ |
| OpenAI     | /v1/chat/completions      | Claude/Gemini/OpenAI | 根据 model 字段和关键词自动分流，格式自动转换    |
| Claude     | /v1/anthropic/completions | Claude/OpenAI/Gemini | 支持 Claude 标准格式，后端可按配置转发到任意模型 |
| Gemini     | /v1/gemini/completions    | Gemini/OpenAI/Claude | 支持 Gemini 标准格式，后端可按配置转发到任意模型 |

- **transformer 模式**：启用 API 互转能力，支持多模型无缝切换。
- **direct 模式**：直连目标 API，不做格式转换。

---

## 3. 配置方法

编辑 `config/app.yml`，核心配置如下：

```yaml
MODE: "transformer"  # transformer: 互转模式，direct: 直连模式
PORT: 8000
HOST: "0.0.0.0"
DEBUG: true
PREFERRED_PROVIDER: anthropic  # 默认优先路由

# API密钥池配置（支持多密钥轮换和自定义认证）
API_KEY_POOLS:
  openai:
    keys: 
      - "sk-your-openai-key-1"
      - "sk-your-openai-key-2"
    auth_header: "Authorization"  # 可选，默认为Bearer
    auth_format: "Bearer {key}"   # 可选，默认格式
  anthropic:
    keys:
      - "sk-ant-your-key-1"
      - "sk-ant-your-key-2"
    auth_header: "x-api-key"
    auth_format: "{key}"
  gemini:
    keys:
      - "your-gemini-key-1"
      - "your-gemini-key-2"

# 向后兼容的单密钥配置（仍然支持）
OPENAI_API_KEY: 你的OpenAI密钥
ANTHROPIC_API_KEY: 你的Claude密钥
GEMINI_API_KEY: 你的Gemini密钥
```

### 配置说明

- `MODE` 决定是否启用 API 互转。
- `API_KEY_POOLS` 支持多密钥轮换，提高并发能力和稳定性。
- 模型路由配置已迁移到数据库，可通过 Web 管理界面进行配置。
- 路由可配置专用密钥池，实现更精细的密钥管理。

### API密钥管理功能

#### 多密钥轮换
- 支持为每个提供商配置多个API密钥
- 自动轮换使用，提高并发处理能力
- 当遇到429限流错误时，自动切换到下一个可用密钥

#### 自定义认证头
- 支持自定义认证头名称和格式
- 适配不同第三方API的认证方式
- 灵活的认证值格式化

#### 密钥使用统计
- 实时监控每个密钥的请求次数和成功率
- 记录请求状态码，便于问题排查
- 内存中维护统计信息，性能优异

#### 监控API端点
访问 `/v1/api-keys/stats` 查看密钥使用统计：

```json
{
  "openai": {
    "sk-key1": {
      "total_requests": 150,
      "successful_requests": 145,
      "failed_requests": 5,
      "success_rate": 0.967,
      "last_used": "2024-01-15T10:30:00Z",
      "status_codes": {
        "200": 145,
        "429": 3,
        "500": 2
      }
    }
  }
}
```

---

## 4. 启动服务

### 4.1 快速启动

```bash
# 安装依赖
uv pip install -r pyproject.toml

# 启动API服务器
python start.py

# 启动Web管理界面
python start.py --web

# 同时启动API和Web界面
python start.py --all
```

### 4.2 启动选项

| 命令                          | 说明                  |
| ----------------------------- | --------------------- |
| `python start.py`             | 启动API代理服务器     |
| `python start.py --web`       | 启动Web管理界面       |
| `python start.py --all`       | 同时启动API和Web界面  |
| `python start.py --port 8080` | 指定端口启动API服务器 |
| `python start.py --no-reload` | 禁用自动重载          |

### 4.3 Web管理界面

项目提供了现代化的Web管理界面，支持：

- **仪表盘**：实时监控API使用情况和统计数据
- **模型配置**：管理API路由和模型映射
- **密钥管理**：管理API密钥池，支持多密钥轮换
- **路由管理**：配置API路由规则
- **请求日志**：查看详细的API调用日志

访问地址：
- Web管理界面：http://localhost:3000
- API服务器：http://localhost:8000
- API文档：http://localhost:8000/docs

### 4.4 CLI管理工具

除了Web界面，还提供命令行管理工具：

```bash
# 查看所有模型配置
python -m src.cli_admin models list

# 添加模型配置
python -m src.cli_admin models create --route-key "gpt4" --target-model "gpt-4" --provider "openai"

# 查看API密钥
python -m src.cli_admin keys list

# 添加API密钥
python -m src.cli_admin keys add --provider "openai" --api-key "sk-xxx"

# 查看统计信息
python -m src.cli_admin stats requests
```

---

## 5. curl 测试示例

### 5.1 OpenAI API → Claude

```bash
curl -X POST http://localhost:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 任意字符串" \
  -d '{
    "model": "claude-3-opus-20240229",
    "messages": [
      {"role": "user", "content": "请用中文自我介绍一下你自己。"}
    ]
  }'
```
**说明**：请求格式与 OpenAI 官方一致，代理自动转为 Claude API 调用，返回结构不变。

---

### 5.2 OpenAI API → Gemini

```bash
curl -X POST http://localhost:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 任意字符串" \
  -d '{
    "model": "gemini-pro",
    "messages": [
      {"role": "user", "content": "介绍一下Google Gemini。"}
    ]
  }'
```
**说明**：只需更换 model 字段，代理自动转为 Gemini API 调用。

---

### 5.3 Claude 标准 API → OpenAI/Gemini

```bash
curl -X POST http://localhost:8082/v1/anthropic/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-opus-20240229",
    "messages": [
      {"role": "user", "content": "你好 Claude！"}
    ]
  }'
```
**说明**：可按配置将 Claude 标准请求转发到 OpenAI 或 Gemini。

---

### 5.4 Gemini 标准 API → OpenAI/Claude

```bash
curl -X POST http://localhost:8082/v1/gemini/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-pro",
    "messages": [
      {"role": "user", "content": "你好 Gemini！"}
    ]
  }'
```
**说明**：可按配置将 Gemini 标准请求转发到 OpenAI 或 Claude。

---

## 6. 常见问题

- **如何切换后端模型？**  
  只需更改 model 字段或配置关键词路由，无需修改客户端代码。

- **如何兼容 OpenAI SDK？**  
  只需将 `api_base` 指向本代理服务，API Key 可随意填写。

- **如何查看日志？**  
  日志自动记录每次 API 调用的来源、目标、参数、响应等，详见 `src/utils/db.py`。

---

## 7. 进阶用法

- 支持流式（stream）响应，curl 测试时加 `"stream": true` 字段即可。
- 支持自定义分流规则，可通过 Web 管理界面或 CLI 工具进行配置。
- 支持多租户、多模型混合部署。

---

如有问题请提交 issue 或联系维护者。
