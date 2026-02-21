"""数据源连接 API：增删查改，支持 QMT 参数化与行情源/交易源角色"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.data_source_connection import DataSourceConnection
from app.services.data_source.sync import get_adapter_for_connection

router = APIRouter(prefix="", tags=["数据源连接"])


# ---------- Pydantic 模型 ----------


class DataSourceConnectionBase(BaseModel):
    """数据源连接基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    source_type: str = Field(..., description="数据源类型: qmt, joinquant, tushare")
    is_active: bool = True
    is_quote_source: bool = False
    is_trading_source: bool = False
    # QMT/miniQMT：连接仅用 xt_quant_path、xt_quant_acct；host/port/user/password 为预留
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    xt_quant_path: Optional[str] = None
    xt_quant_acct: Optional[str] = None
    description: Optional[str] = None


class DataSourceConnectionCreate(DataSourceConnectionBase):
    """创建数据源连接"""
    pass


class DataSourceConnectionUpdate(BaseModel):
    """更新数据源连接（全部可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_quote_source: Optional[bool] = None
    is_trading_source: Optional[bool] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    xt_quant_path: Optional[str] = None
    xt_quant_acct: Optional[str] = None
    description: Optional[str] = None


def _model_to_item(m: DataSourceConnection) -> dict:
    """ORM 转响应字典（密码不返回）"""
    return {
        "id": m.id,
        "name": m.name,
        "source_type": m.source_type,
        "is_active": m.is_active,
        "is_quote_source": m.is_quote_source,
        "is_trading_source": m.is_trading_source,
        "host": m.host,
        "port": m.port,
        "user": m.user,
        "password": None,  # 不返回明文密码
        "xt_quant_path": m.xt_quant_path,
        "xt_quant_acct": m.xt_quant_acct,
        "description": m.description,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.get("/list")
async def list_connections(
    source_type: Optional[str] = Query(None, description="按数据源类型筛选"),
    is_active: Optional[bool] = Query(None, description="按是否启用筛选"),
    db: Session = Depends(get_db),
):
    """获取数据源连接列表，支持按类型、启用状态筛选"""
    q = db.query(DataSourceConnection)
    if source_type is not None:
        q = q.filter(DataSourceConnection.source_type == source_type)
    if is_active is not None:
        q = q.filter(DataSourceConnection.is_active == is_active)
    rows = q.order_by(DataSourceConnection.id).all()
    items = [_model_to_item(r) for r in rows]
    return {"code": 0, "data": {"items": items, "total": len(items)}, "message": "success"}


@router.post("/connections")
async def create_connection(body: DataSourceConnectionCreate, db: Session = Depends(get_db)):
    """新建数据源连接"""
    if body.source_type not in ("qmt", "joinquant", "tushare"):
        raise HTTPException(status_code=400, detail="source_type 须为 qmt、joinquant、tushare 之一")
    # miniQMT 为本地连接，不需要 host/port，不设默认端口
    conn = DataSourceConnection(
        name=body.name,
        source_type=body.source_type,
        is_active=body.is_active,
        is_quote_source=body.is_quote_source,
        is_trading_source=body.is_trading_source,
        host=body.host,
        port=body.port,
        user=body.user,
        password=body.password,
        xt_quant_path=body.xt_quant_path,
        xt_quant_acct=body.xt_quant_acct,
        description=body.description,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"code": 0, "data": _model_to_item(conn), "message": "success"}


@router.get("/connections/{connection_id}")
async def get_connection(connection_id: int, db: Session = Depends(get_db)):
    """获取单条数据源连接"""
    conn = db.query(DataSourceConnection).filter(DataSourceConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")
    return {"code": 0, "data": _model_to_item(conn), "message": "success"}


@router.put("/connections/{connection_id}")
async def update_connection(
    connection_id: int,
    body: DataSourceConnectionUpdate,
    db: Session = Depends(get_db),
):
    """更新数据源连接"""
    conn = db.query(DataSourceConnection).filter(DataSourceConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")
    update_data = body.model_dump(exclude_unset=True)
    if body.source_type is not None and body.source_type not in ("qmt", "joinquant", "tushare"):
        raise HTTPException(status_code=400, detail="source_type 须为 qmt、joinquant、tushare 之一")
    for k, v in update_data.items():
        setattr(conn, k, v)
    db.commit()
    db.refresh(conn)
    return {"code": 0, "data": _model_to_item(conn), "message": "success"}


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """删除数据源连接"""
    conn = db.query(DataSourceConnection).filter(DataSourceConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")
    db.delete(conn)
    db.commit()
    return {"code": 0, "data": None, "message": "success"}


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: int, db: Session = Depends(get_db)):
    """测试数据源连接有效性（QMT 会尝试连接 xtdata，聚宽/Tushare 暂不支持）"""
    conn = db.query(DataSourceConnection).filter(DataSourceConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")
    try:
        adapter = get_adapter_for_connection(conn)
        ok, msg = adapter.test_connection()
        return {"code": 0, "data": {"ok": ok, "message": msg}, "message": "success"}
    except Exception as e:
        return {"code": 0, "data": {"ok": False, "message": str(e)}, "message": "success"}


# ---------- 接口调试（按数据源类型提供独立能力，当前仅 miniQMT） ----------


def _require_qmt_connection(connection_id: int, db: Session) -> DataSourceConnection:
    """获取连接并校验为 qmt 类型，否则抛 400/404。"""
    conn = db.query(DataSourceConnection).filter(DataSourceConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")
    if conn.source_type != "qmt":
        raise HTTPException(status_code=400, detail="接口调试当前仅支持 miniQMT 类型数据源")
    return conn


class DebugStocksInSectorBody(BaseModel):
    """按板块取股票列表"""
    sector: str = Field(..., min_length=1, description="板块名称，如 沪深A股")


class DebugInstrumentDetailBody(BaseModel):
    """标的详情"""
    symbol: str = Field(..., min_length=1, description="标的代码，如 000001.SZ")


class DebugMarketDataBody(BaseModel):
    """K 线数据"""
    symbol: str = Field(..., min_length=1, description="标的代码")
    period: str = Field("1d", description="周期：1m/1d 等")
    count: int = Field(100, ge=1, le=2000, description="条数")


class DebugRealtimeQuoteBody(BaseModel):
    """实时行情"""
    symbols: List[str] = Field(..., min_length=1, max_length=50, description="标的代码列表")


class DebugStockListBody(BaseModel):
    """证券列表（可选按市场、板块过滤）"""
    market: Optional[str] = Field(None, description="市场：SH/SZ/BJ，不传为全部")
    sector: Optional[str] = Field(None, description="板块名称，不传则返回全量/按 market 过滤")


class DebugPositionsBody(BaseModel):
    """持仓查询"""
    account_id: str = Field(..., min_length=1, description="资金账号")


class DebugAccountInfoBody(BaseModel):
    """账户信息"""
    account_id: str = Field(..., min_length=1, description="资金账号")


class DebugSearchStocksBody(BaseModel):
    """股票搜索"""
    keyword: str = Field(..., min_length=1, description="关键词（代码或名称）")


@router.get("/connections/{connection_id}/debug/sectors")
async def debug_sectors(connection_id: int, db: Session = Depends(get_db)):
    """[miniQMT] 获取板块列表"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    sectors = adapter.get_sector_list()
    return {"code": 0, "data": {"sectors": sectors}, "message": "success"}


