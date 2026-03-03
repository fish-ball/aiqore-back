"""板块信息模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Integer
from sqlalchemy.sql import func
from app.database import Base


class Sector(Base):
    """板块信息"""
    __tablename__ = "sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="板块名称，如 '沪深A股'、'深市ETF'")
    display_name = Column(String(100), comment="显示名称，用于前端展示")
    category = Column(String(50), comment="板块分类：股票、基金、债券、期货、期权、指数等")
    market = Column(String(10), comment="所属市场：SH、SZ、BJ等，None表示跨市场")
    description = Column(Text, comment="板块描述")
    security_count = Column(Integer, default=0, comment="板块内证券数量")
    is_active = Column(Integer, default=1, comment="是否有效，1-有效，0-无效")
    last_sync_at = Column(DateTime, comment="最后同步时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 创建索引（使用唯一前缀避免与其他表的索引冲突）
    __table_args__ = (
        Index('idx_sectors_name', 'name'),
        Index('idx_sectors_category', 'category'),
        Index('idx_sectors_market', 'market'),
        Index('idx_sectors_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Sector(name={self.name}, count={self.security_count})>"

