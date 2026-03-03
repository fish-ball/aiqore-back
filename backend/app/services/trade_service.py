"""交易服务"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.trade import Trade, TradeDirection, TradeStatus
from app.models.position import Position
from app.services.data_source import get_default_qmt_adapter
import logging

logger = logging.getLogger(__name__)


class TradeService:
    """交易服务"""

    def __init__(self):
        self._qmt = None

    @property
    def qmt(self):
        """懒加载 QMT 适配器，避免启动时阻塞。"""
        if self._qmt is None:
            self._qmt = get_default_qmt_adapter()
        return self._qmt

    def sync_account(self, db: Session, account_id: str) -> Optional[Account]:
        """
        同步账户信息
        
        Args:
            db: 数据库会话
            account_id: QMT账户ID
            
        Returns:
            账户对象
        """
        try:
            # 从QMT获取账户信息
            qmt_account = self.qmt.get_account_info(account_id)
            if not qmt_account:
                return None
            
            # 查找或创建账户
            account = db.query(Account).filter(Account.account_id == account_id).first()
            if not account:
                account = Account(
                    account_id=account_id,
                    name=f"账户-{account_id}",
                    initial_capital=Decimal(str(qmt_account.get("balance", 0))),
                    current_balance=Decimal(str(qmt_account.get("balance", 0))),
                    available_balance=Decimal(str(qmt_account.get("available", 0))),
                    frozen_balance=Decimal(str(qmt_account.get("frozen", 0))),
                    market_value=Decimal(str(qmt_account.get("market_value", 0))),
                    total_asset=Decimal(str(qmt_account.get("total_asset", 0)))
                )
                db.add(account)
            else:
                # 更新账户信息
                account.current_balance = Decimal(str(qmt_account.get("balance", 0)))
                account.available_balance = Decimal(str(qmt_account.get("available", 0)))
                account.frozen_balance = Decimal(str(qmt_account.get("frozen", 0)))
                account.market_value = Decimal(str(qmt_account.get("market_value", 0)))
                account.total_asset = Decimal(str(qmt_account.get("total_asset", 0)))
            
            db.commit()
            db.refresh(account)
            return account
        except Exception as e:
            logger.error(f"同步账户信息失败: {e}")
            db.rollback()
            return None
    
    def sync_positions(self, db: Session, account_id: str) -> List[Position]:
        """
        同步持仓信息
        
        Args:
            db: 数据库会话
            account_id: QMT账户ID
            
        Returns:
            持仓列表
        """
        try:
            account = db.query(Account).filter(Account.account_id == account_id).first()
            if not account:
                return []
            
            # 从QMT获取持仓
            qmt_positions = self.qmt.get_positions(account_id)
            
            # 更新或创建持仓
            positions = []
            for qmt_pos in qmt_positions:
                symbol = qmt_pos.get("symbol")
                position = db.query(Position).filter(
                    Position.account_id == account.id,
                    Position.symbol == symbol
                ).first()
                
                if not position:
                    position = Position(
                        account_id=account.id,
                        symbol=symbol,
                        symbol_name=qmt_pos.get("name", ""),
                        quantity=int(qmt_pos.get("quantity", 0)),
                        available_quantity=int(qmt_pos.get("available_quantity", 0)),
                        frozen_quantity=int(qmt_pos.get("frozen_quantity", 0)),
                        cost_price=Decimal(str(qmt_pos.get("cost_price", 0))),
                        current_price=Decimal(str(qmt_pos.get("current_price", 0))),
                        cost_amount=Decimal(str(qmt_pos.get("cost_amount", 0))),
                        market_value=Decimal(str(qmt_pos.get("market_value", 0))),
                        profit_loss=Decimal(str(qmt_pos.get("profit_loss", 0))),
                        profit_loss_ratio=Decimal(str(qmt_pos.get("profit_loss_ratio", 0)))
                    )
                    db.add(position)
                else:
                    position.quantity = int(qmt_pos.get("quantity", 0))
                    position.available_quantity = int(qmt_pos.get("available_quantity", 0))
                    position.frozen_quantity = int(qmt_pos.get("frozen_quantity", 0))
                    position.cost_price = Decimal(str(qmt_pos.get("cost_price", 0)))
                    position.current_price = Decimal(str(qmt_pos.get("current_price", 0)))
                    position.cost_amount = Decimal(str(qmt_pos.get("cost_amount", 0)))
                    position.market_value = Decimal(str(qmt_pos.get("market_value", 0)))
                    position.profit_loss = Decimal(str(qmt_pos.get("profit_loss", 0)))
                    position.profit_loss_ratio = Decimal(str(qmt_pos.get("profit_loss_ratio", 0)))
                
                positions.append(position)
            
            db.commit()
            for pos in positions:
                db.refresh(pos)
            
            return positions
        except Exception as e:
            logger.error(f"同步持仓信息失败: {e}")
            db.rollback()
            return []
    
    def record_trade(
        self,
        db: Session,
        account_id: int,
        symbol: str,
        direction: TradeDirection,
        price: Decimal,
        quantity: int,
        trade_time: datetime,
        **kwargs
    ) -> Optional[Trade]:
        """
        记录交易
        
        Args:
            db: 数据库会话
            account_id: 账户ID
            symbol: 证券代码
            direction: 交易方向
            price: 成交价格
            quantity: 成交数量
            trade_time: 成交时间
            **kwargs: 其他参数
            
        Returns:
            交易记录对象
        """
        try:
            amount = price * quantity
            commission = kwargs.get("commission", Decimal("0"))
            tax = kwargs.get("tax", Decimal("0"))
            total_cost = amount + commission + tax
            
            # 生成订单ID
            import uuid
            order_id = kwargs.get("order_id", str(uuid.uuid4()))
            
            trade = Trade(
                account_id=account_id,
                order_id=order_id,
                symbol=symbol,
                symbol_name=kwargs.get("symbol_name", ""),
                direction=direction,
                price=price,
                quantity=quantity,
                amount=amount,
                commission=commission,
                tax=tax,
                total_cost=total_cost,
                status=TradeStatus.FILLED,
                trade_time=trade_time,
                qmt_order_id=kwargs.get("qmt_order_id"),
                remark=kwargs.get("remark", "")
            )
            
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            # 更新持仓
            self._update_position(db, account_id, symbol, direction, price, quantity)
            
            return trade
        except Exception as e:
            logger.error(f"记录交易失败: {e}")
            db.rollback()
            return None
    
    def _update_position(
        self,
        db: Session,
        account_id: int,
        symbol: str,
        direction: TradeDirection,
        price: Decimal,
        quantity: int
    ):
        """更新持仓"""
        position = db.query(Position).filter(
            Position.account_id == account_id,
            Position.symbol == symbol
        ).first()
        
        if direction == TradeDirection.BUY:
            # 买入
            if position:
                # 更新成本价（加权平均）
                total_cost = position.cost_amount + (price * quantity)
                total_quantity = position.quantity + quantity
                position.cost_price = total_cost / total_quantity if total_quantity > 0 else price
                position.quantity = total_quantity
                position.available_quantity = position.quantity - position.frozen_quantity
                position.cost_amount = total_cost
            else:
                # 新建持仓
                position = Position(
                    account_id=account_id,
                    symbol=symbol,
                    quantity=quantity,
                    available_quantity=quantity,
                    cost_price=price,
                    current_price=price,
                    cost_amount=price * quantity,
                    market_value=price * quantity
                )
                db.add(position)
        else:
            # 卖出
            if position:
                position.quantity -= quantity
                position.available_quantity = position.quantity - position.frozen_quantity
                if position.quantity == 0:
                    db.delete(position)
        
        db.commit()


# 全局交易服务实例
trade_service = TradeService()

