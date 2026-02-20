"""证券基础信息模型

数据表: securities

字段分组定义:
--------------
一、主键与标识
  id              主键，自增
  symbol          证券代码，唯一，如 000001.SZ、600000.SH

二、基础信息（业务必填/常用）
  name            证券名称
  market          市场代码，如 SZ、SH
  security_type   证券类型（业务层），如 股票、基金、债券、期货、期权、可转债 等
  is_active       是否有效，1-有效，0-无效，默认 1

三、扩展基础信息（可选，多用于展示与筛选）
  industry        所属行业
  list_date       上市日期
  delist_date     退市日期
  pinyin          拼音简称，用于搜索
  abbreviation    字母简写，如 ZGZM（中国中免），用于快速搜索
  description     描述信息

四、系统字段
  created_at      创建时间（带时区）
  updated_at      更新时间（带时区）

五、QMT 标的属性（与 QMT InstrumentType 对应）
  instrument_type 标的类型，如 Stock、Fund、Bond、Future、Option 等
  exchange_id     交易所代码，如 SSE、SZSE
  product_id      产品代码
  currency_id     货币代码，如 CNY、USD

六、交易与报价规则
  tick_size       最小变动单位
  lot_size        交易单位/每手数量
  price_tick      价格精度

七、行情快照（来自 QMT 实时/快照，非历史 K 线）
  upper_limit           涨停价
  lower_limit           跌停价
  pre_settlement_price  昨结算价（期货等）
  pre_close_price       昨收盘价
  open_price            开盘价
  last_price            最新价
  volume                成交量
  amount                成交额
  open_interest         持仓量（期货/期权）

八、期权/期货专用
  strike_price    行权价
  expiry_date     到期日

九、可转债专用
  underlying_symbol  标的证券代码
  conversion_ratio   转股比例

十、债券专用
  interest_rate   利率
  maturity_date   到期日
  face_value      面值

十一、基金专用
  fund_type       基金类型，如 ETF、LOF、封闭式基金
  nav             净值
  accumulated_nav 累计净值

十二、原始数据
  raw_data        JSON，保存 QMT get_instrument_detail 完整返回，便于扩展与排查

QMT 数据源与 Security 字段对照:
------------------------------
（一）证券列表来源
  QMT 接口: xtdata.get_stock_list_in_sector(sector) / get_instrument_list(exchange)
  返回每条: 字符串为 symbol（如 000001.SZ），市场由后缀推断。
  Security 使用:
    symbol   <- 列表项本身（证券代码）
    market   <- 根据 symbol 后缀: .SH->SH, .SZ->SZ, .BJ->BJ
    sector   <- 仅用于同步时筛选板块，不落库；用于 InstrumentType 为空时推断 security_type

（二）标的详情 get_instrument_detail(symbol) 返回字段 -> Security 字段
  QMT 字段名(英文)       Security 字段           说明/转换
  -----------------      -----------------       -----------------
  InstrumentName         name                    标的名称
  InstrumentType         instrument_type         原样存储；并映射到 security_type（见下）
  ExchangeID             exchange_id            交易所代码
  ProductID              product_id             产品代码
  CurrencyID             currency_id            货币代码
  TickSize               tick_size               float
  LotSize                lot_size                int
  PriceTick              price_tick              float
  UpperLimit             upper_limit             float
  LowerLimit             lower_limit             float
  PreSettlementPrice     pre_settlement_price    float
  PreClosePrice          pre_close_price         float
  OpenPrice              open_price              float
  LastPrice              last_price              float
  Volume                 volume                  int
  Amount                 amount                  float
  OpenInterest           open_interest          int
  StrikePrice            strike_price           float
  ExpiryDate             expiry_date            datetime
  UnderlyingSymbol       underlying_symbol      字符串
  ConversionRatio        conversion_ratio       float
  InterestRate           interest_rate          float
  MaturityDate           maturity_date          datetime
  FaceValue              face_value             float
  FundType               fund_type             字符串
  NAV                    nav                    float
  AccumulatedNAV         accumulated_nav        float
  整份 detail 对象       raw_data               JSON 原样保存

（三）InstrumentType -> security_type 映射（业务层）
  QMT 取值(含大小写)      security_type
  STOCK / 默认            股票
  FUND / ETF / LOF        基金
  BOND                    债券
  CONVERTIBLE             可转债
  FUTURE                  期货
  OPTION                  期权
  INDEX                   指数
  WARRANT                 权证
  若 InstrumentType 为空，则用 sector 字符串（如含「基金」「债」「期货」「期权」）推断。

（四）本系统自有或衍生字段（非 QMT 直接提供）
  id, is_active, industry, list_date, delist_date, pinyin, abbreviation,
  description, created_at, updated_at
  其中 abbreviation 由 name 经 pypinyin 生成首字母简写（如 中国中免->ZGZM）。
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index, JSON
from sqlalchemy.sql import func
from app.database import Base


class Security(Base):
    """证券基础信息"""
    __tablename__ = "securities"

    # 一、主键与标识
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True, comment="证券代码，如 000001.SZ")
    name = Column(String(100), nullable=False, comment="证券名称")
    market = Column(String(10), nullable=False, comment="市场，如 SZ, SH")
    security_type = Column(String(20), nullable=False, default="股票", comment="证券类型：股票、基金、债券等")
    is_active = Column(Integer, default=1, comment="是否有效，1-有效，0-无效")

    # 二、扩展基础信息
    industry = Column(String(50), comment="所属行业")
    list_date = Column(DateTime, comment="上市日期")
    delist_date = Column(DateTime, comment="退市日期")
    pinyin = Column(String(200), comment="拼音简称，用于搜索")
    abbreviation = Column(String(50), comment="字母简写，如ZGZM（中国中免），用于快速搜索")
    description = Column(Text, comment="描述信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 三、QMT 标的属性
    instrument_type = Column(String(50), comment="标的类型（InstrumentType），如 Stock, Fund, Bond, Future, Option 等")
    exchange_id = Column(String(20), comment="交易所代码（ExchangeID），如 SSE, SZSE 等")
    product_id = Column(String(50), comment="产品代码（ProductID）")
    currency_id = Column(String(10), comment="货币代码（CurrencyID），如 CNY, USD 等")

    # 四、交易与报价规则
    tick_size = Column(Numeric(10, 4), comment="最小变动单位（TickSize）")
    lot_size = Column(Integer, comment="交易单位（LotSize），每手数量")
    price_tick = Column(Numeric(10, 4), comment="价格精度（PriceTick）")

    # 五、行情快照（来自 QMT 快照，非历史 K 线）
    upper_limit = Column(Numeric(10, 4), comment="涨停价（UpperLimit）")
    lower_limit = Column(Numeric(10, 4), comment="跌停价（LowerLimit）")
    pre_settlement_price = Column(Numeric(10, 4), comment="昨结算价（PreSettlementPrice）")
    pre_close_price = Column(Numeric(10, 4), comment="昨收盘价（PreClosePrice）")
    open_price = Column(Numeric(10, 4), comment="开盘价（OpenPrice）")
    last_price = Column(Numeric(10, 4), comment="最新价（LastPrice）")
    volume = Column(Integer, comment="成交量（Volume）")
    amount = Column(Numeric(20, 2), comment="成交额（Amount）")
    open_interest = Column(Integer, comment="持仓量（OpenInterest），期货/期权用")

    # 六、期权/期货专用
    strike_price = Column(Numeric(10, 4), comment="行权价（StrikePrice），期权用")
    expiry_date = Column(DateTime, comment="到期日（ExpiryDate），期货/期权用")

    # 七、可转债专用
    underlying_symbol = Column(String(20), comment="标的证券代码（UnderlyingSymbol），期权/可转债用")
    conversion_ratio = Column(Numeric(10, 4), comment="转股比例（ConversionRatio），可转债用")

    # 八、债券专用
    interest_rate = Column(Numeric(10, 4), comment="利率（InterestRate），债券用")
    maturity_date = Column(DateTime, comment="到期日（MaturityDate），债券用")
    face_value = Column(Numeric(10, 4), comment="面值（FaceValue），债券用")

    # 九、基金专用
    fund_type = Column(String(50), comment="基金类型（FundType），如 ETF, LOF, 封闭式基金 等")
    nav = Column(Numeric(10, 4), comment="净值（NAV），基金用")
    accumulated_nav = Column(Numeric(10, 4), comment="累计净值（AccumulatedNAV），基金用")

    # 十、原始数据
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

