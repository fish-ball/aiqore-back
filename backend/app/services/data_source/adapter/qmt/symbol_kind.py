# -*- coding: utf-8 -*-
"""根据合约代码推断行情分层（股票类 / 期货 / 期权）。"""
from __future__ import annotations

from app.services.data_source.adapter.qmt.mappings import FUTURES_EXCHANGE_SUFFIXES
from app.services.data_source.models.enums import MarketLayer


def infer_market_layer(symbol: str) -> MarketLayer:
    """
    推断行情分层：沪深现货、指数、基金等均视为 Equity；期货、期权单独分类。
    """
    if not symbol or "." not in symbol:
        return MarketLayer.Equity
    code, suf = symbol.rsplit(".", 1)
    suf_l = suf.lower()
    if suf_l in FUTURES_EXCHANGE_SUFFIXES:
        return MarketLayer.Future
    code_u = code.upper()
    if "-C-" in code_u or "-P-" in code_u:
        return MarketLayer.Option
    if suf_l in ("sh", "sz", "bj") and code.isdigit() and len(code) > 6:
        return MarketLayer.Option
    return MarketLayer.Equity
