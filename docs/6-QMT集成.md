# QMT 集成

## 功能概述

国金 MiniQMT 数据接入，支持：

- 将证券基础信息自动更新到数据库（股票、ETF、基金、债券、期货、期权、指数等）
- 实时行情、K 线、股票搜索
- 账户与持仓同步（通过交易 API）

### 支持的标的类型

- 股票：沪深 A/B 股、创业板等
- ETF/基金：沪深/深市/沪市 ETF、基金
- 债券：沪深/沪市债券、转债
- 指数：沪深/沪市指数
- 期货：上期所、大商所、郑商所、中金所、能源中心
- 期权：上证/深证期权
- 其他：连续合约、港交所等

## 配置

### 环境变量

在 `.env` 中配置（或使用 `app/config.py` 默认值）：

```env
XT_QUANT_PATH=C:\国金证券QMT交易端\userdata_mini
XT_QUANT_ACCT=39271919
```

### 客户端要求

- 已安装国金 QMT 客户端
- MiniQMT 已启动
- `xtquant` 模块可用（一般随 QMT 安装）

## 使用方式

### 更新证券基础信息

**通过 API（推荐）：**

```bash
# 全部市场
curl -X POST "http://localhost:8000/api/security/update"

# 指定市场
curl -X POST "http://localhost:8000/api/security/update?market=SH"
curl -X POST "http://localhost:8000/api/security/update?market=SZ"
```

接口可能返回任务 ID（异步），使用 `GET /api/task/{task_id}` 查询进度。前端「从 QMT 更新」即调用此接口并轮询状态。

**脚本方式：**

```bash
uv run python -c "from app.database import SessionLocal; from app.services.security_service import security_service; db = SessionLocal(); result = security_service.update_securities_from_qmt(db, market=None); print(result); db.close()"
```

### 查询与搜索

- 列表：`GET /api/security/list`，可选 query: market, limit, offset
- 搜索：`GET /api/security/search?keyword=平安`
- 详情：`GET /api/security/000001.SZ`

### 行情接口说明

- `/api/market/quote`：从数据库补全证券名称
- `/api/market/search`：优先数据库，无结果时再走 QMT

## 数据模型（证券表）

证券采用主表 + 数据源外表 + 子表结构：

- **主表 securities**：symbol、name、market、security_type、industry、list_date、delist_date、is_active、pinyin、abbreviation、description、created_at、updated_at。与具体数据源解耦。
- **数据源外表 security_source_qmt**：存放 QMT 标识与原始数据。字段：instrument_type、exchange_id、product_id、currency_id、raw_data（get_instrument_detail 完整返回）、updated_at。同一证券可对应多种数据源（后续可加 security_source_xxx）。
- **子表**：security_trading_rules（tick_size、lot_size、price_tick）、security_quote_snapshot（涨跌停价、昨收、最新价、成交量等）、以及按类型的 security_stock / security_fund / security_bond / security_convertible / security_option / security_future。

QMT 同步时：写主表后写 security_source_qmt，再写交易规则、行情快照与对应类型子表。列表/详情 API 仅查主表；若需子表或 QMT 原始数据，可通过 ORM relationship（如 security.source_qmt、security.quote_snapshot）加载。

建表与迁移见 Alembic 迁移 001、002、003，或 `init_db.py`。

## 定时更新建议

- Windows：任务计划程序执行 `curl -X POST "http://localhost:8000/api/security/update"`
- Linux：cron 例如 `0 2 * * * curl -X POST "http://localhost:8000/api/security/update"`
- 或应用内使用 APScheduler 等定时调用更新逻辑

## 故障排查

- **无法导入 xtquant**：检查 QMT 是否安装、`XT_QUANT_PATH` 及 Python 路径
- **股票列表为空**：确认 QMT 与 MiniQMT 已运行、账户配置正确，查看日志
- **更新慢**：按市场分批（market=SH/SZ）、使用异步任务、仅更新活跃标的

## 已知问题与说明

- 基金/ETF 等需使用正确板块名（如「深市ETF」「沪市ETF」），系统已按 MiniQMT 板块名适配
- 首次全量更新耗时较长；建议在 QMT 运行稳定时执行，并配合异步任务与前端进度展示

更多实现细节见 `app/services/qmt_service.py`、`app/services/security_service.py` 及 [7-异步任务](./7-异步任务.md)。
