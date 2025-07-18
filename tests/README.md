# 测试指南

## 概述

本项目包含完整的测试套件，支持单元测试、集成测试和性能测试。

## 测试结构

```
tests/
├── test_framework.py          # 测试框架核心
├── unit/                      # 单元测试
│   └── test_model_service.py  # ModelService单元测试
├── integration/               # 集成测试
│   └── test_api_integration.py # API集成测试
├── fixtures/                  # 测试数据
├── mocks/                     # 模拟对象
└── utils/                     # 测试工具
```

## 快速开始

### 1. 安装测试依赖

```bash
pip install -r requirements-test.txt
```

### 2. 运行测试

使用测试运行脚本：

```bash
# 运行所有测试
python run_tests.py

# 运行特定类型测试
python run_tests.py unit
python run_tests.py integration
python run_tests.py performance

# 运行覆盖率报告
python run_tests.py coverage

# 设置测试环境
python run_tests.py --setup
```

使用pytest直接运行：

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 运行性能测试
pytest -m performance -v

# 运行带覆盖率的测试
pytest --cov=src --cov-report=html --cov-report=term
```

## 测试类型

### 单元测试 (Unit Tests)
- 测试单个组件的功能
- 使用模拟对象隔离依赖
- 快速执行，适合CI/CD

```bash
pytest tests/unit -v
```

### 集成测试 (Integration Tests)
- 测试组件间的交互
- 使用真实数据库和外部服务
- 验证完整的业务流程

```bash
pytest tests/integration -v
```

### 性能测试 (Performance Tests)
- 测试响应时间和吞吐量
- 内存使用监控
- 并发请求处理

```bash
pytest -m performance -v
```

### 冒烟测试 (Smoke Tests)
- 快速验证核心功能
- 适合部署后验证

```bash
pytest -m smoke -v
```

## 测试标记

- `unit`: 单元测试
- `integration`: 集成测试
- `performance`: 性能测试
- `smoke`: 冒烟测试
- `regression`: 回归测试
- `slow`: 慢速测试

## 测试配置

测试配置位于 `pytest.ini` 文件中，包含：
- 测试发现规则
- 覆盖率配置
- 标记定义
- 警告过滤

## 测试数据

测试使用以下数据源：
- SQLite内存数据库（默认）
- 模拟API响应
- 工厂模式生成测试数据

## 环境变量

测试环境变量：

```bash
export ENVIRONMENT=test
export DATABASE_URL=sqlite:///./test.db
export LOG_LEVEL=DEBUG
export RATE_LIMIT_ENABLED=false
```

## 覆盖率报告

运行测试后会生成覆盖率报告：
- HTML报告：`htmlcov/index.html`
- 终端报告：控制台输出
- 覆盖率阈值：80%

## 最佳实践

1. **测试命名**：使用描述性的测试函数名
2. **测试结构**：遵循AAA模式（Arrange, Act, Assert）
3. **测试数据**：使用工厂模式生成测试数据
4. **模拟对象**：适当使用mock隔离外部依赖
5. **断言**：使用具体的断言而不是通用的assert
6. **测试文档**：为复杂的测试添加详细注释

## 调试测试

### 调试单个测试

```bash
pytest tests/unit/test_model_service.py::TestModelService::test_get_all_models -v -s
```

### 调试失败的测试

```bash
pytest --pdb -v
```

### 查看详细输出

```bash
pytest -v -s --tb=long
```

## 持续集成

测试配置支持GitHub Actions：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements-test.txt
      - run: python run_tests.py
```

## 故障排除

### 测试数据库问题

```bash
# 清理测试数据库
rm test.db
python run_tests.py --setup
```

### 端口冲突

```bash
# 使用不同端口运行测试
export TEST_SERVER_PORT=8001
```

### 依赖问题

```bash
# 重新安装测试依赖
pip install -r requirements-test.txt --force-reinstall
```

## 扩展测试

添加新的测试：

1. 在相应目录创建测试文件
2. 使用适当的测试标记
3. 遵循现有测试模式
4. 更新测试文档

## 性能基准

当前性能基准：
- 单元测试：< 1秒
- 集成测试：< 30秒
- 性能测试：50并发请求 < 5秒
- 内存增长：< 50MB

## 联系支持

如有测试相关问题，请：
1. 查看测试日志
2. 检查环境配置
3. 参考本指南
4. 创建issue报告问题