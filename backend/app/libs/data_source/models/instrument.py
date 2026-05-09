# -*- coding: utf-8 -*-
"""证券列表、搜索等基础结构。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class InstrumentBrief(BaseModel):
    """证券列表/搜索结果中的简要条目。"""

    symbol: str
    market: str = ""
    sector: str = ""
    name: str = ""


class DataSourceInstrument(BaseModel):
    """
    数据源侧标的详情（与 QMT / Tushare 等 SDK 原始字典解耦）。
    字段语义对齐迅投常见键，便于适配器从各来源填充。
    """

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field("", description="合约代码，如 600000.SH")
    name: str = Field("", description="证券名称")
    instrument_type: str = Field("", description="数据源侧品种类型原始字符串")
    exchange_id: str = Field("", description="交易所标识，如 SSE")
    open_date: Optional[Any] = Field(None, description="上市日，原始类型由数据源决定")
    expiry_date: Optional[Any] = Field(None, description="到期日")
    last_price: Optional[float] = Field(None, description="最近价，无则 None")
