"""板块模型：层级结构 + 元数据（JSON）。"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Sector(Base):
    """
    板块。

    - name：显示名称
    - alias：唯一别名，通常与数据源板块键一致（如 QMT get_stock_list_in_sector 入参）
    - parent / children：树形层级
    - sector_meta：数据库列名为 metadata，存放同步统计、数据来源等扩展信息
    """

    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True, comment="显示名称")
    alias = Column(String(100), nullable=False, unique=True, index=True, comment="唯一别名（数据源板块键等）")
    parent_id = Column(
        Integer,
        ForeignKey("sectors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父板块 id",
    )
    # 避免与 DeclarativeBase.metadata 冲突，Python 属性名为 sector_meta
    sector_meta = Column("metadata", JSON, nullable=True, comment="JSON 元数据（统计、数据来源等）")
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
        Index("idx_sectors_parent_id", "parent_id"),
        Index("idx_sectors_name", "name"),
    )

    def __repr__(self):
        return f"<Sector(alias={self.alias}, name={self.name})>"
