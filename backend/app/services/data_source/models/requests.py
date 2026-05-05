# -*- coding: utf-8 -*-
"""行情请求参数模型（适配器层统一入参，可选使用）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.services.data_source.models.enums import MarketLayer


class KlineQuery(BaseModel):
    """K 线查询参数。"""

    symbol: str
    period: str = "1d"
    count: int = 100
    start_time: Optional[str] = Field(None, description="YYYY-MM-DD 或 HH:MM:SS 组合")
    end_time: Optional[str] = None
    market_layer: Optional[MarketLayer] = Field(
        None,
        description="显式指定行情分层（Equity/Future/Option）；未指定时由 symbol 推断",
    )


class TickQuery(BaseModel):
    """分笔查询。"""

    symbol: str
    trade_date: str = Field(..., description="YYYYMMDD 或 YYYY-MM-DD")
    market_layer: Optional[MarketLayer] = None


class DividFactorsQuery(BaseModel):
    """除权因子查询。"""

    symbol: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
