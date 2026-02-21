# API 接口

## 文档地址

启动后端后：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 接口概览

### 账户与交易（/api/trade）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/trade/account | 创建账户 |
| GET | /api/trade/accounts | 获取所有账户 |
| GET | /api/trade/account/{account_id} | 获取账户详情 |
| POST | /api/trade/account/{account_id}/sync | 从 QMT 同步账户 |
| GET | /api/trade/account/{account_id}/trades | 交易记录 |
| POST | /api/trade/account/{account_id}/trade | 记录一笔交易 |
| GET | /api/trade/account/{account_id}/positions | 持仓列表 |
| POST | /api/trade/account/{account_id}/positions/sync | 从 QMT 同步持仓 |

### 行情（/api/market）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/market/quote | 实时行情，query: symbols=000001.SZ,600000.SH |
| GET | /api/market/kline | K 线，query: symbol, period, count |
| GET | /api/market/search | 搜索股票，query: keyword |

### 分析（/api/analysis）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/analysis/account/{account_id}/summary | 账户汇总 |
| GET | /api/analysis/account/{account_id}/positions | 持仓分析 |
| GET | /api/analysis/account/{account_id}/trade-stats | 交易统计 |
| GET | /api/analysis/account/{account_id}/profit-trend | 盈亏趋势，query: days |

### 证券（/api/security）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/security/update | 从数据源更新证券（异步），query: market, sector, source_type=qmt, source_id（可选） |
| GET | /api/security/list | 证券列表，query: market, sector, limit, offset |
| GET | /api/security/search | 搜索证券，query: keyword, limit |
| GET | /api/security/{symbol} | 证券详情 |

### 数据源连接（/api/data-source）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/data-source/list | 连接列表，query: source_type, is_active |
| POST | /api/data-source/connections | 新建连接（body: name, source_type, QMT 字段等） |
| GET | /api/data-source/connections/{id} | 单条连接 |
| PUT | /api/data-source/connections/{id} | 更新连接 |
| DELETE | /api/data-source/connections/{id} | 删除连接 |
| POST | /api/data-source/connections/{id}/test | 测试连接有效性（QMT 尝试连接 xtdata） |

**接口调试（当前仅 miniQMT 类型连接支持）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/data-source/connections/{id}/debug/sectors | 获取板块列表 |
| POST | /api/data-source/connections/{id}/debug/stocks-in-sector | 获取指定板块股票，body: sector |
| POST | /api/data-source/connections/{id}/debug/instrument-detail | 获取标的详情，body: symbol |
| POST | /api/data-source/connections/{id}/debug/market-data | 获取 K 线，body: symbol, period, count |
| POST | /api/data-source/connections/{id}/debug/realtime-quote | 获取实时行情，body: symbols（数组） |
| POST | /api/data-source/connections/{id}/debug/stock-list | 获取证券列表，body: market（可选）, sector（可选） |
| POST | /api/data-source/connections/{id}/debug/positions | 查询持仓，body: account_id |
| POST | /api/data-source/connections/{id}/debug/account-info | 获取账户信息，body: account_id |
| POST | /api/data-source/connections/{id}/debug/search-stocks | 按关键词搜索股票，body: keyword |

### 板块（/api/sector）

板块相关接口见 Swagger/ReDoc，前缀 `/api/sector`。

### 异步任务状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/task/{task_id} | 查询任务状态（如证券更新任务） |

### 调试（仅 DEBUG）

前缀 `/api/debug`，仅在 `settings.DEBUG` 为 True 时注册。

## 请求示例

### 创建账户

```bash
curl -X POST "http://localhost:8000/api/trade/account" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "123456", "name": "我的投资账户", "initial_capital": 100000}'
```

### 记录交易

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

### 实时行情

```bash
curl "http://localhost:8000/api/market/quote?symbols=000001.SZ,600000.SH"
```

### 账户汇总

```bash
curl "http://localhost:8000/api/analysis/account/1/summary"
```

### 提交证券更新任务（异步，经数据源抽象层）

```bash
curl -X POST "http://localhost:8000/api/security/update?market=SH"
# 可选: sector=板块名, source_type=qmt, source_id=连接ID（不传则用默认连接）
# 返回 task_id，使用 GET /api/task/{task_id} 查询进度
```

接口变更以实际代码与 Swagger/ReDoc 为准；新增或修改接口后请同步更新本文档（见 [文档维护说明](./README.md#文档维护说明)）。
