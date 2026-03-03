"""交易记录模型"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TradeDirection(enum.Enum):
    """交易方向"""
    BUY = "买入"
    SELL = "卖出"


class TradeStatus(enum.Enum):
    """交易状态"""
    PENDING = "待成交"
    PARTIAL = "部分成交"
    FILLED = "已成交"
    CANCELLED = "已撤销"
    REJECTED = "已拒绝"


class Trade(Base):
    """交易记录"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账户ID")
    order_id = Column(String(50), unique=True, nullable=False, comment="订单ID")
    symbol = Column(String(20), nullable=False, comment="证券代码")
    symbol_name = Column(String(100), comment="证券名称")
    direction = Column(SQLEnum(TradeDirection), nullable=False, comment="交易方向")
    price = Column(Numeric(10, 3), nullable=False, comment="成交价格")
    quantity = Column(Integer, nullable=False, comment="成交数量")
    amount = Column(Numeric(15, 2), nullable=False, comment="成交金额")
    commission = Column(Numeric(10, 2), default=0, comment="手续费")
    tax = Column(Numeric(10, 2), default=0, comment="印花税")
    total_cost = Column(Numeric(15, 2), nullable=False, comment="总成本")
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING, comment="交易状态")
    trade_time = Column(DateTime(timezone=True), nullable=False, comment="成交时间")
    qmt_order_id = Column(String(50), comment="QMT订单ID")
    remark = Column(String(500), comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    account = relationship("Account", backref="trades")
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, direction={self.direction.value}, quantity={self.quantity})>"

