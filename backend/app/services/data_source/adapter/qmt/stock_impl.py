# -*- coding: utf-8 -*-
"""股票类标的（含指数、基金、ETF）：列表、板块、搜索。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.data_source.adapter.qmt.core import DEFAULT_SECTORS
from app.services.data_source.adapter.qmt.kline_fetch import fetch_klines
from app.services.data_source.models.instrument import InstrumentBrief
from app.services.data_source.models.kline import KlineBar

logger = logging.getLogger(__name__)


class QMTStockLikeMixin:
    """股票类行情与列表能力（与 QMTAdapter 组合使用）。"""

    _config: Dict[str, Any]

    def _get_xtdata(self) -> Any:
        raise NotImplementedError

    def get_stock_list(
        self,
        market: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[InstrumentBrief]:
        if sector:
            return self.get_stock_list_in_sector(sector, market)
        xtdata = self._get_xtdata()
        all_securities: List[InstrumentBrief] = []
        seen_symbols: set[str] = set()
        sectors: List[str] = []
        try:
            if hasattr(xtdata, "get_sector_list"):
                s = xtdata.get_sector_list()
                if s:
                    sectors = list(s)
        except Exception:
            pass
        if not sectors:
            sectors = DEFAULT_SECTORS
        for sec_name in sectors:
            try:
                securities = xtdata.get_stock_list_in_sector(sec_name)
                if securities:
                    for sec in securities:
                        if isinstance(sec, str) and sec not in seen_symbols:
                            m = (
                                "SH"
                                if sec.endswith(".SH")
                                else "SZ"
                                if sec.endswith(".SZ")
                                else "BJ"
                                if sec.endswith(".BJ")
                                else "SH"
                            )
                            if market is None or m == market:
                                all_securities.append(
                                    InstrumentBrief(symbol=sec, market=m, sector=sec_name)
                                )
                                seen_symbols.add(sec)
            except Exception:
                continue
        try:
            if hasattr(xtdata, "get_instrument_list"):
                for exchange in ["SSE", "SZSE", "BSE"]:
                    try:
                        instruments = xtdata.get_instrument_list(exchange)
                        if instruments:
                            for inst in instruments:
                                if isinstance(inst, str) and inst not in seen_symbols:
                                    m = (
                                        "SH"
                                        if inst.endswith(".SH")
                                        else "SZ"
                                        if inst.endswith(".SZ")
                                        else "BJ"
                                        if inst.endswith(".BJ")
                                        else "SH"
                                    )
                                    if market is None or m == market:
                                        all_securities.append(
                                            InstrumentBrief(
                                                symbol=inst,
                                                market=m,
                                                sector="全部标的",
                                            )
                                        )
                                        seen_symbols.add(inst)
                    except Exception:
                        continue
        except Exception:
            pass
        return all_securities

    def get_stock_list_in_sector(
        self,
        sector: str,
        market: Optional[str] = None,
    ) -> List[InstrumentBrief]:
        xtdata = self._get_xtdata()
        try:
            securities = xtdata.get_stock_list_in_sector(sector)
            if not securities:
                return []
            result: List[InstrumentBrief] = []
            for sec in securities:
                if isinstance(sec, str):
                    m = (
                        "SH"
                        if sec.endswith(".SH")
                        else "SZ"
                        if sec.endswith(".SZ")
                        else "BJ"
                        if sec.endswith(".BJ")
                        else "SH"
                    )
                    if market is None or m == market:
                        result.append(InstrumentBrief(symbol=sec, market=m, sector=sector))
            return result
        except Exception as e:
            logger.error("获取板块 '%s' 证券列表失败: %s", sector, e)
            return []

    def get_sector_list(self) -> List[str]:
        """获取板块列表（供 sector_service 等使用）。"""
        xtdata = self._get_xtdata()
        try:
            if hasattr(xtdata, "get_sector_list"):
                s = xtdata.get_sector_list()
                return list(s) if s else []
        except Exception:
            pass
        return DEFAULT_SECTORS.copy()

    def search_stocks(self, keyword: str) -> List[InstrumentBrief]:
        xtdata = self._get_xtdata()
        all_stocks = self.get_stock_list()
        results: List[InstrumentBrief] = []
        keyword_upper = keyword.upper()
        matched_symbols: List[str] = []
        for stock in all_stocks:
            symbol = stock.symbol
            if keyword_upper in symbol.upper():
                matched_symbols.append(symbol)
                results.append(
                    InstrumentBrief(
                        symbol=symbol,
                        name="",
                        market=stock.market,
                        sector=stock.sector,
                    )
                )
        if matched_symbols and hasattr(xtdata, "get_instrument_detail"):
            for symbol in matched_symbols:
                try:
                    detail = xtdata.get_instrument_detail(symbol)
                    if detail and isinstance(detail, dict):
                        n = detail.get("InstrumentName", "")
                        if n:
                            for r in results:
                                if r.symbol == symbol:
                                    r.name = n
                                    break
                except Exception:
                    pass
        return results[:50]

    def _get_klines_stock_like(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[KlineBar]]:
        """股票类（含指数、基金）K 线。"""
        xtdata = self._get_xtdata()
        return fetch_klines(xtdata, symbol, period, count, start_time, end_time)
