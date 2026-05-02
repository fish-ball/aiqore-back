# -*- coding: utf-8 -*-
"""
行情数据源协议（Typed Contract），与 adapter 包具体实现及 models 对齐。
注意：与包名 `adapter/` 并存，本文件避免使用 adapter.py 文件名以免与导入冲突。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from app.services.data_source.models import KlineBar, RealtimeQuote


class MarketDataSourceProtocol(Protocol):
    """统一行情能力接口（QMT/其他实现应对齐返回类型）。"""

    def get_stock_list(
        self,
        market: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[Any]:
        ...

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        ...

    def get_klines_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[KlineBar]]:
        ...

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, RealtimeQuote]]:
        ...
