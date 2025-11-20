"""证券基础信息模型"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index, JSON
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
    
    # QMT 原始数据字段
    instrument_type = Column(String(50), comment="标的类型（InstrumentType），如 Stock, Fund, Bond, Future, Option 等")
    exchange_id = Column(String(20), comment="交易所代码（ExchangeID），如 SSE, SZSE 等")
    product_id = Column(String(50), comment="产品代码（ProductID）")
    currency_id = Column(String(10), comment="货币代码（CurrencyID），如 CNY, USD 等")
    tick_size = Column(Numeric(10, 4), comment="最小变动单位（TickSize）")
    lot_size = Column(Integer, comment="交易单位（LotSize），每手数量")
    price_tick = Column(Numeric(10, 4), comment="价格精度（PriceTick）")
    upper_limit = Column(Numeric(10, 4), comment="涨停价（UpperLimit）")
    lower_limit = Column(Numeric(10, 4), comment="跌停价（LowerLimit）")
    pre_settlement_price = Column(Numeric(10, 4), comment="昨结算价（PreSettlementPrice）")
    pre_close_price = Column(Numeric(10, 4), comment="昨收盘价（PreClosePrice）")
    open_price = Column(Numeric(10, 4), comment="开盘价（OpenPrice）")
    last_price = Column(Numeric(10, 4), comment="最新价（LastPrice）")
    volume = Column(Integer, comment="成交量（Volume）")
    amount = Column(Numeric(20, 2), comment="成交额（Amount）")
    open_interest = Column(Integer, comment="持仓量（OpenInterest），期货/期权用")
    strike_price = Column(Numeric(10, 4), comment="行权价（StrikePrice），期权用")
    expiry_date = Column(DateTime, comment="到期日（ExpiryDate），期货/期权用")
    underlying_symbol = Column(String(20), comment="标的证券代码（UnderlyingSymbol），期权/可转债用")
    conversion_ratio = Column(Numeric(10, 4), comment="转股比例（ConversionRatio），可转债用")
    interest_rate = Column(Numeric(10, 4), comment="利率（InterestRate），债券用")
    maturity_date = Column(DateTime, comment="到期日（MaturityDate），债券用")
    face_value = Column(Numeric(10, 4), comment="面值（FaceValue），债券用")
    fund_type = Column(String(50), comment="基金类型（FundType），如 ETF, LOF, 封闭式基金 等")
    nav = Column(Numeric(10, 4), comment="净值（NAV），基金用")
    accumulated_nav = Column(Numeric(10, 4), comment="累计净值（AccumulatedNAV），基金用")
    
    # 原始数据 JSON 字段，保存完整的 get_instrument_detail 返回数据
    raw_data = Column(JSON, comment="原始数据 JSON，保存完整的 QMT get_instrument_detail 返回数据")
    
    # 创建索引
    __table_args__ = (
        Index('idx_symbol', 'symbol'),
        Index('idx_name', 'name'),
        Index('idx_market', 'market'),
        Index('idx_is_active', 'is_active'),
        Index('idx_abbreviation', 'abbreviation'),
        Index('idx_instrument_type', 'instrument_type'),
        Index('idx_exchange_id', 'exchange_id'),
        Index('idx_security_type', 'security_type'),
    )
    
    def __repr__(self):
        return f"<Security(symbol={self.symbol}, name={self.name}, type={self.security_type})>"

