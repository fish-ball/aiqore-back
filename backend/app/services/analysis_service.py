"""投资收益分析服务"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.account import Account
from app.models.trade import Trade, TradeDirection
from app.models.position import Position
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class AnalysisService:
    """投资收益分析服务"""
    
    def get_account_summary(self, db: Session, account_id: int) -> Dict[str, Any]:
        """
        获取账户汇总信息
        
        Args:
            db: 数据库会话
            account_id: 账户ID
            
        Returns:
            账户汇总信息
        """
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {}
            
            # 计算总盈亏
            total_profit_loss = account.total_asset - account.initial_capital
            total_profit_loss_ratio = (
                (account.total_asset - account.initial_capital) / account.initial_capital * 100
                if account.initial_capital > 0 else 0
            )
            
            # 统计持仓数量
            position_count = db.query(func.count(Position.id)).filter(
                Position.account_id == account_id,
                Position.quantity > 0
            ).scalar() or 0
            
            # 统计交易次数
            trade_count = db.query(func.count(Trade.id)).filter(
                Trade.account_id == account_id
            ).scalar() or 0
            
            return {
                "account_id": account.id,
                "account_name": account.name,
                "initial_capital": float(account.initial_capital),
                "current_balance": float(account.current_balance),
                "available_balance": float(account.available_balance),
                "market_value": float(account.market_value),
                "total_asset": float(account.total_asset),
                "total_profit_loss": float(total_profit_loss),
                "total_profit_loss_ratio": float(total_profit_loss_ratio),
                "position_count": position_count,
                "trade_count": trade_count,
                "update_time": account.updated_at.isoformat() if account.updated_at else None
            }
        except Exception as e:
            logger.error(f"获取账户汇总失败: {e}")
            return {}
    
    def get_position_analysis(self, db: Session, account_id: int) -> List[Dict[str, Any]]:
        """
        获取持仓分析
        
        Args:
            db: 数据库会话
            account_id: 账户ID
            
        Returns:
            持仓分析列表
        """
        try:
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.quantity > 0
            ).all()
            
            # 获取账户总资产用于计算权重
            account = db.query(Account).filter(Account.id == account_id).first()
            total_asset = float(account.total_asset) if account and account.total_asset > 0 else 1
            
            result = []
            for pos in positions:
                result.append({
                    "symbol": pos.symbol,
                    "symbol_name": pos.symbol_name,
                    "quantity": pos.quantity,
                    "available_quantity": pos.available_quantity,
                    "cost_price": float(pos.cost_price),
                    "current_price": float(pos.current_price),
                    "cost_amount": float(pos.cost_amount),
                    "market_value": float(pos.market_value),
                    "profit_loss": float(pos.profit_loss),
                    "profit_loss_ratio": float(pos.profit_loss_ratio),
                    "weight": float(pos.market_value) / total_asset * 100 if total_asset > 0 else 0
                })
            
            # 按市值排序
            result.sort(key=lambda x: x["market_value"], reverse=True)
            return result
        except Exception as e:
            logger.error(f"获取持仓分析失败: {e}")
            return []
    
    def get_trade_statistics(
        self,
        db: Session,
        account_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取交易统计
        
        Args:
            db: 数据库会话
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易统计信息
        """
        try:
            query = db.query(Trade).filter(Trade.account_id == account_id)
            
            if start_date:
                query = query.filter(Trade.trade_time >= start_date)
            if end_date:
                query = query.filter(Trade.trade_time <= end_date)
            
            trades = query.all()
            
            if not trades:
                return {
                    "total_trades": 0,
                    "buy_trades": 0,
                    "sell_trades": 0,
                    "total_amount": 0,
                    "total_commission": 0,
                    "total_tax": 0
                }
            
            buy_trades = [t for t in trades if t.direction == TradeDirection.BUY]
            sell_trades = [t for t in trades if t.direction == TradeDirection.SELL]
            
            total_amount = sum(float(t.amount) for t in trades)
            total_commission = sum(float(t.commission) for t in trades)
            total_tax = sum(float(t.tax) for t in trades)
            
            return {
                "total_trades": len(trades),
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades),
                "total_amount": total_amount,
                "total_commission": total_commission,
                "total_tax": total_tax,
                "buy_amount": sum(float(t.amount) for t in buy_trades),
                "sell_amount": sum(float(t.amount) for t in sell_trades)
            }
        except Exception as e:
            logger.error(f"获取交易统计失败: {e}")
            return {}
    
    def get_profit_loss_trend(
        self,
        db: Session,
        account_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取盈亏趋势
        
        Args:
            db: 数据库会话
            account_id: 账户ID
            days: 天数
            
        Returns:
            盈亏趋势数据
        """
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return []
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取每日的交易记录
            trades = db.query(Trade).filter(
                Trade.account_id == account_id,
                Trade.trade_time >= start_date,
                Trade.trade_time <= end_date
            ).order_by(Trade.trade_time).all()
            
            # 按日期分组计算
            df = pd.DataFrame([{
                "date": t.trade_time.date(),
                "profit_loss": float(t.profit_loss) if hasattr(t, 'profit_loss') else 0
            } for t in trades])
            
            if df.empty:
                return []
            
            # 按日期聚合
            daily_profit = df.groupby("date")["profit_loss"].sum().reset_index()
            
            result = []
            cumulative_profit = 0
            for _, row in daily_profit.iterrows():
                cumulative_profit += row["profit_loss"]
                result.append({
                    "date": row["date"].isoformat(),
                    "daily_profit_loss": row["profit_loss"],
                    "cumulative_profit_loss": cumulative_profit
                })
            
            return result
        except Exception as e:
            logger.error(f"获取盈亏趋势失败: {e}")
            return []


# 全局分析服务实例
analysis_service = AnalysisService()

