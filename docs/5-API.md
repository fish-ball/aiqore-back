# API 接口

## 文档地址

启动后端后：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 统一响应格式

除 HTTP 4xx/5xx 外，接口均返回 JSON，结构为：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 0 表示成功，非 0 表示业务失败 |
| data | object / array / null | 业务数据，失败时可为 null 或错误信息 |
| message | string | 提示信息 |

错误时可能直接返回 HTTP 状态码及 FastAPI 默认 body（如 `{"detail": "..."}`）。

**请求传参约定**：GET 请求使用 Query（URL 查询参数）；POST/PUT/PATCH/DELETE 使用 Body JSON，不使用 Query 传业务参数（路径参数如 `{id}` 除外）。

---

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
| GET | /api/market/quote | 实时行情 |
| GET | /api/market/kline | K 线/分时（默认读本地 parquet） |
| GET | /api/market/search | 搜索股票 |

### 分析（/api/analysis）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/analysis/account/{account_id}/summary | 账户汇总 |
| GET | /api/analysis/account/{account_id}/positions | 持仓分析 |
| GET | /api/analysis/account/{account_id}/trade-stats | 交易统计 |
| GET | /api/analysis/account/{account_id}/profit-trend | 盈亏趋势 |

### 证券（/api/security）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/security/update | 从数据源更新证券（异步） |
| POST | /api/security/update-one | 从数据源更新单个证券基础信息（同步） |
| POST | /api/security/update-data | 按指定数据源拉取并补全单个证券的本地缓存数据（全量日/周/月 K 线及分时，按 meta 补全） |
| GET | /api/security/list | 证券列表 |
| GET | /api/security/search | 搜索证券 |
| GET | /api/security/{symbol} | 证券详情 |

### 数据源连接（/api/data-source）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/data-source/list | 连接列表 |
| POST | /api/data-source/connections | 新建连接 |
| GET | /api/data-source/connections/{id} | 单条连接 |
| PUT | /api/data-source/connections/{id} | 更新连接 |
| DELETE | /api/data-source/connections/{id} | 删除连接 |
| POST | /api/data-source/connections/{id}/test | 测试连接 |
| GET | /api/data-source/connections/{id}/debug/sectors | [miniQMT] 板块列表 |
| POST | /api/data-source/connections/{id}/debug/stocks-in-sector | [miniQMT] 指定板块股票 |
| POST | /api/data-source/connections/{id}/debug/instrument-detail | [miniQMT] 标的详情 |
| POST | /api/data-source/connections/{id}/debug/market-data | [miniQMT] K 线 |
| POST | /api/data-source/connections/{id}/debug/realtime-quote | [miniQMT] 实时行情 |
| POST | /api/data-source/connections/{id}/debug/stock-list | [miniQMT] 证券列表 |
| POST | /api/data-source/connections/{id}/debug/positions | [miniQMT] 持仓 |
| POST | /api/data-source/connections/{id}/debug/account-info | [miniQMT] 账户信息 |
| POST | /api/data-source/connections/{id}/debug/search-stocks | [miniQMT] 搜索股票 |

### 板块（/api/sector）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/sector/sync | 从 QMT 同步板块列表 |
| GET | /api/sector/list | 板块列表 |
| GET | /api/sector/statistics | 板块统计 |
| GET | /api/sector/{sector_name} | 板块详情 |

### 异步任务状态

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/task/{task_id} | 查询任务状态（需对接 Celery 结果后端或自建查询接口） |

---

## 详细接口说明

### 一、账户与交易（/api/trade）

#### POST /api/trade/account 创建账户

- **请求**  
  - Body (JSON): `account_id`(string, 必填), `name`(string, 可选), `initial_capital`(number, 可选，默认 0)
- **响应**  
  - `data`: 账户对象（含 id, account_id, name, initial_capital, current_balance, available_balance 等）

#### GET /api/trade/accounts 获取所有账户

- **请求**  
  - 无 Query
- **响应**  
  - `data`: 账户对象数组

#### GET /api/trade/account/{account_id} 获取账户详情

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: 账户对象；404 表示账户不存在

