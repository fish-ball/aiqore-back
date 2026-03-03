"""行情API"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.market_service import market_service
from app.database import get_db

router = APIRouter(prefix="/api/market", tags=["行情"])


@router.get("/quote")
async def get_realtime_quote(
    symbols: str = Query(..., description="证券代码，多个用逗号分隔"),
    db: Session = Depends(get_db)
):
    """
    获取实时行情
    
    Args:
        symbols: 证券代码，如 '000001.SZ,600000.SH'
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    quotes = market_service.get_realtime_quote(symbol_list, db)
    return {"code": 0, "data": list(quotes.values()), "message": "success"}


@router.get("/kline")
async def get_kline(
    symbol: str = Query(..., description="证券代码"),
    period: str = Query("1d", description="周期：1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M"),
    count: int = Query(100, description="数据条数"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    force_update: bool = Query(False, description="是否从数据源拉取并更新本地 parquet，默认直接读 parquet"),
    db: Session = Depends(get_db),
):
    """
    获取K线/分时数据。
    - 当 `force_update=false` 时：直接读取本地 data 目录下的 parquet（1d/1w/1M 为 daily/weekly/monthly.parquet，1m 单日为 ticks/YYYYMMDD.parquet）；
    - 当 `force_update=true` 时：提交对应 Celery 任务更新数据并返回 task_id，由前端轮询任务状态后再调用本接口获取数据。
    """
    from datetime import datetime, timedelta
    from app.services.data_source.cache import get_daily, get_weekly, get_monthly, get_ticks
    from app.services.data_source import get_default_qmt_adapter
    from app.services.security_service import security_service
    from app.tasks.security_tasks import (
        task_update_single_security_kdata,
        task_update_single_security_tick_for_date,
    )

    # 缺省 start_date/end_date 时返回全部 K 线，由前端控制显示范围
    end_d = end_date
    start_d = start_date
    if start_d is not None or end_d is not None:
        if not end_d:
            end_d = datetime.now().strftime("%Y-%m-%d")
        if not start_d and period in ("1d", "1w", "1M"):
            end_dt = datetime.strptime(end_d, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=min(365 * 2, max(1, count)))
            start_d = start_dt.strftime("%Y-%m-%d")

    # 日/周/月 K 线
    if period in ("1d", "1w", "1M"):
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type

        if force_update:
            task = task_update_single_security_kdata.delay(
                symbol=symbol,
                security_type=security_type,
                period=period,
                start_date=start_d,
                end_date=end_d,
                source_type="qmt",
                source_id=None,
                force_update=False,
            )
            return {
                "code": 0,
                "data": {
                    "task_id": task.id,
                    "status": "PENDING",
                },
                "message": "任务已提交，正在后台处理",
            }

        adapter = get_default_qmt_adapter()
        if period == "1d":
            data = get_daily(security_type, symbol, start_d, end_d, force_update=False, adapter=adapter)
        elif period == "1w":
            data = get_weekly(security_type, symbol, start_d, end_d, force_update=False, adapter=adapter)
        else:
            data = get_monthly(security_type, symbol, start_d, end_d, force_update=False, adapter=adapter)
        return {"code": 0, "data": data, "message": "success"}

    # 1 分钟分时（按单日 ticks）
    if period == "1m":
        trade_date = (end_d or start_d or datetime.now().strftime("%Y-%m-%d")) if (start_d or end_d) else datetime.now().strftime("%Y-%m-%d")
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type

        if force_update:
            task = task_update_single_security_tick_for_date.delay(
                symbol=symbol,
                trade_date=trade_date,
                security_type=security_type,
                source_type="qmt",
                source_id=None,
                force_update=False,
            )
            return {
                "code": 0,
                "data": {
                    "task_id": task.id,
                    "status": "PENDING",
                },
                "message": "任务已提交，正在后台处理",
            }

        adapter = get_default_qmt_adapter()
        data = get_ticks(security_type, symbol, trade_date, force_update=False, adapter=adapter)
        return {"code": 0, "data": data, "message": "success"}

    data = market_service.get_kline_data(symbol, period, count, start_date, end_date)
    return {"code": 0, "data": data, "message": "success"}


def _ticks_to_jsonable(rows: list) -> list:
    """将 tick 列表中的 numpy/pandas 类型转为 Python 原生类型，便于 JSON 序列化。"""
    import numpy as np
    result = []
    for rec in rows:
        if not isinstance(rec, dict):
            continue
        out = {}
        for k, v in rec.items():
            if v is None:
                out[k] = None
            elif isinstance(v, np.ndarray):
                out[k] = [_scalar_to_native(x) for x in v]
            elif isinstance(v, list):
                out[k] = [_scalar_to_native(x) for x in v]
            elif hasattr(v, "item") and getattr(v, "ndim", 0) == 0:
                out[k] = v.item()
            else:
                out[k] = _scalar_to_native(v)
        result.append(out)
    return result


def _scalar_to_native(x):
    """单个值转为 Python 原生类型（仅处理标量，不处理数组）。"""
    import numpy as np
    if x is None:
        return None
    if isinstance(x, np.ndarray):
        return [_scalar_to_native(y) for y in x]
    if hasattr(x, "item") and getattr(x, "ndim", 0) == 0:
        return x.item()
    if isinstance(x, (np.integer, np.int64, np.int32)):
        return int(x)
    if isinstance(x, (np.floating, np.float64, np.float32)):
        return float(x)
    return x


@router.get("/ticks")
async def get_ticks(
    symbol: str = Query(..., description="证券代码"),
    trade_date: str = Query(..., description="交易日，格式：YYYY-MM-DD 或 YYYYMMDD"),
    force_update: bool = Query(False, description="是否从数据源拉取并更新本地 parquet"),
    db: Session = Depends(get_db),
):
    """
    获取指定交易日的分笔数据。
    - 当 `force_update=false` 时：直接从本地 parquet 读取并返回。
    - 当 `force_update=true` 时：提交 Celery 任务拉取并写入 parquet，返回 task_id。
    """
    from app.services.data_source.cache import get_ticks as cache_get_ticks
    from app.services.data_source import get_default_qmt_adapter
    from app.services.security_service import security_service
    from app.tasks.security_tasks import task_update_single_security_tick_for_date

    security_type = "股票"
    sec = security_service.get_security_by_symbol(db, symbol)
    if sec and sec.security_type:
        security_type = sec.security_type

    if force_update:
        task = task_update_single_security_tick_for_date.delay(
            symbol=symbol,
            trade_date=trade_date,
            security_type=security_type,
            source_type="qmt",
            source_id=None,
            force_update=False,
        )
        return {
            "code": 0,
            "data": {
                "task_id": task.id,
                "status": "PENDING",
            },
            "message": "任务已提交，正在后台处理",
        }

    adapter = get_default_qmt_adapter()
    data = cache_get_ticks(security_type, symbol, trade_date, force_update=False, adapter=adapter)
    data = _ticks_to_jsonable(data)
    return {"code": 0, "data": data, "message": "success"}


@router.get("/search")
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """
    搜索股票
    """
    stocks = market_service.search_stocks(keyword, db)
    return {"code": 0, "data": stocks, "message": "success"}

