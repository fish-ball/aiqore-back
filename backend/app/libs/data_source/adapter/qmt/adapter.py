# -*- coding: utf-8 -*-
"""QMTAdapter：xtdata 证券列表、K 线、分笔、实时行情等。"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.adapter.qmt.core import DEFAULT_SECTORS, ensure_xtdata
from app.libs.data_source.adapter.qmt.kline_fetch import fetch_klines
from app.libs.data_source.adapter.qmt.mappings import to_xtdata_time
from app.libs.data_source.adapter.qmt.native.maintain import download_history_data
from app.libs.data_source.models import DataSourceSector, MarketLayer
from app.libs.data_source.models.instrument import InstrumentBrief
from app.libs.data_source.models.kline import KlineBar
from app.libs.data_source.models.quote import RealtimeQuote

logger = logging.getLogger(__name__)


class QMTAdapter(DataSourceAdapter):
    """QMT 适配器：直接调用 xtquant.xtdata。"""

    @property
    def name(self) -> str:
        return "qmt"

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}
        self._xt_quant_path = self._config.get("xt_quant_path") or None
        self._xt_quant_acct = self._config.get("xt_quant_acct") or None

    def _get_xtdata(self) -> Any:
        xtdata = ensure_xtdata(self._xt_quant_path)
        if xtdata is None:
            raise RuntimeError("xtquant 未安装或不可用，请确保已安装 miniQMT 并配置 xt_quant_path")
        return xtdata

    def test_connection(self) -> tuple[bool, str]:
        base = Path(self._xt_quant_path) if self._xt_quant_path else None
        if not base or not base.is_dir():
            return False, "xtquant 路径不存在或不可用"
        acct = (self._xt_quant_acct or "").strip()
        if acct:
            acct_dir = base / "users" / acct
            if not acct_dir.is_dir():
                return False, f"账号 {acct} 在配置路径下不存在对应文件夹，视作连接失败"
        try:
            xtdata = ensure_xtdata(self._xt_quant_path)
            if xtdata is None:
                return False, "xtquant 未安装或不可用，请确保已安装 miniQMT 并将 xtquant 路径配置正确"
            if hasattr(xtdata, "get_sector_list"):
                xtdata.get_sector_list()
            elif hasattr(xtdata, "get_stock_list_in_sector"):
                xtdata.get_stock_list_in_sector("沪深A股")
            else:
                return False, "当前 xtquant 版本无可用探测接口"
            return True, "连接成功"
        except Exception as e:
            logger.exception("QMT 连接测试异常")
            return False, str(e)

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        xtdata = self._get_xtdata()
        try:
            if hasattr(xtdata, "get_instrument_detail"):
                return xtdata.get_instrument_detail(symbol)
        except Exception:
            pass
        return None

    def get_klines_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[KlineBar]]:
        """K 线（股票/期货/期权均走同一 xt 接口）。"""
        return fetch_klines(
            self._get_xtdata(), symbol, period, count, start_time, end_time
        )

    def get_ticks_data(self, symbol: str, trade_date: str) -> Optional[Any]:
        """
        按交易日拉取分笔数据。使用 get_market_data_ex(period='tick', dividend_type='none', fill_data=False)，
        不传 count，仅返回历史行情。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        返回 pandas DataFrame，列与迅投 tick 行情一致；否则返回 None。
        """
        trade_date_flat = trade_date.replace("-", "")[:8]
        if len(trade_date_flat) != 8:
            return None
        st = f"{trade_date_flat[:4]}{trade_date_flat[4:6]}{trade_date_flat[6:8]}000000"
        et = f"{trade_date_flat[:4]}{trade_date_flat[4:6]}{trade_date_flat[6:8]}235959"
        xtdata = self._get_xtdata()
        if not xtdata:
            return None
        try:
            try:
                download_history_data(
                    xtdata,
                    symbol,
                    "tick",
                    start_time=st,
                    end_time=et,
                )
            except Exception as dl_e:
                logger.warning("download_history_data tick 失败（继续尝试获取）: %s", dl_e)
            if not hasattr(xtdata, "get_market_data_ex"):
                logger.warning("当前 xtdata 无 get_market_data_ex，无法拉取分笔")
                return None
            data = xtdata.get_market_data_ex(
                stock_list=[symbol],
                period="tick",
                dividend_type="none",
                fill_data=False,
                start_time=st,
                end_time=et,
            )
            if not data or symbol not in data:
                return None
            arr = data[symbol]
            if arr is None:
                return None
            try:
                import pandas as pd

                if isinstance(arr, pd.DataFrame):
                    return arr
            except ImportError:
                pass
            return None
        except Exception as e:
            logger.error("获取分笔数据失败 %s %s: %s", symbol, trade_date_flat, e)
            return None

    def get_divid_factors(
        self,
        symbol: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[Any]:
        """
        获取除权数据，直接封装 xtdata.get_divid_factors。
        start_time/end_time 支持 YYYY-MM-DD 或 YYYYMMDD，内部转换为 xtdata 需要的格式。
        """
        xtdata = self._get_xtdata()
        if not hasattr(xtdata, "get_divid_factors"):
            logger.warning("当前 xtdata 版本不支持 get_divid_factors，无法获取除权数据")
            return None
        st = to_xtdata_time(start_time) if start_time else ""
        et = to_xtdata_time(end_time) if end_time else ""
        try:
            df = xtdata.get_divid_factors(symbol, start_time=st or "", end_time=et or "")
            return df
        except Exception as e:
            logger.error("获取除权数据失败 %s: %s", symbol, e)
            return None

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, RealtimeQuote]]:
        xtdata = self._get_xtdata()
        try:
            quotes = xtdata.get_full_tick(symbols)
            names: Dict[str, str] = {}
            if hasattr(xtdata, "get_instrument_detail"):
                for symbol in symbols:
                    try:
                        detail = xtdata.get_instrument_detail(symbol)
                        if detail and isinstance(detail, dict):
                            n = detail.get("InstrumentName", "")
                            if n:
                                names[symbol] = n
                    except Exception:
                        pass
            result: Dict[str, RealtimeQuote] = {}
            now_iso = datetime.now().isoformat()
            for symbol in symbols:
                name = names.get(symbol, "")
                if quotes and symbol in quotes:
                    tick = quotes[symbol]
                    if isinstance(tick, dict):
                        last_price = float(tick.get("lastPrice", 0))
                        open_p = float(tick.get("open", 0))
                        high = float(tick.get("high", 0))
                        low = float(tick.get("low", 0))
                        pre_close = float(tick.get("lastClose", 0))
                        volume = int(tick.get("volume", 0))
                        amount = float(tick.get("amount", 0))
                    else:
                        last_price = open_p = high = low = pre_close = amount = 0.0
                        volume = 0
                    result[symbol] = RealtimeQuote(
                        symbol=symbol,
                        name=name,
                        last_price=last_price,
                        open=open_p,
                        high=high,
                        low=low,
                        pre_close=pre_close,
                        volume=volume,
                        amount=amount,
                        time=now_iso,
                    )
                else:
                    result[symbol] = RealtimeQuote(
                        symbol=symbol,
                        name=name,
                        last_price=0.0,
                        open=0.0,
                        high=0.0,
                        low=0.0,
                        pre_close=0.0,
                        volume=0,
                        amount=0.0,
                        time=now_iso,
                    )
            return result
        except Exception as e:
            logger.error("获取实时行情失败: %s", e)
            return None

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

    def get_sector_list(self) -> List[DataSourceSector]:
        """
        板块列表：当前为扁平列表，每项无 children；资产类别暂统一为 Equity（后续可按板块细分）。
        """
        xtdata = self._get_xtdata()
        names: List[str] = []
        try:
            if hasattr(xtdata, "get_sector_list"):
                s = xtdata.get_sector_list()
                if s:
                    names = list(s)
        except Exception:
            pass
        if not names:
            names = DEFAULT_SECTORS.copy()
        return [
            DataSourceSector(name=n, alias=n, asset_class=MarketLayer.Equity, children=[])
            for n in names
            if n
        ]

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


# 命令行连通性自检：在 backend 目录下执行
#   python -m app.libs.data_source.adapter.qmt.adapter [xt_quant_path] [xt_quant_acct]
def _cli_main() -> None:
    import sys as _sys

    DEFAULT_TEST_PATH = r"C:\国金证券QMT交易端\userdata_mini"
    DEFAULT_TEST_ACCT = "39271919"
    if len(_sys.argv) > 1:
        path = _sys.argv[1].strip()
        acct = (_sys.argv[2].strip() if len(_sys.argv) > 2 else None) or DEFAULT_TEST_ACCT
        cfg = {"xt_quant_path": path, "xt_quant_acct": acct}
    else:
        cfg = {"xt_quant_path": DEFAULT_TEST_PATH, "xt_quant_acct": DEFAULT_TEST_ACCT}
    adapter = QMTAdapter(cfg)
    ok, msg = adapter.test_connection()
    print("连通性测试:", "通过" if ok else "失败", "-", msg)
    _sys.exit(0 if ok else 1)


if __name__ == "__main__":
    _cli_main()