#### POST /api/trade/account/{account_id}/sync 从 QMT 同步账户

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: 同步后的账户信息；404/500 表示账户不存在或同步失败

#### GET /api/trade/account/{account_id}/positions 持仓列表

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: 持仓对象数组（symbol, quantity, cost_price, market_value, profit_loss 等）

#### POST /api/trade/account/{account_id}/positions/sync 从 QMT 同步持仓

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: 持仓对象数组

#### GET /api/trade/account/{account_id}/trades 交易记录

- **请求**  
  - 路径参数: `account_id`(int)  
  - Query: `limit`(int, 默认 100), `offset`(int, 默认 0)
- **响应**  
  - `data`: `{ "items": 交易数组, "total": 总数, "limit": limit, "offset": offset }`

#### POST /api/trade/account/{account_id}/trade 记录一笔交易

- **请求**  
  - 路径参数: `account_id`(int)  
  - Body (JSON): `symbol`, `symbol_name`(可选), `direction`("买入"/"卖出"), `price`, `quantity`, `trade_time`(ISO 8601), `commission`(可选, 默认 0), `tax`(可选, 默认 0), `remark`(可选)
- **响应**  
  - `data`: 交易记录对象

---

### 二、行情（/api/market）

#### GET /api/market/quote 实时行情

- **请求**  
  - Query: `symbols`(string, 必填)，多个代码逗号分隔，如 `000001.SZ,600000.SH`
- **响应**  
  - `data`: 数组，每项为 `{ symbol, name, last_price, open, high, low, pre_close, volume, amount, change, change_percent, time }`

#### GET /api/market/kline K 线/分时

- **请求**  
  - Query: `symbol`(string, 必填), `period`(string, 默认 "1d"，可选 1m/5m/15m/30m/1h/1d/1w/1M), `count`(int, 默认 100), `start_date`(string, 可选, YYYY-MM-DD), `end_date`(string, 可选, YYYY-MM-DD), `force_update`(bool, 默认 false，为 true 时从数据源拉取并更新本地 parquet)
- **响应**  
  - `data`: 数组，每项为 `{ time, date, open, high, low, close, volume, amount }`。1d/1w/1M 默认读本地 parquet；1m 且单日读 ticks/YYYYMMDD.parquet；无数据或 force_update 时从数据源拉取并写入后返回。

#### GET /api/market/search 搜索股票

- **请求**  
  - Query: `keyword`(string, 必填)
- **响应**  
  - `data`: 数组，每项为 `{ symbol, name, market }`

---

### 三、分析（/api/analysis）

#### GET /api/analysis/account/{account_id}/summary 账户汇总

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: `{ account_id, account_name, initial_capital, current_balance, available_balance, market_value, total_asset, total_profit_loss, total_profit_loss_ratio, position_count, trade_count, update_time }`，无账户时为空对象

#### GET /api/analysis/account/{account_id}/positions 持仓分析

- **请求**  
  - 路径参数: `account_id`(int)
- **响应**  
  - `data`: 数组，每项为 `{ symbol, symbol_name, quantity, available_quantity, cost_price, current_price, cost_amount, market_value, profit_loss, profit_loss_ratio, weight }`

#### GET /api/analysis/account/{account_id}/trade-stats 交易统计

- **请求**  
  - 路径参数: `account_id`(int)  
  - Query: `start_date`(string, 可选, YYYY-MM-DD), `end_date`(string, 可选, YYYY-MM-DD)
- **响应**  
  - `data`: `{ total_trades, buy_trades, sell_trades, total_amount, total_commission, total_tax, buy_amount, sell_amount }`

#### GET /api/analysis/account/{account_id}/profit-trend 盈亏趋势

- **请求**  
  - 路径参数: `account_id`(int)  
  - Query: `days`(int, 默认 30)
- **响应**  
  - `data`: 数组，每项为 `{ date, daily_profit_loss, cumulative_profit_loss }`

---

### 四、证券（/api/security）

#### POST /api/security/update 从数据源更新证券（异步）

