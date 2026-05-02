# -*- coding: utf-8 -*-
"""实时行情统一模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RealtimeQuote(BaseModel):
    """单标的实时快照（由 get_full_tick + 可选名称解析）。"""

    symbol: str
    name: str = ""
    last_price: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    time: str = Field(..., description="行情时间 ISO 字符串或上游约定格式")
