# -*- coding: utf-8 -*-
"""根据 market、数据源 ExchangeID、合约后缀解析规范 exchange_code（对照 app.constants.exchanges）。"""
from __future__ import annotations

from typing import Any, Optional

from app.constants.exchanges import (
    MARKET_TO_EXCHANGE_CODE,
    SUFFIX_TO_EXCHANGE_CODE,
    get_exchange_def,
    normalize_exchange_code,
)


def resolve_exchange_code_for_security(
    *,
    market: str,
    qmt_exchange_id: Optional[Any],
    symbol: str,
) -> Optional[str]:
    """
    解析证券对应的规范 exchange_code。
    优先级：数据源 ExchangeID（含别名）> 代码后缀 > 现货 market（SH/SZ/BJ）。
    """
    if qmt_exchange_id is not None:
        canonical = normalize_exchange_code(str(qmt_exchange_id).strip())
        if canonical and get_exchange_def(canonical):
            return canonical

    if symbol and "." in symbol:
        suf = symbol.rsplit(".", 1)[1].strip().lower()
        code = SUFFIX_TO_EXCHANGE_CODE.get(suf)
        if code and get_exchange_def(code):
            return code

    m = (market or "").strip().upper()
    if m in MARKET_TO_EXCHANGE_CODE:
        code = MARKET_TO_EXCHANGE_CODE[m]
        if get_exchange_def(code):
            return code

    return None


def ensure_exchange_code_for_security(
    *,
    market: str,
    qmt_exchange_id: Optional[Any],
    symbol: str,
    existing_exchange_code: Optional[str],
) -> str:
    """
    得到可写入主表的 exchange_code：先解析；否则保留已有（若在目录内）；再按现货市场与期货兜底。
    """
    resolved = resolve_exchange_code_for_security(
        market=market, qmt_exchange_id=qmt_exchange_id, symbol=symbol
    )
    if resolved:
        return resolved
    if existing_exchange_code:
        ex = normalize_exchange_code(existing_exchange_code)
        if ex and get_exchange_def(ex):
            return ex
    m = (market or "").strip().upper()
    if m in MARKET_TO_EXCHANGE_CODE:
        return MARKET_TO_EXCHANGE_CODE[m]
    if get_exchange_def("SHFE"):
        return "SHFE"
    return "SSE"