- **请求** Body JSON: `market`(string, 可选, SH/SZ), `sector`(string, 可选), `source_type`(string, 默认 "qmt"), `source_id`(int, 可选)
- **响应**
  - `data`: `{ task_id, status: "PENDING" }`
  - 409: 任务已运行中

#### POST /api/security/update-one 从数据源更新单个证券基础信息（同步）

- **请求** Body JSON: `symbol`(string, 必填), `source_type`(string, 默认 "qmt"), `source_id`(int, 可选)
- **响应**
  - 成功: `code: 0`, `data`: `{ success, total, created, updated, errors, message? }`
  - 失败: `code: 1`, `data`: 同上，`message`: 错误说明

#### POST /api/security/update-data 拉取并补全单个证券的本地缓存数据

- **请求** Body JSON: `symbol`(string, 必填), `source_type`(string, 默认 "qmt"), `source_id`(int, 可选，不传则使用默认连接)
- **说明**
  按 metadata.yaml 记录的时间补全尚未下载的数据：全量日线、周线、月线（缺失区间从数据源拉取并写入 parquet）；分时按日线 parquet 中的交易日补全尚未下载的 ticks/YYYYMMDD.parquet。接口执行后 data 目录下会产生对应 parquet 与 metadata.yaml（日期 YYYY-MM-DD，时间 YYYY-MM-DD HH:mm:ss）。若数据源未返回任何 K 线，`data.hint` 会带提示信息。
- **响应**
  - `data`: `{ symbol, daily, weekly, monthly, ticks_dates [, hint ] }`，各为条数/天数；无 K 线时含 `hint` 提示
  - 404: 证券不存在；400: 未找到指定数据源或 source_type 不支持

#### GET /api/security/list 证券列表

- **请求**  
  - Query: `market`(string, 可选), `sector`(string, 可选), `security_type`(string, 可选), `limit`(int, 默认 100), `offset`(int, 默认 0)
- **响应**  
  - `data`: `{ items: 证券数组, total, limit, offset }`，每项含 `id, symbol, name, market, security_type, industry, is_active, abbreviation, created_at, updated_at`

#### GET /api/security/search 搜索证券

- **请求**  
  - Query: `keyword`(string, 必填), `limit`(int, 默认 50)
- **响应**  
  - `data`: 证券数组，每项含 `id, symbol, name, market, security_type, industry, is_active, abbreviation`

#### GET /api/security/{symbol} 证券详情

- **请求**  
  - 路径参数: `symbol`(string)
- **响应**  
  - `data`: `{ id, symbol, name, market, security_type, industry, list_date, delist_date, is_active, pinyin, abbreviation, description, created_at, updated_at }`  
  - 404: 证券不存在

---

### 五、数据源连接（/api/data-source）

#### GET /api/data-source/list 连接列表

- **请求**  
  - Query: `source_type`(string, 可选), `is_active`(bool, 可选)
- **响应**  
  - `data`: `{ items: 连接数组, total }`，每项含 `id, name, source_type, is_active, is_quote_source, is_trading_source, host, port, user, password: null, xt_quant_path, xt_quant_acct, description, created_at, updated_at`

#### POST /api/data-source/connections 新建连接

- **请求**  
  - Body (JSON): `name`(必填), `source_type`(必填, qmt/joinquant/tushare), `is_active`, `is_quote_source`, `is_trading_source`, `host`, `port`, `user`, `password`, `xt_quant_path`, `xt_quant_acct`, `description`
- **响应**  
  - `data`: 连接对象（同上，不含明文 password）

#### GET /api/data-source/connections/{connection_id} 单条连接

- **请求**  
  - 路径参数: `connection_id`(int)
- **响应**  
  - `data`: 连接对象；404: 连接不存在

#### PUT /api/data-source/connections/{connection_id} 更新连接

- **请求**  
  - 路径参数: `connection_id`(int)  
  - Body (JSON): 全部可选，同新建字段
- **响应**  
  - `data`: 更新后的连接对象

#### DELETE /api/data-source/connections/{connection_id} 删除连接

- **请求**  
  - 路径参数: `connection_id`(int)
- **响应**  
  - `data`: null；404: 连接不存在

#### POST /api/data-source/connections/{connection_id}/test 测试连接

