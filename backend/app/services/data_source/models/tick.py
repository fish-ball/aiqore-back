# -*- coding: utf-8 -*-
"""分笔（tick）统一行模型（由 ndarray/dict 转换后的轻量结构）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TickRow(BaseModel):
    """单笔 tick 归一化行（与旧版 _tick_row_to_standard 输出对齐）。"""

    model_config = ConfigDict(populate_by_name=True)

    time: int = Field(..., description="UNIX 毫秒时间戳")
    date: str = Field(..., description="交易日 YYYY-MM-DD")
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = Field(0.0, description="成交价，对应 lastPrice")
    volume: int = 0
    amount: float = 0.0
    lastClose: Optional[float] = None
    askPrice: Optional[float] = None
    bidPrice: Optional[float] = None
    askVol: Optional[int] = None
    bidVol: Optional[int] = None
    transactionNum: Optional[int] = None
