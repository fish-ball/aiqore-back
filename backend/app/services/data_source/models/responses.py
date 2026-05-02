# -*- coding: utf-8 -*-
"""行情响应包装（便于序列化与多实现对齐）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.data_source.models.enums import SecurityType
from app.services.data_source.models.instrument import InstrumentBrief
from app.services.data_source.models.kline import KlineBar
from app.services.data_source.models.quote import RealtimeQuote


class KlineDataResponse(BaseModel):
    """K 线数据响应。"""

    symbol: str
    period: str
    security_type: SecurityType
    bars: List[KlineBar] = Field(default_factory=list)


class RealtimeQuoteBatchResponse(BaseModel):
    """批量实时行情。"""

    quotes: Dict[str, RealtimeQuote] = Field(default_factory=dict)


class InstrumentListResponse(BaseModel):
    """证券列表。"""

    items: List[InstrumentBrief] = Field(default_factory=list)


class ConnectionTestResponse(BaseModel):
    """连接测试结果。"""

    ok: bool
    message: str
    extra: Optional[Dict[str, Any]] = None
