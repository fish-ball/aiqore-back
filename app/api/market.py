"""行情API"""
from fastapi import APIRouter, Query
from typing import List, Optional
from app.services.market_service import market_service

router = APIRouter(prefix="/api/market", tags=["行情"])


@router.get("/quote")
async def get_realtime_quote(symbols: str = Query(..., description="证券代码，多个用逗号分隔")):
    """
    获取实时行情
    
    Args:
        symbols: 证券代码，如 '000001.SZ,600000.SH'
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    quotes = market_service.get_realtime_quote(symbol_list)
    return {"code": 0, "data": quotes, "message": "success"}


@router.get("/kline")
async def get_kline(
    symbol: str = Query(..., description="证券代码"),
    period: str = Query("1d", description="周期：1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M"),
    count: int = Query(100, description="数据条数"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取K线数据
    """
    data = market_service.get_kline_data(symbol, period, count, start_date, end_date)
    return {"code": 0, "data": data, "message": "success"}


@router.get("/search")
async def search_stocks(keyword: str = Query(..., description="搜索关键词")):
    """
    搜索股票
    """
    stocks = market_service.search_stocks(keyword)
    return {"code": 0, "data": stocks, "message": "success"}

