# -*- coding: utf-8 -*-
"""根据合约代码推断证券大类（股票类 / 期货 / 期权）。"""
from __future__ import annotations

from app.services.data_source.adapter.qmt.mappings import FUTURES_EXCHANGE_SUFFIXES
from app.services.data_source.models.enums import SecurityType


def infer_security_type(symbol: str) -> SecurityType:
    """
    推断证券大类：沪深现货、指数、基金等均视为 Equity；期货、期权单独分类。
    """
    if not symbol or "." not in symbol:
        return SecurityType.Equity
    code, suf = symbol.rsplit(".", 1)
    suf_l = suf.lower()
    if suf_l in FUTURES_EXCHANGE_SUFFIXES:
        return SecurityType.Future
    code_u = code.upper()
    if "-C-" in code_u or "-P-" in code_u:
        return SecurityType.Option
    if suf_l in ("sh", "sz", "bj") and code.isdigit() and len(code) > 6:
        return SecurityType.Option
    return SecurityType.Equity
