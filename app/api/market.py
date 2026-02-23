"""行情API"""
from fastapi import APIRouter, Query, Depends
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
    获取K线/分时数据。默认直接读取本地 data 目录下的 parquet（1d/1w/1M 为 daily/weekly/monthly.parquet，1m 单日为 ticks/YYYYMMDD.parquet）；
    无数据或 force_update=true 时从数据源拉取并写入 parquet 后返回。
    """
    from datetime import datetime, timedelta
    from app.services.data_source.cache import get_daily, get_weekly, get_monthly, get_ticks
    from app.services.data_source import get_default_qmt_adapter
    from app.services.security_service import security_service

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

    if period in ("1d", "1w", "1M"):
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type
        adapter = get_default_qmt_adapter()
        if period == "1d":
            data = get_daily(security_type, symbol, start_d, end_d, force_update=force_update, adapter=adapter)
        elif period == "1w":
            data = get_weekly(security_type, symbol, start_d, end_d, force_update=force_update, adapter=adapter)
        else:
            data = get_monthly(security_type, symbol, start_d, end_d, force_update=force_update, adapter=adapter)
        return {"code": 0, "data": data, "message": "success"}

    if period == "1m":
        trade_date = (end_d or start_d or datetime.now().strftime("%Y-%m-%d")) if (start_d or end_d) else datetime.now().strftime("%Y-%m-%d")
        security_type = "股票"
        sec = security_service.get_security_by_symbol(db, symbol)
        if sec and sec.security_type:
            security_type = sec.security_type
        adapter = get_default_qmt_adapter()
        data = get_ticks(security_type, symbol, trade_date, force_update=force_update, adapter=adapter)
        return {"code": 0, "data": data, "message": "success"}

    data = market_service.get_kline_data(symbol, period, count, start_date, end_date)
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

