"""分析API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["分析"])


@router.get("/account/{account_id}/summary")
async def get_account_summary(account_id: int, db: Session = Depends(get_db)):
    """获取账户汇总信息"""
    summary = analysis_service.get_account_summary(db, account_id)
    return {"code": 0, "data": summary, "message": "success"}


@router.get("/account/{account_id}/positions")
async def get_position_analysis(account_id: int, db: Session = Depends(get_db)):
    """获取持仓分析"""
    positions = analysis_service.get_position_analysis(db, account_id)
    return {"code": 0, "data": positions, "message": "success"}


@router.get("/account/{account_id}/trade-stats")
async def get_trade_statistics(
    account_id: int,
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """获取交易统计"""
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    stats = analysis_service.get_trade_statistics(db, account_id, start, end)
    return {"code": 0, "data": stats, "message": "success"}


@router.get("/account/{account_id}/profit-trend")
async def get_profit_loss_trend(
    account_id: int,
    days: int = Query(30, description="天数"),
    db: Session = Depends(get_db)
):
    """获取盈亏趋势"""
    trend = analysis_service.get_profit_loss_trend(db, account_id, days)
    return {"code": 0, "data": trend, "message": "success"}