- **请求**  
  - 路径参数: `connection_id`(int)
- **响应**  
  - `data`: `{ ok: boolean, message: string }`

#### 调试接口（miniQMT）

- **GET .../debug/sectors**  
  - 响应: `data`: `{ sectors: string[] }`
- **POST .../debug/stocks-in-sector**  
  - Body: `{ sector: string }`  
  - 响应: `data`: `{ sector, stocks, total }`
- **POST .../debug/instrument-detail**  
  - Body: `{ symbol: string }`  
  - 响应: `data`: `{ symbol, detail }`
- **POST .../debug/market-data**  
  - Body: `{ symbol, period, count }`  
  - 响应: `data`: `{ symbol, period, rows }`
- **POST .../debug/realtime-quote**  
  - Body: `{ symbols: string[] }`  
  - 响应: `data`: `{ quotes }`
- **POST .../debug/stock-list**  
  - Body: `{ market?, sector? }`  
  - 响应: `data`: `{ stocks, total }`
- **POST .../debug/positions**  
  - Body: `{ account_id: string }`  
  - 响应: `data`: `{ account_id, positions, total }`
- **POST .../debug/account-info**  
  - Body: `{ account_id: string }`  
  - 响应: `data`: `{ account_id, info }`
- **POST .../debug/search-stocks**  
  - Body: `{ keyword: string }`  
  - 响应: `data`: `{ keyword, stocks, total }`

---

### 六、板块（/api/sector）

#### POST /api/sector/sync 从 QMT 同步板块列表

- **请求**  
  - 无 Body/Query
- **响应**  
  - `code`: 0 或 1，`data`: `{ success, message? }`，`message`: 提示

#### GET /api/sector/list 板块列表

- **请求**  
  - Query: `category`(string, 可选), `market`(string, 可选), `is_active`(int, 默认 1)
- **响应**  
  - `data`: `{ items: 板块数组, total }`，每项含 `id, name, display_name, category, market, description, security_count, is_active, last_sync_at, created_at, updated_at`

#### GET /api/sector/statistics 板块统计

- **请求**  
  - 无 Query
- **响应**  
  - `data`: 统计对象（由 sector_service.get_sector_statistics 返回）

#### GET /api/sector/{sector_name} 板块详情

- **请求**  
  - 路径参数: `sector_name`(string)
- **响应**  
  - `data`: 板块对象（同上单条结构）；404: 板块不存在

---

### 七、异步任务状态

任务由 POST /api/security/update 等提交后返回 `task_id`。查询任务状态需对接 Celery 结果后端（如 Redis）或项目内提供的任务查询接口（若有）。常见响应约定：`{ status: "PENDING"|"STARTED"|"SUCCESS"|"FAILURE", result?: ... }`。

---

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

### K 线/分时（默认读本地 parquet）

```bash
curl "http://localhost:8000/api/market/kline?symbol=000001.SZ&period=1d&count=250"
curl "http://localhost:8000/api/market/kline?symbol=000001.SZ&period=1d&start_date=2024-01-01&end_date=2025-02-22"
curl "http://localhost:8000/api/market/kline?symbol=000001.SZ&period=1m&start_date=2025-02-22&end_date=2025-02-22"
curl "http://localhost:8000/api/market/kline?symbol=000001.SZ&period=1d&start_date=2024-01-01&end_date=2025-02-22&force_update=true"
```

### 提交证券更新任务（异步）

```bash
curl -X POST "http://localhost:8000/api/security/update" -H "Content-Type: application/json" -d "{\"market\":\"SH\"}"
# Body 可选: sector, source_type, source_id；返回 data.task_id，用于查询任务进度
```

### 拉取单证券本地缓存数据

```bash
curl -X POST "http://localhost:8000/api/security/update-data" -H "Content-Type: application/json" -d "{\"symbol\":\"000001.SZ\"}"
# Body 可选: source_type, source_id；返回 data: { symbol, daily, weekly, monthly, ticks_dates }
```

接口变更以实际代码与 Swagger/ReDoc 为准；新增或修改接口后请同步更新本文档（见 [文档维护说明](./README.md#文档维护说明)）。
