# QMT 数据集成说明

## 功能概述

已实现国金 MiniQMT 数据接入，支持：
- 自动更新证券基础信息到数据库（支持所有类型标的：股票、ETF、基金、债券、期货、期权、指数等）
- 实时行情查询
- K线数据获取
- 股票搜索功能

### 支持的标的类型

系统现在可以同步以下所有类型的标的：
- **股票**：沪深A股、沪深B股、创业板、上证A股、上证B股
- **ETF基金**：沪深ETF、深市ETF、沪市ETF
- **基金**：沪深基金、深市基金、沪市基金
- **债券**：沪深债券、沪市债券、沪深转债、上证转债
- **指数**：沪深指数、沪市指数
- **期货**：上期所、大商所、郑商所、中金所、能源中心
- **期权**：上证期权、深证期权
- **其他**：连续合约、香港联交所股票等

## 配置说明

### 1. 环境变量配置

在 `.env` 文件中配置 QMT 相关参数：

```env
XT_QUANT_PATH=C:\国金证券QMT交易端\userdata_mini
XT_QUANT_ACCT=39271919
```

或者在 `app/config.py` 中已设置默认值。

### 2. QMT 客户端要求

- 确保已安装国金证券 QMT 客户端
- 确保 MiniQMT 已启动
- 确保 `xtquant` 模块可用（通常随 QMT 客户端安装）

## 数据库迁移

### 创建证券信息表

运行应用时，数据库表会自动创建。如果需要手动创建：

```python
from app.database import engine, Base
from app.models.security import Security

Base.metadata.create_all(bind=engine)
```

或使用 Alembic：

```bash
alembic revision --autogenerate -m "add_security_table"
alembic upgrade head
```

## 使用说明

### 1. 更新证券基础信息

#### 方法一：通过 API 接口

```bash
# 更新全部市场
curl -X POST "http://localhost:8000/api/security/update"

# 更新指定市场
curl -X POST "http://localhost:8000/api/security/update?market=SH"
curl -X POST "http://localhost:8000/api/security/update?market=SZ"
```

#### 方法二：使用脚本

```bash
# 使用 API 接口更新（推荐）
curl -X POST "http://localhost:8000/api/security/update"

# 或使用 Python 脚本
uv run python -c "from app.database import SessionLocal; from app.services.security_service import security_service; db = SessionLocal(); result = security_service.update_securities_from_qmt(db, market=None); print(result); db.close()"
```

### 2. 查询证券列表

```bash
# 获取所有证券
GET /api/security/list

# 获取指定市场证券
GET /api/security/list?market=SH

# 分页查询
GET /api/security/list?limit=100&offset=0
```

### 3. 搜索证券

```bash
GET /api/security/search?keyword=平安
```

### 4. 获取证券详情

```bash
GET /api/security/000001.SZ
```

## API 接口说明

### 证券信息接口

#### 更新证券信息
- **URL**: `/api/security/update`
- **方法**: `POST`
- **参数**: 
  - `market` (可选): 市场代码，`SH` 或 `SZ`
- **返回**: 更新结果统计

#### 获取证券列表
- **URL**: `/api/security/list`
- **方法**: `GET`
- **参数**:
  - `market` (可选): 市场代码
  - `limit` (可选): 返回数量，默认 100
  - `offset` (可选): 偏移量，默认 0
- **返回**: 证券列表

#### 搜索证券
- **URL**: `/api/security/search`
- **方法**: `GET`
- **参数**:
  - `keyword` (必需): 搜索关键词
  - `limit` (可选): 返回数量，默认 50
- **返回**: 匹配的证券列表

#### 获取证券详情
- **URL**: `/api/security/{symbol}`
- **方法**: `GET`
- **参数**:
  - `symbol` (路径参数): 证券代码，如 `000001.SZ`
- **返回**: 证券详细信息

### 行情接口（已更新）

#### 获取实时行情
- **URL**: `/api/market/quote`
- **方法**: `GET`
- **参数**: `symbols` (必需): 证券代码，多个用逗号分隔
- **说明**: 现在会自动从数据库获取证券名称

