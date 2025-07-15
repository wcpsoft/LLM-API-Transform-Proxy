# 前端测试说明

本项目包含了完整的前端测试套件，确保API调用的正确性和兼容性。

## 测试类型

### 1. 单元测试 (api.test.js)
- 测试API函数的调用参数和端点路径
- 使用Mock验证API调用的正确性
- 不依赖实际的后端服务

### 2. 集成测试 (integration.test.js)
- 测试实际的API端点响应
- 验证前后端接口的兼容性
- 需要后端服务运行在 `http://localhost:8000`

## 运行测试

### 安装依赖
```bash
cd web
pnpm install
```

### 运行所有测试
```bash
pnpm test
```

### 运行单次测试
```bash
pnpm test:run
```

### 运行集成测试
```bash
# 确保后端服务已启动
pnpm test:integration
```

### 运行测试并生成覆盖率报告
```bash
pnpm test:coverage
```

### 使用UI界面运行测试
```bash
pnpm test:ui
```

## 测试覆盖范围

### API端点测试
- ✅ 模型管理 (`/v1/admin/models`)
- ✅ API密钥管理 (`/v1/admin/api-keys`)
- ✅ 路由管理 (`/v1/admin/routes`)
- ✅ 日志查询 (`/v1/admin/logs`)
- ✅ 统计数据 (`/v1/admin/stats`)
- ✅ 公共API (`/v1/models`, `/v1/chat/completions`)

### 测试场景
- ✅ GET请求参数传递
- ✅ POST请求数据格式
- ✅ PUT请求更新操作
- ✅ PATCH请求状态更新
- ✅ DELETE请求删除操作
- ✅ 错误处理和状态码验证

## 测试最佳实践

1. **运行集成测试前确保后端服务启动**
   ```bash
   cd ..
   python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **查看测试结果**
   - 单元测试应该100%通过
   - 集成测试可能因为后端实现不完整而部分失败，这是正常的

3. **调试测试失败**
   - 检查控制台输出的错误信息
   - 确认API端点路径是否正确
   - 验证请求数据格式是否匹配后端期望

4. **添加新测试**
   - 在 `api.test.js` 中添加新的API函数测试
   - 在 `integration.test.js` 中添加新的端点集成测试

## 故障排除

### 常见问题

1. **404错误**
   - 检查API路径是否正确
   - 确认后端路由是否已实现

2. **CORS错误**
   - 确保后端CORS配置正确
   - 检查请求头设置

3. **超时错误**
   - 增加测试超时时间
   - 检查后端服务是否正常响应

### 调试技巧

1. 使用 `console.log` 查看请求和响应数据
2. 检查浏览器开发者工具的网络面板
3. 使用Postman等工具手动测试API端点
4. 查看后端日志确认请求是否到达