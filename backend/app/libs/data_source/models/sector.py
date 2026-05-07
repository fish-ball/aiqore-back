# -*- coding: utf-8 -*-
"""数据源侧板块树节点（与 ORM Sector 解耦，供适配器 get_sector_list 返回）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.libs.data_source.models.enums import AssetClass, InstrumentType


@dataclass
class DataSourceSector:
    """层级板块节点：name 展示名；alias 为数据源侧键（如 QMT get_stock_list_in_sector 入参）。"""

    name: str
    alias: str
    asset_class: AssetClass
    instrument_type: InstrumentType
    children: List[DataSourceSector] = field(default_factory=list)

    def to_public_dict(self) -> Dict[str, Any]:
        """调试接口等用的可 JSON 序列化结构。"""
        return {
            "name": self.name,
            "alias": self.alias,
            "asset_class": self.asset_class.value,
            "instrument_type": self.instrument_type.value,
            "children": [c.to_public_dict() for c in self.children],
        }
