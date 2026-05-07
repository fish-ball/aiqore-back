# -*- coding: utf-8 -*-
"""xtquant DataFrame 行转为统一 K 线模型；get_market_data_ex K 线结果适配。"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

import pandas as pd

from app.libs.data_source.models.kline import KlineBar


def xt_row_to_kline(row: Any) -> KlineBar:
    """xtquant 单行（DataFrame row）转为标准 K 线模型。"""
    t = row.get("time")
    try:
        time_ms = int(float(t)) if t is not None else 0
    except (TypeError, ValueError):
        time_ms = 0

    def _f(key: str, default: float = 0) -> float:
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0) -> int:
        v = row.get(key)
        if v is None:
            return default
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    vol = row.get("volume", row.get("vol"))
    vol = int(float(vol)) if vol is not None else 0
    return KlineBar(
        time=time_ms,
        open=_f("open"),
        high=_f("high"),
        low=_f("low"),
        close=_f("close"),
        volume=vol,
        amount=_f("amount"),
        settle=_f("settle"),
        openInterest=_i("openInterest"),
        preClose=_f("preClose"),
        suspendFlag=_i("suspendFlag"),
    )


def rows_from_symbol_df(df: Any) -> List[KlineBar]:
    """从 xtquant 单标的 DataFrame 转为标准 K 线列表。结算价列 ``settelementPrice`` 映射为 ``settle``。"""
    if df is not None and hasattr(df, "columns"):
        cols = getattr(df, "columns", None)
        if cols is not None and "settelementPrice" in cols and "settle" not in cols:
            df = df.rename(columns={"settelementPrice": "settle"})
    return [xt_row_to_kline(row) for _, row in df.iterrows()]


def adapt_xt_get_market_data_ex_kline(
    raw: Any,
    *,
    expected_symbols: Sequence[str],
) -> Dict[str, List[KlineBar]]:
    """
    将 ``get_market_data_ex`` 在 K 线周期下的 dict[合约, DataFrame] 转为 dict[合约, KlineBar 列表]。

    - DataFrame 为空：空列表。
    - 无 time 列且表非空：无法构成 KlineBar，空列表。
    """
    if not isinstance(raw, dict):
        raise TypeError(
            f"get_market_data_ex（K 线）预期顶层为 dict，实为 {type(raw).__name__}"
        )
    missing = [s for s in expected_symbols if s not in raw]
    if missing:
        raise ValueError(f"缺少合约键: {missing}，当前键 {list(raw.keys())}")
    out: Dict[str, List[KlineBar]] = {}
    for sym in expected_symbols:
        v = raw[sym]
        if not isinstance(v, pd.DataFrame):
            raise TypeError(
                f"合约 {sym!r} 预期 pd.DataFrame，实为 {type(v).__name__}"
            )
        if v.empty:
            out[sym] = []
            continue
        if "time" not in v.columns:
            out[sym] = []
            continue
        out[sym] = rows_from_symbol_df(v)
    return out
