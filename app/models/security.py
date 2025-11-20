"""证券基础信息模型"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index
from sqlalchemy.sql import func
from app.database import Base


class Security(Base):
    """证券基础信息"""
    __tablename__ = "securities"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True, comment="证券代码，如 000001.SZ")
    name = Column(String(100), nullable=False, comment="证券名称")
    market = Column(String(10), nullable=False, comment="市场，如 SZ, SH")
    security_type = Column(String(20), nullable=False, default="股票", comment="证券类型：股票、基金、债券等")
    industry = Column(String(50), comment="所属行业")
    list_date = Column(DateTime, comment="上市日期")
    delist_date = Column(DateTime, comment="退市日期")
    is_active = Column(Integer, default=1, comment="是否有效，1-有效，0-无效")
    pinyin = Column(String(200), comment="拼音简称，用于搜索")
    abbreviation = Column(String(50), comment="字母简写，如ZGZM（中国中免），用于快速搜索")
    description = Column(Text, comment="描述信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_symbol', 'symbol'),
        Index('idx_name', 'name'),
        Index('idx_market', 'market'),
        Index('idx_is_active', 'is_active'),
        Index('idx_abbreviation', 'abbreviation'),
    )
    
    def __repr__(self):
        return f"<Security(symbol={self.symbol}, name={self.name})>"

