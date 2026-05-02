# -*- coding: utf-8 -*-
"""
多标的行情批量统一模型（与具体数据源 SDK 返回形态解耦）。

迅投 ``get_market_data_ex`` 在 K 线类 period 下返回 ``dict[合约代码, pd.DataFrame]``，
经适配层转为本模块类型，字段与 ``KlineBar``、``data_schema.KLINE_ROW_FIELDS`` 一致。
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from app.services.data_source.models.kline import KlineBar


class KlineBatchBySymbol(BaseModel):
    """
    多标的 K 线统一视图：合约代码 -> ``KlineBar`` 列表（通常按时间升序）。

    由适配器将上游「按标的分表的 DataFrame」转为标准模型，供 API / 缓存复用。
    """

    model_config = ConfigDict(frozen=False)

    bars_by_symbol: Dict[str, List[KlineBar]] = Field(
        default_factory=dict,
        description="各标的 K 线根序列",
    )
