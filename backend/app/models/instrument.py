"""标的统一模型 instruments：单表存储，无外扩子表。"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Index, Numeric, String
from sqlalchemy.sql import func

from app.database import Base


class AssetClass(str, Enum):
    """资产大类（instruments.asset_class）。"""

    EQUITY = "EQUITY"  # 权益类
    COMMODITY = "COMMODITY"  # 大宗商品
    FIXED_INCOME = "FIXED_INCOME"  # 固收类


class InstrumentType(str, Enum):
    """标的类型（instruments.instrument_type），细分品种。"""

    STOCK = "STOCK"  # 股票
    FUND = "FUND"  # 基金
    INDEX = "INDEX"  # 指数
    FUTURE = "FUTURE"  # 期货
    OPTION = "OPTION"  # 期权
    BOND = "BOND"  # 债券
    ETF = "ETF"  # ETF 基金


def parse_market_suffix_from_code(code: str) -> str:
    """从标的代码解析市场后缀，如 601888.SH -> SH。"""
    if not code:
        return ""
    parts = code.rsplit(".", 1)
    return parts[-1].upper() if len(parts) == 2 else ""


def instrument_type_to_market_layer(instrument_type: Optional[str]) -> str:
    """
    instrument_type -> 本地行情缓存目录使用的三大类字符串（Equity/Future/Option）。
    与 app.libs.data_source.cache 中约定一致。
    """
    from app.libs.data_source.models.enums import MarketLayer

    if not instrument_type:
        return MarketLayer.Equity.value
    u = instrument_type.upper()
    if u == InstrumentType.FUTURE.value:
        return MarketLayer.Future.value
    if u == InstrumentType.OPTION.value:
        return MarketLayer.Option.value
    return MarketLayer.Equity.value


def infer_asset_class_from_instrument_type(inst_type: InstrumentType | str) -> AssetClass:
    """由标的类型推导资产大类。"""
    u = inst_type.value if isinstance(inst_type, InstrumentType) else str(inst_type).upper()
    if u == InstrumentType.FUTURE.value:
        return AssetClass.COMMODITY
    if u == InstrumentType.OPTION.value:
        return AssetClass.EQUITY
    if u == InstrumentType.BOND.value:
        return AssetClass.FIXED_INCOME
    return AssetClass.EQUITY


class Instrument(Base):
    """标的主表：代码为主键，单表无子类型扩展表。"""

    __tablename__ = "instruments"

    code = Column(String(64), primary_key=True, comment="标的代码，如 601888.SH")
    name = Column(String(100), nullable=False, comment="证券名称")
    exchange_code = Column(
        String(32),
        nullable=False,
        index=True,
        comment="所属交易所规范代码，与 app.constants.exchanges 中 code 一致（如 SSE、SHFE）",
    )
    asset_class = Column(
        String(20),
        nullable=False,
        comment="资产大类：EQUITY / FIXED_INCOME / COMMODITY",
    )
    instrument_type = Column(
        String(20),
        nullable=False,
        comment="标的类型：STOCK / FUND / INDEX / FUTURE / OPTION / BOND / ETF",
    )
    open_date = Column(DateTime, nullable=True, comment="上市日期或合约开始日期")
    expire_date = Column(DateTime, nullable=True, comment="退市日期或合约结束日期")
    abbreviation = Column(String(50), nullable=True, comment="缩写（拼音简写）")
    last_price = Column(Numeric(18, 6), nullable=True, comment="最新价格")
    is_active = Column(Boolean, nullable=False, default=True, comment="当前是否可交易")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index("idx_instruments_name", "name"),
        Index("idx_instruments_asset_class", "asset_class"),
        Index("idx_instruments_instrument_type", "instrument_type"),
        Index("idx_instruments_is_active", "is_active"),
        Index("idx_instruments_abbreviation", "abbreviation"),
    )

    def __repr__(self):
        return f"<Instrument(code={self.code}, name={self.name}, type={self.instrument_type})>"
