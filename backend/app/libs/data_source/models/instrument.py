# -*- coding: utf-8 -*-
"""证券列表、搜索等基础结构。"""
from __future__ import annotations

from pydantic import BaseModel


class InstrumentBrief(BaseModel):
    """证券列表/搜索结果中的简要条目。"""

    symbol: str
    market: str = ""
    sector: str = ""
    name: str = ""
