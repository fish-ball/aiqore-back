"""账户模型"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Account(Base):
    """投资账户"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="账户名称")
    account_id = Column(String(50), unique=True, nullable=False, comment="QMT账户ID")
    initial_capital = Column(Numeric(15, 2), nullable=False, default=0, comment="初始资金")
    current_balance = Column(Numeric(15, 2), nullable=False, default=0, comment="当前余额")
    available_balance = Column(Numeric(15, 2), nullable=False, default=0, comment="可用余额")
    frozen_balance = Column(Numeric(15, 2), nullable=False, default=0, comment="冻结资金")
    market_value = Column(Numeric(15, 2), nullable=False, default=0, comment="持仓市值")
    total_asset = Column(Numeric(15, 2), nullable=False, default=0, comment="总资产")
    description = Column(Text, comment="账户描述")
    is_active = Column(Integer, default=1, comment="是否激活")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name}, account_id={self.account_id})>"

