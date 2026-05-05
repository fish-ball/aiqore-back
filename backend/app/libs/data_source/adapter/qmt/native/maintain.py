# -*- coding: utf-8 -*-
"""
行情数据维护类原生调用：下载本地历史 K/分笔等（对应 xtdata.download_history_data）。
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def download_history_data(
    xtdata: Any,
    stockcode: str,
    period: str,
    start_time: str = "",
    end_time: str = "",
    *,
    incrementally: Optional[bool] = None,
) -> None:
    """
    调用 xtdata.download_history_data(stockcode, period=..., start_time=..., end_time=..., incrementally=...)。

    参数与迅投文档一致：stockcode 形如 600000.SH；period 如 1d、1m、tick；
    start_time/end_time 为 YYYYMMDD 或 YYYYMMDDhhmmss，可为空串。
    Python 绑定使用关键字 period、start_time、end_time（对应文档 startTime、endTime）。
    若当前 xtdata 无 download_history_data 则直接返回（不抛异常）。
    """
    if not hasattr(xtdata, "download_history_data"):
        return
    kwargs: Dict[str, Any] = {
        "period": period,
        "start_time": start_time or "",
        "end_time": end_time or "",
    }
    if incrementally is not None:
        kwargs["incrementally"] = incrementally
    xtdata.download_history_data(stockcode, **kwargs)
