# -*- coding: utf-8 -*-
"""xtquant DataFrame / ndarray / dict 行转为统一模型。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from datetime import datetime

from app.services.data_source.models.kline import KlineBar


def tick_scalar(val: Any) -> Any:
    """numpy 标量转 Python 原生。"""
    if hasattr(val, "item"):
        return val.item()
    return val


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


def normalize_xt_kline_dataframe(df: Any) -> Any:
    """
    迅投 K 线 DataFrame 列名与 ``KlineBar`` / data_schema 对齐。
    文档与实测中结算价字段为 ``settelementPrice``（拼写），统一映射为 ``settle``。
    """
    if df is None or not hasattr(df, "columns"):
        return df
    cols = getattr(df, "columns", None)
    if cols is not None and "settelementPrice" in cols and "settle" not in cols:
        return df.rename(columns={"settelementPrice": "settle"})
    return df


def rows_from_symbol_df(df: Any) -> List[KlineBar]:
    """从 xtquant 单标的 DataFrame 转为标准 K 线列表。"""
    df = normalize_xt_kline_dataframe(df)
    return [xt_row_to_kline(row) for _, row in df.iterrows()]


def tick_row_to_standard(row: Dict[str, Any], date_str: str) -> Dict[str, Any]:
    """
    单笔 tick 行转为统一字段。保留 time(毫秒)、date、open、high、low、close(=lastPrice)、volume、amount；
    可选 lastClose、askPrice、bidPrice、askVol、bidVol、transactionNum。
    """
    def _f(key: str, default: float = 0) -> float:
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(tick_scalar(v))
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0) -> int:
        v = row.get(key)
        if v is None:
            return default
        try:
            return int(float(tick_scalar(v)))
        except (TypeError, ValueError):
            return default

    t = row.get("time")
    try:
        time_ms = int(float(t)) if t is not None else 0
    except (TypeError, ValueError):
        time_ms = 0
    out = {
        "time": time_ms,
        "date": date_str,
        "open": _f("open"),
        "high": _f("high"),
        "low": _f("low"),
        "close": _f("lastPrice", _f("close")),
        "volume": _i("volume"),
        "amount": _f("amount"),
    }
    for k in ("lastClose", "askPrice", "bidPrice", "askVol", "bidVol", "transactionNum"):
        if k in row and row[k] is not None:
            out[k] = _f(k) if k in ("lastClose", "askPrice", "bidPrice") else _i(k)
    return out


def tick_ndarray_to_rows(arr: Any, trade_date_flat: str) -> List[Dict[str, Any]]:
    """将 xtdata period=tick 返回的 ndarray 转为统一分笔行列表。"""
    result: List[Dict[str, Any]] = []
    date_str = f"{trade_date_flat[:4]}-{trade_date_flat[4:6]}-{trade_date_flat[6:8]}"
    names = getattr(arr.dtype, "names", None) if hasattr(arr, "dtype") else None
    if names:
        for i in range(len(arr)):
            row = {n: tick_scalar(arr[n][i]) for n in names}
            result.append(tick_row_to_standard(row, date_str))
    elif getattr(arr, "shape", None) == (0,) or len(arr) == 0:
        pass
    else:
        for i in range(len(arr)):
            rec = arr[i]
            names_i = getattr(rec.dtype, "names", None) if hasattr(rec, "dtype") else None
            if names_i:
                row = {n: tick_scalar(rec[n]) for n in names_i}
            else:
                row = {}
            result.append(tick_row_to_standard(row, date_str))
    return result


def tick_list_to_rows(items: List[Any], trade_date_flat: str) -> List[Dict[str, Any]]:
    """将 list 形式的分笔数据转为统一行列表。"""
    date_str = f"{trade_date_flat[:4]}-{trade_date_flat[4:6]}-{trade_date_flat[6:8]}"
    result: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            result.append(tick_row_to_standard(item, date_str))
        else:
            result.append(tick_row_to_standard({}, date_str))
    return result
