# -*- coding: utf-8 -*-
"""数据源模型：仅行情侧连接；source_type 约束见 libs.data_source.models.enums.DataSourceType。"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.database import Base
from app.libs.data_source.models.enums import DataSourceType


class DataSource(Base):
    """行情数据源连接配置（QMT、聚宽、tushare 等）。"""

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="显示名称")
    source_type = Column(
        SAEnum(
            DataSourceType,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        index=True,
        comment="数据源类型：qmt / joinquant / tushare",
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    # default=dict：SQLAlchemy 在每次 INSERT 时调用，得到新的空 dict（不可写 default={}）
    config = Column(JSON, nullable=False, default=dict, comment="类型相关 JSON 配置字典")
    description = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, name={self.name}, source_type={self.source_type})>"
