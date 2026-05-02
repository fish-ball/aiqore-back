# -*- coding: utf-8 -*-
"""数据源通用枚举：市场、周期等（证券大类见 app.models.security.SecurityType）。"""
from __future__ import annotations

from enum import Enum

from app.models.security import SecurityType

__all__ = ["MarketCode", "ExchangeCode", "SecurityType", "BarPeriod"]


class MarketCode(str, Enum):
    """常见市场代码（沪深北等地域/交易所后缀）。"""

    SH = "SH"
    SZ = "SZ"
    BJ = "BJ"


class ExchangeCode(str, Enum):
    """常见沪深北证券交易所代码（接口参数等场景）。"""

    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


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