#### 搜索股票
- **URL**: `/api/market/search`
- **方法**: `GET`
- **参数**: `keyword` (必需): 搜索关键词
- **说明**: 优先从数据库搜索，数据库没有时从 QMT 搜索

## 数据模型

### Security 表结构

```sql
CREATE TABLE securities (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,  -- 证券代码
    name VARCHAR(100) NOT NULL,          -- 证券名称
    market VARCHAR(10) NOT NULL,         -- 市场代码
    security_type VARCHAR(20),           -- 证券类型
    industry VARCHAR(50),                -- 所属行业
    list_date TIMESTAMP,                 -- 上市日期
    delist_date TIMESTAMP,               -- 退市日期
    is_active INTEGER DEFAULT 1,         -- 是否有效
    pinyin VARCHAR(200),                 -- 拼音简称
    description TEXT,                     -- 描述
    created_at TIMESTAMP,                -- 创建时间
    updated_at TIMESTAMP                 -- 更新时间
);
```

## 定时更新建议

可以设置定时任务定期更新证券信息：

### Windows 任务计划程序

1. 创建批处理文件 `update_securities.bat`:
```batch
@echo off
cd /d C:\Users\Alfred\app\aiqore\aiqore-back
REM 使用 API 接口更新（推荐）
curl -X POST "http://localhost:8000/api/security/update"
```

2. 在任务计划程序中设置每天执行

### Linux Cron

```bash
# 每天凌晨2点更新（使用 API 接口）
0 2 * * * curl -X POST "http://localhost:8000/api/security/update"
```

### Python 定时任务

可以使用 `APScheduler` 等库在应用内实现定时更新。

## 注意事项

1. **首次更新**: 首次更新可能需要较长时间，因为需要获取所有股票信息
2. **QMT 连接**: 确保 QMT 客户端正在运行
3. **数据量**: 全市场股票数量较多，建议分批更新或使用定时任务
4. **错误处理**: 如果更新失败，检查 QMT 连接和日志信息

## 故障排查

### 问题1: 无法导入 xtquant

**解决方案**:
- 确保 QMT 客户端已安装
- 检查 `XT_QUANT_PATH` 配置是否正确
- 确认 `xtquant` 模块在 Python 路径中

### 问题2: 获取股票列表为空

**解决方案**:
- 检查 QMT 客户端是否运行
- 确认账户配置正确
- 查看日志了解详细错误

### 问题3: 更新速度慢

**解决方案**:
- 分批更新（按市场分别更新）
- 使用异步任务处理
- 考虑只更新活跃股票

## 后续优化建议

1. 实现增量更新（只更新变化的证券）
2. 添加证券行业、概念等更多信息
3. 实现证券名称拼音自动生成（已实现）
4. 添加证券状态管理（停牌、退市等）
5. 实现定时自动更新任务
6. 优化基金、ETF等非股票标的的数据获取和展示

## 已知问题和解决方案

### 问题：无法获取基金、ETF等非股票标的

**原因**：板块名称不正确。MiniQMT 使用特定的板块名称，如 "深市ETF"、"沪市ETF" 而不是 "ETF基金"。

**解决方案**：已修复，现在使用正确的板块名称：
- 使用 "深市ETF"、"沪市ETF"、"沪深ETF" 获取ETF基金
- 使用 "深市基金"、"沪市基金"、"沪深基金" 获取基金
- 使用 "沪深转债"、"上证转债" 获取可转债
- 使用 "沪深指数"、"沪市指数" 获取指数
- 系统会自动获取所有可用板块列表，确保获取完整的标的数据

### 问题：Alembic 编码错误

**原因**：Windows 中文系统默认使用 GBK 编码，但配置文件是 UTF-8。

**解决方案**：使用 `alembic_wrapper.py` 脚本运行 Alembic 命令，或参考 `ALEMBIC_ENCODING_FIX.md` 文档。

