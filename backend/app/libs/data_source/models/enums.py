# -*- coding: utf-8 -*-
"""数据源通用枚举：行情分层类别、K 线周期等。"""
from __future__ import annotations

from enum import Enum

__all__ = ["MarketLayer", "BarPeriod"]


class MarketLayer(str, Enum):
    """
    行情与缓存分层用的三大类（非数据库字段）。
    与 DB instruments.instrument_type 的对应关系见 instrument_type_to_market_layer。
    """

    Equity = "Equity"
    Future = "Future"
    Option = "Option"


class BarPeriod(str, Enum):
    """
    统一 K 线周期（上层 / API / 缓存约定）。
    各数据源适配器自行映射为下游所需字符串。
    """

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"
    M1_MONTH = "1M"