@router.post("/connections/{connection_id}/debug/stocks-in-sector")
async def debug_stocks_in_sector(
    connection_id: int,
    body: DebugStocksInSectorBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取指定板块下的股票列表"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    stocks = adapter.get_stock_list_in_sector(body.sector, market=None)
    return {"code": 0, "data": {"sector": body.sector, "stocks": stocks, "total": len(stocks)}, "message": "success"}


@router.post("/connections/{connection_id}/debug/instrument-detail")
async def debug_instrument_detail(
    connection_id: int,
    body: DebugInstrumentDetailBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取标的详情"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    detail = adapter.get_instrument_detail(body.symbol)
    return {"code": 0, "data": {"symbol": body.symbol, "detail": detail}, "message": "success"}


@router.post("/connections/{connection_id}/debug/market-data")
async def debug_market_data(
    connection_id: int,
    body: DebugMarketDataBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取 K 线数据"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    rows = adapter.get_market_data(body.symbol, period=body.period, count=body.count)
    return {"code": 0, "data": {"symbol": body.symbol, "period": body.period, "rows": rows or []}, "message": "success"}


@router.post("/connections/{connection_id}/debug/realtime-quote")
async def debug_realtime_quote(
    connection_id: int,
    body: DebugRealtimeQuoteBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取实时行情"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    quotes = adapter.get_realtime_quote(body.symbols)
    return {"code": 0, "data": {"quotes": quotes or {}}, "message": "success"}


@router.post("/connections/{connection_id}/debug/stock-list")
async def debug_stock_list(
    connection_id: int,
    body: DebugStockListBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取证券列表（可选 market、sector 过滤）"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    stocks = adapter.get_stock_list(market=body.market, sector=body.sector)
    return {"code": 0, "data": {"stocks": stocks or [], "total": len(stocks or [])}, "message": "success"}


@router.post("/connections/{connection_id}/debug/positions")
async def debug_positions(
    connection_id: int,
    body: DebugPositionsBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 查询指定资金账号持仓"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    positions = adapter.get_positions(body.account_id)
    return {"code": 0, "data": {"account_id": body.account_id, "positions": positions or [], "total": len(positions or [])}, "message": "success"}


@router.post("/connections/{connection_id}/debug/account-info")
async def debug_account_info(
    connection_id: int,
    body: DebugAccountInfoBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 获取账户信息"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    info = adapter.get_account_info(body.account_id)
    return {"code": 0, "data": {"account_id": body.account_id, "info": info}, "message": "success"}


@router.post("/connections/{connection_id}/debug/search-stocks")
async def debug_search_stocks(
    connection_id: int,
    body: DebugSearchStocksBody,
    db: Session = Depends(get_db),
):
    """[miniQMT] 按关键词搜索股票"""
    conn = _require_qmt_connection(connection_id, db)
    adapter = get_adapter_for_connection(conn)
    results = adapter.search_stocks(body.keyword)
    return {"code": 0, "data": {"keyword": body.keyword, "stocks": results or [], "total": len(results or [])}, "message": "success"}
