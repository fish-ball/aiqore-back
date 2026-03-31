"""交易API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.database import get_db
from app.services.trade_service import trade_service
from app.models.account import Account
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.models.position import Position

router = APIRouter(prefix="/api/trade", tags=["交易"])


class AccountCreate(BaseModel):
    """创建账户请求"""
    account_id: str
    name: Optional[str] = None
    initial_capital: float = 0


class AccountUpdate(BaseModel):
    """更新账户请求（部分字段）"""
    account_id: Optional[str] = None
    name: Optional[str] = None
    initial_capital: Optional[float] = None
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None


class TradeRecord(BaseModel):
    """交易记录请求"""
    symbol: str
    symbol_name: Optional[str] = None
    direction: str  # "买入" 或 "卖出"
    price: float
    quantity: int
    trade_time: datetime
    commission: float = 0
    tax: float = 0
    remark: Optional[str] = None


class TradeCreate(TradeRecord):
    """创建交易请求（包含账户ID）"""
    account_id: int


class TradeUpdate(BaseModel):
    """更新交易请求（部分字段）"""
    account_id: Optional[int] = None
    symbol: Optional[str] = None
    symbol_name: Optional[str] = None
    direction: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    trade_time: Optional[datetime] = None
    commission: Optional[float] = None
    tax: Optional[float] = None
    remark: Optional[str] = None


@router.post("/account")
async def create_account(account_data: AccountCreate, db: Session = Depends(get_db)):
    """创建账户"""
    # 检查账户是否已存在
    existing = db.query(Account).filter(Account.account_id == account_data.account_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="账户已存在")
    
    account = Account(
        account_id=account_data.account_id,
        name=account_data.name or f"账户-{account_data.account_id}",
        initial_capital=Decimal(str(account_data.initial_capital)),
        current_balance=Decimal(str(account_data.initial_capital)),
        available_balance=Decimal(str(account_data.initial_capital))
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/account")
async def get_accounts(
    page: int = Query(default=1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(default=10, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
):
    """获取账户列表（分页，单数资源）"""
    query = db.query(Account).filter(Account.is_active == 1)
    total = query.count()
    offset = (page - 1) * page_size
    accounts = query.order_by(Account.id.desc()).offset(offset).limit(page_size).all()
    return {
        "count": total,
        "results": accounts,
    }


@router.get("/account/{account_id}")
async def get_account(account_id: int, db: Session = Depends(get_db)):
    """获取账户详情"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    return account


@router.patch("/account/{account_id}")
async def update_account(account_id: int, account_data: AccountUpdate, db: Session = Depends(get_db)):
    """更新账户"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    payload = account_data.model_dump(exclude_unset=True)

    if "account_id" in payload:
        existing = db.query(Account).filter(
            Account.account_id == payload["account_id"],
            Account.id != account_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="账户ID已存在")
        account.account_id = payload["account_id"]
    if "name" in payload:
        account.name = payload["name"]
    if "initial_capital" in payload:
        account.initial_capital = Decimal(str(payload["initial_capital"]))
    if "current_balance" in payload:
        account.current_balance = Decimal(str(payload["current_balance"]))
    if "available_balance" in payload:
        account.available_balance = Decimal(str(payload["available_balance"]))

    db.commit()
    db.refresh(account)
    return account


@router.post("/account/{account_id}/sync")
async def sync_account(account_id: int, db: Session = Depends(get_db)):
    """同步账户信息（从QMT）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    synced_account = trade_service.sync_account(db, account.account_id)
    if not synced_account:
        raise HTTPException(status_code=500, detail="同步失败")
    
    return {"code": 0, "data": synced_account, "message": "success"}


