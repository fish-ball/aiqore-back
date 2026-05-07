"""标的统一模型 instruments：单表存储，无外扩子表。"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Index, Numeric, String
from sqlalchemy.sql import func

from app.database import Base
from app.libs.data_source.models.enums import AssetClass, InstrumentType


def parse_market_suffix_from_code(code: str) -> str:
    """从标的代码解析市场后缀，如 601888.SH -> SH。"""
    if not code:
        return ""
    parts = code.rsplit(".", 1)
    return parts[-1].upper() if len(parts) == 2 else ""


def infer_asset_class_from_instrument_type(inst_type: InstrumentType | str) -> AssetClass:
    """由标的类型推导写入 instruments.asset_class 的大类（与 AssetClass 枚举 value 一致）。"""
    u = inst_type.value if isinstance(inst_type, InstrumentType) else str(inst_type).upper()
    if u == InstrumentType.FUTURE.value:
        return AssetClass.COMMODITY
    if u == InstrumentType.OPTION.value:
        return AssetClass.EQUITY
    if u in (InstrumentType.BOND.value, InstrumentType.CONV_BOND.value, InstrumentType.REPO.value):
        return AssetClass.DEBT
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
        comment="资产大类：与 AssetClass 枚举 value 一致（如 EQUITY、DEBT、COMMODITY）",
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
