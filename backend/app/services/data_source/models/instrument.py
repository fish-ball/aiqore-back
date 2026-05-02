# -*- coding: utf-8 -*-
"""证券列表、搜索等基础结构。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class InstrumentBrief(BaseModel):
    """证券列表/搜索结果中的简要条目。"""

    symbol: str
    market: str = ""
    sector: str = ""
    name: str = ""


class InstrumentDetailView(BaseModel):
    """
    标的详情视图：封装 xt get_instrument_detail 常用字段，未知结构时保留 raw。
    """

    symbol: str
    raw: Dict[str, Any] = Field(default_factory=dict)
    instrument_name: Optional[str] = Field(None, description="InstrumentName 等")
