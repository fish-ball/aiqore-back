"""策略模型：策略名称、策略类型、代码 script"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


# 策略类型枚举，当前仅 backtrader
STRATEGY_TYPE_BACKTRADER = "backtrader"


class Strategy(Base):
    """策略配置：名称、类型、脚本代码"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="策略名称")
    strategy_type = Column(String(32), nullable=False, index=True, comment="策略类型: backtrader 等")
    script = Column(Text, nullable=True, comment="策略代码 script")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, strategy_type={self.strategy_type})>"
