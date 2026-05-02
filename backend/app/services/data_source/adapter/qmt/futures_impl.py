# -*- coding: utf-8 -*-
"""期货类标的：K 线等与 xtdata 交互（当前与股票类共用 fetch_klines）。"""
from __future__ import annotations

from typing import Any, List, Optional

from app.services.data_source.adapter.qmt.kline_fetch import fetch_klines
from app.services.data_source.models.kline import KlineBar


class QMTFuturesMixin:
    """期货行情（组合进 QMTAdapter）。"""

    def _get_xtdata(self) -> Any:
        raise NotImplementedError

    def _get_klines_futures(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[KlineBar]]:
        xtdata = self._get_xtdata()
        return fetch_klines(xtdata, symbol, period, count, start_time, end_time)
