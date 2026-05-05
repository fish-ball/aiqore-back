# -*- coding: utf-8 -*-
"""K 线统一数据模型。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KlineBar(BaseModel):
    """
    标准化 K 线单根 Bar。
    字段与 cache.KLINE_COLUMNS 一致，便于 parquet 与缓存层复用。
    """

    model_config = ConfigDict(populate_by_name=True, frozen=False)

    time: int = Field(..., description="UNIX 毫秒时间戳")
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    settle: float = Field(0.0, description="今结算（股票多为 0）")
    openInterest: int = Field(0, description="持仓量（股票多为 0）")
    preClose: float = Field(0.0, description="前收盘价")
    suspendFlag: int = Field(0, description="停牌 1 停牌，0 不停牌")