@router.delete("/account/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账户（硬删除）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    db.delete(account)
    db.commit()
    return {"id": account_id, "deleted": True}


@router.get("/position")
async def get_position_list(
    page: int = Query(default=1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(default=10, ge=1, le=200, description="每页条数"),
    account_id: Optional[int] = Query(default=None, description="按账户过滤"),
    db: Session = Depends(get_db),
):
    """获取持仓列表（分页，单数资源）"""
    query = db.query(Position).filter(Position.quantity > 0)
    if account_id is not None:
        query = query.filter(Position.account_id == account_id)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Position.id.desc()).offset(offset).limit(page_size).all()
    return {
        "count": total,
        "results": items,
    }


@router.post("/account/{account_id}/positions/sync")
async def sync_positions(account_id: int, db: Session = Depends(get_db)):
    """同步持仓信息（从QMT）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    positions = trade_service.sync_positions(db, account.account_id)
    return {"code": 0, "data": positions, "message": "success"}


@router.get("/trade")
async def get_trade_list(
    page: int = Query(default=1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(default=10, ge=1, le=200, description="每页条数"),
    account_id: Optional[int] = Query(default=None, description="按账户过滤"),
    db: Session = Depends(get_db),
):
    """获取交易记录列表（分页，单数资源）"""
    query = db.query(Trade)
    if account_id is not None:
        query = query.filter(Trade.account_id == account_id)
    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Trade.trade_time.desc()).offset(offset).limit(page_size).all()
    return {
        "count": total,
        "results": items,
    }


@router.post("/trade")
async def create_trade(trade_data: TradeCreate, db: Session = Depends(get_db)):
    """创建交易记录（单数资源）"""
    account = db.query(Account).filter(Account.id == trade_data.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    direction = TradeDirection.BUY if trade_data.direction == "买入" else TradeDirection.SELL

    trade = trade_service.record_trade(
        db=db,
        account_id=trade_data.account_id,
        symbol=trade_data.symbol,
        direction=direction,
        price=Decimal(str(trade_data.price)),
        quantity=trade_data.quantity,
        trade_time=trade_data.trade_time,
        symbol_name=trade_data.symbol_name,
        commission=Decimal(str(trade_data.commission)),
        tax=Decimal(str(trade_data.tax)),
        remark=trade_data.remark
    )

    if not trade:
        raise HTTPException(status_code=500, detail="记录交易失败")
    return trade


@router.get("/trade/{trade_id}")
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """获取交易记录详情"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    return trade


@router.patch("/trade/{trade_id}")
async def update_trade(trade_id: int, trade_data: TradeUpdate, db: Session = Depends(get_db)):
    """更新交易记录"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="交易记录不存在")

    payload = trade_data.model_dump(exclude_unset=True)

    if "account_id" in payload:
        account = db.query(Account).filter(Account.id == payload["account_id"]).first()
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        trade.account_id = payload["account_id"]
    if "symbol" in payload:
        trade.symbol = payload["symbol"]
    if "symbol_name" in payload:
        trade.symbol_name = payload["symbol_name"]
    if "direction" in payload:
        trade.direction = TradeDirection.BUY if payload["direction"] == "买入" else TradeDirection.SELL
    if "price" in payload:
        trade.price = Decimal(str(payload["price"]))
    if "quantity" in payload:
        trade.quantity = payload["quantity"]
    if "trade_time" in payload:
        trade.trade_time = payload["trade_time"]
    if "commission" in payload:
        trade.commission = Decimal(str(payload["commission"]))
    if "tax" in payload:
        trade.tax = Decimal(str(payload["tax"]))
    if "remark" in payload:
        trade.remark = payload["remark"]

    # 根据当前价格与数量重算金额相关字段
    amount = Decimal(str(trade.price)) * trade.quantity
    commission = Decimal(str(trade.commission or 0))
    tax = Decimal(str(trade.tax or 0))
    trade.amount = amount
    trade.total_cost = amount + commission + tax

    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/trade/{trade_id}")
async def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """删除交易记录"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="交易记录不存在")
    db.delete(trade)
    db.commit()
    return {"id": trade_id, "deleted": True}



