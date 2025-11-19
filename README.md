# 个人投资系统

基于国金QMT驱动的个人投资管理系统，支持行情浏览、交易管理和投资收益分析。

## 功能特性

- 📊 **行情浏览**：实时行情查看、历史行情查询
- 💰 **投资账本**：交易记录管理、持仓跟踪
- 📈 **收益分析**：收益率计算、持仓分析、盈亏统计
- 🔌 **QMT集成**：连接国金QMT驱动获取行情和交易数据

## 技术栈

- FastAPI：现代Python Web框架
- SQLAlchemy：ORM数据库操作
- Pandas：数据分析
- QMT：国金量化交易平台

## 快速开始

### 1. 安装 UV（如果未安装）

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

或使用 pip:
```bash
pip install uv
```

### 2. 安装依赖

```bash
uv sync
```

这会自动创建虚拟环境并安装所有依赖。

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

### 4. 初始化数据库

```bash
python init_db.py
```

或者使用Alembic：

```bash
alembic upgrade head
```

### 5. 启动服务

**使用 UV（推荐）:**
```bash
uv run python run.py
```

或使用批处理文件（Windows）:
```bash
start_server.bat
```

**传统方式（需要先激活虚拟环境）:**
```bash
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # Linux/macOS

python run.py
```

或者：

```bash
uvicorn app.main:app --reload
```

服务将在 http://localhost:8000 启动

## 项目结构

```
aiqore-back/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI主应用
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── account.py       # 账户模型
│   │   ├── trade.py         # 交易记录模型
│   │   └── position.py      # 持仓模型
│   ├── services/            # 业务逻辑
│   │   ├── __init__.py
│   │   ├── qmt_service.py   # QMT连接服务
│   │   ├── market_service.py # 行情服务
│   │   ├── trade_service.py  # 交易服务
│   │   └── analysis_service.py # 分析服务
│   └── api/                 # API路由
│       ├── __init__.py
│       ├── market.py        # 行情API
│       ├── trade.py         # 交易API
│       └── analysis.py      # 分析API
├── alembic/                 # 数据库迁移
├── pyproject.toml          # 项目配置和依赖（UV）
├── .python-version         # Python版本要求
├── .env.example
└── README.md

```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要API接口

### 账户管理

- `POST /api/trade/account` - 创建账户
- `GET /api/trade/accounts` - 获取所有账户
- `GET /api/trade/account/{account_id}` - 获取账户详情
- `POST /api/trade/account/{account_id}/sync` - 同步账户信息（从QMT）

### 交易管理

- `GET /api/trade/account/{account_id}/trades` - 获取交易记录
- `POST /api/trade/account/{account_id}/trade` - 记录交易
- `GET /api/trade/account/{account_id}/positions` - 获取持仓列表
- `POST /api/trade/account/{account_id}/positions/sync` - 同步持仓信息（从QMT）

### 行情浏览

- `GET /api/market/quote?symbols=000001.SZ,600000.SH` - 获取实时行情
- `GET /api/market/kline?symbol=000001.SZ&period=1d&count=100` - 获取K线数据
- `GET /api/market/search?keyword=平安` - 搜索股票

### 收益分析

- `GET /api/analysis/account/{account_id}/summary` - 获取账户汇总
- `GET /api/analysis/account/{account_id}/positions` - 获取持仓分析
- `GET /api/analysis/account/{account_id}/trade-stats` - 获取交易统计
- `GET /api/analysis/account/{account_id}/profit-trend?days=30` - 获取盈亏趋势

## 使用示例

### 1. 创建账户

```bash
curl -X POST "http://localhost:8000/api/trade/account" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "123456",
    "name": "我的投资账户",
    "initial_capital": 100000
  }'
```

### 2. 记录交易

```bash
curl -X POST "http://localhost:8000/api/trade/account/1/trade" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001.SZ",
    "symbol_name": "平安银行",
    "direction": "买入",
    "price": 10.5,
    "quantity": 1000,
    "trade_time": "2024-01-01T09:30:00",
    "commission": 5.0,
    "tax": 0.0
  }'
```

### 3. 获取实时行情

```bash
curl "http://localhost:8000/api/market/quote?symbols=000001.SZ,600000.SH"
```

### 4. 查看账户汇总

```bash
curl "http://localhost:8000/api/analysis/account/1/summary"
```

## QMT连接说明

当前QMT服务模块提供了接口框架，实际使用时需要：

1. 安装QMT Python SDK（通常为xtquant库）
2. 在 `app/services/qmt_service.py` 中实现具体的连接逻辑
3. 配置 `.env` 文件中的QMT连接参数

详细连接方式请参考国金QMT官方文档。

## 注意事项

- 首次使用前需要初始化数据库
- QMT连接需要确保QMT客户端已启动并配置正确
- 建议在生产环境中使用PostgreSQL等专业数据库替代SQLite

