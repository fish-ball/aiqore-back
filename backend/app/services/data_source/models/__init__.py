# -*- coding: utf-8 -*-
"""
数据源统一 Pydantic 模型与枚举（与具体数据源 SDK 解耦）。
多标的 K 线批量见 ``market_data.KlineBatchBySymbol``；迅投等适配器专属映射放在
``app.services.data_source.adapter.qmt`` 等实现包中。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.data_source.models.enums import (
    ExchangeCode,
    MarketCode,
    SecurityType,
    BarPeriod,
)
from app.services.data_source.models.instrument import InstrumentBrief, InstrumentDetailView
from app.services.data_source.models.kline import KlineBar
from app.services.data_source.models.market_data import KlineBatchBySymbol
from app.services.data_source.models.quote import RealtimeQuote
from app.services.data_source.models.requests import DividFactorsQuery, KlineQuery, TickQuery
from app.services.data_source.models.responses import (
    ConnectionTestResponse,
    InstrumentListResponse,
    KlineDataResponse,
    RealtimeQuoteBatchResponse,
)
from app.services.data_source.models.tick import TickRow


def kline_rows_to_dicts(rows: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """将 K 线序列转为 dict 列表，兼容 parquet/cache 等仍使用 dict 的路径。"""
    if not rows:
        return []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if hasattr(r, "model_dump"):
            out.append(r.model_dump())
        else:
            out.append(r)  # type: ignore[arg-type]
    return out


__all__ = [
    "ExchangeCode",
    "MarketCode",
    "SecurityType",
    "BarPeriod",
    "InstrumentBrief",
    "InstrumentDetailView",
    "KlineBar",
    "KlineBatchBySymbol",
    "RealtimeQuote",
    "KlineQuery",
    "TickQuery",
    "DividFactorsQuery",
    "KlineDataResponse",
    "RealtimeQuoteBatchResponse",
    "InstrumentListResponse",
    "ConnectionTestResponse",
    "TickRow",
    "kline_rows_to_dicts",
]
