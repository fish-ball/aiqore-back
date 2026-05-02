# -*- coding: utf-8 -*-
"""
xtdata.get_market_data_ex 与 data_source 统一模型的适配。

迅投文档：K 线类 period 返回 ``dict[stock_code, pd.DataFrame]``，列含 time、OHLC 等；
本模块将各标的 DataFrame 转为 ``KlineBatchBySymbol``（元素为 ``KlineBar``）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

import pandas as pd

from app.services.data_source.adapter.qmt.convert import rows_from_symbol_df
from app.services.data_source.models.kline import KlineBar
from app.services.data_source.models.market_data import KlineBatchBySymbol


def adapt_xt_get_market_data_ex_kline(
    raw: Any,
    *,
    expected_symbols: Sequence[str],
) -> KlineBatchBySymbol:
    """
    将 ``get_market_data_ex`` 在 K 线周期下的返回值转为 ``KlineBatchBySymbol``。

    - 某标的 DataFrame 为空：对应空列表。
    - 无 ``time`` 列且表非空（例如仅 field_list 请求部分字段）：无法构成 ``KlineBar``，对应空列表。
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
    return KlineBatchBySymbol(bars_by_symbol=out)
