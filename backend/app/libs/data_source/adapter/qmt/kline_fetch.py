# -*- coding: utf-8 -*-
"""从 xtdata 拉取 K 线并转为 KlineBar 列表（股票/期货/期权共用 xt API）。"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from app.libs.data_source.adapter.qmt.convert import rows_from_symbol_df, xt_row_to_kline
from app.libs.data_source.adapter.qmt.native.maintain import download_history_data
from app.libs.data_source.adapter.qmt.mappings import normalize_period_to_xt, to_xtdata_time
from app.libs.data_source.models.kline import KlineBar

logger = logging.getLogger(__name__)


def fetch_klines(
    xtdata: Any,
    symbol: str,
    period: str = "1d",
    count: int = 100,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> Optional[List[KlineBar]]:
    """
    K 线数据：将 xtquant 返回转为 KlineBar 列表。
    失败返回 None；无数据返回空列表。
    """
    st = to_xtdata_time(start_time)
    et = to_xtdata_time(end_time)
    xt_period = normalize_period_to_xt(period)
    try:
        try:
            download_history_data(
                xtdata,
                symbol,
                xt_period,
                start_time=st or "",
                end_time=et or "",
            )
        except Exception as dl_e:
            logger.warning("download_history_data 失败（继续尝试获取）: %s", dl_e)
        data = xtdata.get_market_data(
            stock_list=[symbol],
            period=xt_period,
            count=count,
            start_time=st or "",
            end_time=et or "",
        )
        if not data:
            logger.debug(
                "get_klines_data 无数据: symbol=%s period=%s start=%s end=%s",
                symbol,
                xt_period,
                st,
                et,
            )
            return []
        if symbol in data:
            df = data[symbol]
            if df is not None and not df.empty:
                return rows_from_symbol_df(df)
        time_df = data.get("time")
        if time_df is None or not hasattr(time_df, "loc"):
            logger.debug(
                "get_klines_data 无 time 字段: symbol=%s data_keys=%s",
                symbol,
                list(data.keys()) if isinstance(data, dict) else type(data),
            )
            return []
        if symbol not in time_df.index:
            logger.debug("get_klines_data 无该标的: symbol=%s period=%s", symbol, xt_period)
            return []
        time_series = time_df.loc[symbol]
        result: List[KlineBar] = []
        for t_idx, time_val in time_series.items():
            def _v(field: str, default: float = 0) -> float:
                d = data.get(field)
                if d is None or symbol not in d.index:
                    return default
                try:
                    return float(d.loc[symbol, t_idx])
                except Exception:
                    return default

            try:
                time_ms = int(float(time_val))
            except (TypeError, ValueError):
                time_ms = 0
            vol = _v("volume", _v("vol", 0))
            vol_i = int(float(vol)) if vol is not None else 0
            row_dict = {
                "time": time_ms,
                "open": _v("open", 0),
                "high": _v("high", 0),
                "low": _v("low", 0),
                "close": _v("close", 0),
                "volume": vol_i,
                "amount": _v("amount", 0),
                "settle": _v("settle", 0),
                "openInterest": int(float(_v("openInterest", 0))),
                "preClose": _v("preClose", 0),
                "suspendFlag": int(float(_v("suspendFlag", 0))),
            }
            result.append(xt_row_to_kline(row_dict))
        return result
    except Exception as e:
        logger.error("获取 K 线数据失败 %s: %s", symbol, e)
        return None
