"""证券基础信息模型（主表 + 数据源外表 + 类型扩展子表）

主表 securities：身份与基础信息，与数据源解耦。
数据源外表 security_source_qmt：QMT 相关标识与 raw_data，0-1。
子表：trading_rules、quote_snapshot、stock、fund、bond、convertible、option、future，均为 0-1。
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Security(Base):
    """证券主表：身份与基础信息"""
    __tablename__ = "securities"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(64), unique=True, nullable=False, index=True, comment="证券代码，如 000001.SZ")
    name = Column(String(100), nullable=False, comment="证券名称")
    market = Column(String(10), nullable=False, comment="市场，如 SZ, SH")
    security_type = Column(String(20), nullable=False, default="股票", comment="证券类型：股票、基金、债券等")
    is_active = Column(Integer, default=1, comment="是否有效，1-有效，0-无效")
    industry = Column(String(50), comment="所属行业")
    list_date = Column(DateTime, comment="上市日期")
    delist_date = Column(DateTime, comment="退市日期")
    pinyin = Column(String(200), comment="拼音简称，用于搜索")
    abbreviation = Column(String(50), comment="字母简写，如 ZGZM（中国中免），用于快速搜索")
    description = Column(Text, comment="描述信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    source_qmt = relationship("SecuritySourceQmt", back_populates="security", uselist=False)
    trading_rules = relationship("SecurityTradingRules", back_populates="security", uselist=False)
    quote_snapshot = relationship("SecurityQuoteSnapshot", back_populates="security", uselist=False)
    stock_ext = relationship("SecurityStock", back_populates="security", uselist=False)
    fund_ext = relationship("SecurityFund", back_populates="security", uselist=False)
    bond_ext = relationship("SecurityBond", back_populates="security", uselist=False)
    convertible_ext = relationship("SecurityConvertible", back_populates="security", uselist=False)
    option_ext = relationship("SecurityOption", back_populates="security", uselist=False)
    future_ext = relationship("SecurityFuture", back_populates="security", uselist=False)

    __table_args__ = (
        Index('idx_symbol', 'symbol'),
        Index('idx_name', 'name'),
        Index('idx_market', 'market'),
        Index('idx_is_active', 'is_active'),
        Index('idx_abbreviation', 'abbreviation'),
        Index('idx_security_type', 'security_type'),
    )

    def __repr__(self):
        return f"<Security(symbol={self.symbol}, name={self.name}, type={self.security_type})>"


class SecuritySourceQmt(Base):
    """证券数据源——QMT（0-1）"""
    __tablename__ = "security_source_qmt"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    instrument_type = Column(String(50), comment="标的类型（InstrumentType），如 Stock, Fund, Bond, Future, Option 等")
    exchange_id = Column(String(20), comment="交易所代码（ExchangeID），如 SSE, SZSE 等")
    product_id = Column(String(50), comment="产品代码（ProductID）")
    currency_id = Column(String(10), comment="货币代码（CurrencyID），如 CNY, USD 等")
    raw_data = Column(JSON, comment="QMT get_instrument_detail 完整返回 JSON")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="该数据源最后同步时间")

    security = relationship("Security", back_populates="source_qmt")

    __table_args__ = (Index('idx_security_source_qmt_instrument_type', 'instrument_type'), Index('idx_security_source_qmt_exchange_id', 'exchange_id'))


class SecurityTradingRules(Base):
    """交易与报价规则（0-1）"""
    __tablename__ = "security_trading_rules"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    tick_size = Column(Numeric(10, 4), comment="最小变动单位（TickSize）")
    lot_size = Column(Integer, comment="交易单位（LotSize），每手数量")
    price_tick = Column(Numeric(10, 4), comment="价格精度（PriceTick）")

    security = relationship("Security", back_populates="trading_rules")


class SecurityQuoteSnapshot(Base):
    """行情快照（0-1），来自 QMT 快照非历史 K 线"""
    __tablename__ = "security_quote_snapshot"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    upper_limit = Column(Numeric(10, 4), comment="涨停价（UpperLimit）")
    lower_limit = Column(Numeric(10, 4), comment="跌停价（LowerLimit）")
    pre_settlement_price = Column(Numeric(10, 4), comment="昨结算价（PreSettlementPrice）")
    pre_close_price = Column(Numeric(10, 4), comment="昨收盘价（PreClosePrice）")
    open_price = Column(Numeric(10, 4), comment="开盘价（OpenPrice）")
    last_price = Column(Numeric(10, 4), comment="最新价（LastPrice）")
    volume = Column(Integer, comment="成交量（Volume）")
    amount = Column(Numeric(20, 2), comment="成交额（Amount）")
    open_interest = Column(Integer, comment="持仓量（OpenInterest），期货/期权用")

    security = relationship("Security", back_populates="quote_snapshot")


class SecurityStock(Base):
    """股票扩展（0-1），预留后续股票专属指标"""
    __tablename__ = "security_stock"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")

    security = relationship("Security", back_populates="stock_ext")


class SecurityFund(Base):
    """基金扩展（0-1）"""
    __tablename__ = "security_fund"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    fund_type = Column(String(50), comment="基金类型（FundType），如 ETF, LOF, 封闭式基金 等")
    nav = Column(Numeric(10, 4), comment="净值（NAV）")
    accumulated_nav = Column(Numeric(10, 4), comment="累计净值（AccumulatedNAV）")

    security = relationship("Security", back_populates="fund_ext")


class SecurityBond(Base):
    """债券扩展（0-1）"""
    __tablename__ = "security_bond"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    interest_rate = Column(Numeric(10, 4), comment="利率（InterestRate）")
    maturity_date = Column(DateTime, comment="到期日（MaturityDate）")
    face_value = Column(Numeric(10, 4), comment="面值（FaceValue）")

    security = relationship("Security", back_populates="bond_ext")


class SecurityConvertible(Base):
    """可转债扩展（0-1）"""
    __tablename__ = "security_convertible"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    underlying_symbol = Column(String(20), comment="标的证券代码（UnderlyingSymbol）")
    conversion_ratio = Column(Numeric(10, 4), comment="转股比例（ConversionRatio）")

    security = relationship("Security", back_populates="convertible_ext")


class SecurityOption(Base):
    """期权扩展（0-1）"""
    __tablename__ = "security_option"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    strike_price = Column(Numeric(10, 4), comment="行权价（StrikePrice）")
    expiry_date = Column(DateTime, comment="到期日（ExpiryDate）")
    underlying_symbol = Column(String(20), comment="标的证券代码")

    security = relationship("Security", back_populates="option_ext")


class SecurityFuture(Base):
    """期货扩展（0-1）"""
    __tablename__ = "security_future"

    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True, comment="证券主表 id")
    expiry_date = Column(DateTime, comment="到期日（ExpiryDate）")

    security = relationship("Security", back_populates="future_ext")
