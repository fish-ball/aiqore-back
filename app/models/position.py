"""持仓模型"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Position(Base):
    """持仓记录"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, comment="账户ID")
    symbol = Column(String(20), nullable=False, comment="证券代码")
    symbol_name = Column(String(100), comment="证券名称")
    quantity = Column(Integer, nullable=False, default=0, comment="持仓数量")
    available_quantity = Column(Integer, nullable=False, default=0, comment="可用数量")
    frozen_quantity = Column(Integer, nullable=False, default=0, comment="冻结数量")
    cost_price = Column(Numeric(10, 3), nullable=False, comment="成本价")
    current_price = Column(Numeric(10, 3), nullable=False, default=0, comment="当前价")
    cost_amount = Column(Numeric(15, 2), nullable=False, comment="成本金额")
    market_value = Column(Numeric(15, 2), nullable=False, default=0, comment="市值")
    profit_loss = Column(Numeric(15, 2), nullable=False, default=0, comment="盈亏")
    profit_loss_ratio = Column(Numeric(8, 4), nullable=False, default=0, comment="盈亏比例")
    last_update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最后更新时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关系
    account = relationship("Account", backref="positions")
    
    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, quantity={self.quantity})>"

