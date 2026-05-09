"""板块模型：层级结构 + 数据源与资产类别。"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Sector(Base):
    """
    板块。

    - name：显示名称
    - alias：数据源侧板块键（如 QMT get_stock_list_in_sector 入参）；与 source 联合唯一
    - source：数据源类型字符串（见 DataSourceType）
    - asset_class：资产大类（见 AssetClass）
    - instrument_type：标的类型（见 InstrumentType，与 instruments.instrument_type 枚举值一致）
    - parent / children：树形层级
    """

    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="显示名称")
    alias = Column(String(100), nullable=False, index=True, comment="数据源板块键")
    source = Column(String(32), nullable=False, index=True, comment="数据源：qmt / joinquant / tushare")
    asset_class = Column(String(32), nullable=False, index=True, comment="资产大类：EQUITY / FUTURE / OPTION 等，与 AssetClass 枚举 value 一致")
    instrument_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="标的类型：STOCK / FUND / INDEX / FUTURE / OPTION / BOND / ETF，与 InstrumentType 枚举 value 一致",
    )
    parent_id = Column(
        Integer,
        ForeignKey("sectors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父板块 id",
    )
    remark = Column(Text, nullable=True, comment="用户备注")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    parent = relationship(
        "Sector",
        remote_side=[id],
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children = relationship(
        "Sector",
        foreign_keys=[parent_id],
        back_populates="parent",
    )

    __table_args__ = (
        UniqueConstraint("source", "alias", name="uq_sectors_source_alias"),
        Index("idx_sectors_parent_id", "parent_id"),
        Index("idx_sectors_name", "name"),
        Index("idx_sectors_instrument_type", "instrument_type"),
    )

    def __repr__(self):
        return f"<Sector(source={self.source}, alias={self.alias}, name={self.name})>"
