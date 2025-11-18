"""交易API"""
from fastapi import APIRouter, Depends, HTTPException
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
    
    return {"code": 0, "data": account, "message": "success"}


@router.get("/accounts")
async def get_accounts(db: Session = Depends(get_db)):
    """获取所有账户"""
    accounts = db.query(Account).filter(Account.is_active == 1).all()
    return {"code": 0, "data": accounts, "message": "success"}


@router.get("/account/{account_id}")
async def get_account(account_id: int, db: Session = Depends(get_db)):
    """获取账户详情"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    return {"code": 0, "data": account, "message": "success"}


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


@router.get("/account/{account_id}/positions")
async def get_positions(account_id: int, db: Session = Depends(get_db)):
    """获取持仓列表"""
    positions = db.query(Position).filter(
        Position.account_id == account_id,
        Position.quantity > 0
    ).all()
    return {"code": 0, "data": positions, "message": "success"}


@router.post("/account/{account_id}/positions/sync")
async def sync_positions(account_id: int, db: Session = Depends(get_db)):
    """同步持仓信息（从QMT）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    positions = trade_service.sync_positions(db, account.account_id)
    return {"code": 0, "data": positions, "message": "success"}


@router.get("/account/{account_id}/trades")
async def get_trades(
    account_id: int,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取交易记录"""
    trades = db.query(Trade).filter(
        Trade.account_id == account_id
    ).order_by(Trade.trade_time.desc()).offset(offset).limit(limit).all()
    
    total = db.query(Trade).filter(Trade.account_id == account_id).count()
    
    return {
        "code": 0,
        "data": {
            "items": trades,
            "total": total,
            "limit": limit,
            "offset": offset
        },
        "message": "success"
    }


@router.post("/account/{account_id}/trade")
async def record_trade(
    account_id: int,
    trade_data: TradeRecord,
    db: Session = Depends(get_db)
):
    """记录交易"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    
    direction = TradeDirection.BUY if trade_data.direction == "买入" else TradeDirection.SELL
    
    trade = trade_service.record_trade(
        db=db,
        account_id=account_id,
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
    
    return {"code": 0, "data": trade, "message": "success"}

