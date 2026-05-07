# -*- coding: utf-8 -*-
"""QMT 板块预设：与 xtdata.get_sector_list 经 _sector_keys_filtered 后的键对齐；人工可再调顺序与层级。"""

from __future__ import annotations

from typing import List, Optional

from app.libs.data_source.models import AssetClass, DataSourceSector, InstrumentType

__all__ = ["PRESET_SECTOR_ROOTS"]


def _sec(
    name: str,
    alias: str,
    *,
    ac: AssetClass = AssetClass.EQUITY,
    it: InstrumentType = InstrumentType.STOCK,
    children: Optional[List[DataSourceSector]] = None,
) -> DataSourceSector:
    """构造预设板块节点；asset_class / instrument_type 与 instruments 表枚举对齐。"""
    return DataSourceSector(
        name=name,
        alias=alias,
        asset_class=ac,
        instrument_type=it,
        children=list(children) if children else [],
    )


PRESET_SECTOR_ROOTS: List[DataSourceSector] = [
    # !! 以下注释为待实现占位，**严禁**删除注释 !!
    _sec("上证A股", "上证A股", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    _sec("深证A股", "深证A股", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    _sec("创业板", "创业板", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    _sec("科创板", "科创板", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    # _sec("科创板CDR", "科创板CDR", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    # _sec("北交所", "北交所", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    _sec("沪市ETF", "沪市ETF", ac=AssetClass.EQUITY, it=InstrumentType.ETF),
    _sec("深市ETF", "深市ETF", ac=AssetClass.EQUITY, it=InstrumentType.ETF),
    _sec("沪市指数", "沪市指数", ac=AssetClass.EQUITY, it=InstrumentType.INDEX),
    _sec("深市指数", "深市指数", ac=AssetClass.EQUITY, it=InstrumentType.INDEX),
    # _sec("上证B股", "上证B股", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    # _sec("深证B股", "深证B股", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    # _sec("上证期权", "上证期权", ac=AssetClass.EQUITY, it=InstrumentType.OPTION),
    # _sec("深证期权", "深证期权", ac=AssetClass.EQUITY, it=InstrumentType.OPTION),
    # _sec("上证转债", "上证转债", ac=AssetClass.HYBRID, it=InstrumentType.CONV_BOND),
    # _sec("深证转债", "深证转债", ac=AssetClass.HYBRID, it=InstrumentType.CONV_BOND),
    # _sec("沪市债券", "沪市债券", ac=AssetClass.DEBT, it=InstrumentType.BOND),
    # _sec("深市债券", "深市债券", ac=AssetClass.DEBT, it=InstrumentType.BOND),
    # _sec("沪市基金", "沪市基金", ac=AssetClass.EQUITY, it=InstrumentType.FUND),
    # _sec("深市基金", "深市基金", ac=AssetClass.EQUITY, it=InstrumentType.FUND),
    # _sec("香港联交所指数", "香港联交所指数", ac=AssetClass.EQUITY, it=InstrumentType.INDEX),
    # _sec("香港联交所股票", "香港联交所股票", ac=AssetClass.EQUITY, it=InstrumentType.STOCK),
    # _sec("上期所", "上期所", ac=AssetClass.COMMODITY, it=InstrumentType.FUTURE),
    # _sec("大商所", "大商所", ac=AssetClass.COMMODITY, it=InstrumentType.FUTURE),
    # _sec("郑商所", "郑商所", ac=AssetClass.COMMODITY, it=InstrumentType.FUTURE),
    # _sec("中金所", "中金所", ac=AssetClass.EQUITY, it=InstrumentType.FUTURE),
    # _sec("能源中心", "能源中心", ac=AssetClass.COMMODITY, it=InstrumentType.FUTURE),
    # _sec("连续合约", "连续合约", ac=AssetClass.COMMODITY, it=InstrumentType.FUTURE),
]
