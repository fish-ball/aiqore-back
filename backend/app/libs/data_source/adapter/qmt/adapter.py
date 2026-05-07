# -*- coding: utf-8 -*-
"""QMTAdapter：xtdata 证券列表、K 线、分笔、实时行情等。"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.adapter.qmt.core import ensure_xtdata
from app.libs.data_source.adapter.qmt.kline_fetch import fetch_klines
from app.libs.data_source.adapter.qmt.mappings import to_xtdata_time
from app.libs.data_source.models import DataSourceSector, MarketLayer
from app.libs.data_source.models.instrument import InstrumentBrief
from app.libs.data_source.models.kline import KlineBar
from app.libs.data_source.models.quote import RealtimeQuote

logger = logging.getLogger(__name__)


class QMTAdapter(DataSourceAdapter):
    """QMT 适配器：直接调用 xtquant.xtdata。"""

    @staticmethod
    def _market_for_symbol(code: str) -> str:
        """代码后缀推断现货市场：SH / SZ / BJ，缺省 SH。"""
        if code.endswith(".SH"):
            return "SH"
        if code.endswith(".SZ"):
            return "SZ"
        if code.endswith(".BJ"):
            return "BJ"
        return "SH"

    @staticmethod
    def _sector_keys_filtered(raw: Any) -> List[str]:
        """从 xt 板块列表去掉申万/证监会多级键（SW1、SW2、SW3、CSRC1、CSRC2 前缀）。"""
        if not raw:
            return []
        skip = ("SW1", "SW2", "SW3", "CSRC1", "CSRC2")
        out: List[str] = []
        for n in list(raw):
            if not n or not isinstance(n, str):
                continue
            t = n.strip()
            if not t or any(t.startswith(p) for p in skip):
                continue
            out.append(n)
        return out

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
            xtdata.get_sector_list()
            return True, "连接成功"
        except Exception as e:
            logger.exception("QMT 连接测试异常")
            return False, str(e)

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self._get_xtdata().get_instrument_detail(symbol)

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
        try:
            xtdata.download_history_data(
                symbol,
                period="tick",
                start_time=st,
                end_time=et,
            )
        except Exception as dl_e:
            logger.warning("download_history_data tick 失败（继续尝试获取）: %s", dl_e)
        try:
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
            if isinstance(arr, pd.DataFrame):
                return arr
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
        st = to_xtdata_time(start_time) if start_time else ""
        et = to_xtdata_time(end_time) if end_time else ""
        try:
            return xtdata.get_divid_factors(symbol, start_time=st or "", end_time=et or "")
        except Exception as e:
            logger.error("获取除权数据失败 %s: %s", symbol, e)
            return None

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, RealtimeQuote]]:
        xtdata = self._get_xtdata()
        try:
            quotes = xtdata.get_full_tick(symbols)
            names: Dict[str, str] = {}
            for symbol in symbols:
                detail = xtdata.get_instrument_detail(symbol)
                if detail and isinstance(detail, dict):
                    n = detail.get("InstrumentName", "")
                    if n:
                        names[symbol] = n
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
        sectors = self._sector_keys_filtered(xtdata.get_sector_list())
        for sec_name in sectors:
            securities = xtdata.get_stock_list_in_sector(sec_name)
            if securities:
                for sec in securities:
                    if isinstance(sec, str) and sec not in seen_symbols:
                        m = self._market_for_symbol(sec)
                        if market is None or m == market:
                            all_securities.append(
                                InstrumentBrief(symbol=sec, market=m, sector=sec_name)
                            )
                            seen_symbols.add(sec)
        for exchange in ["SSE", "SZSE", "BSE"]:
            instruments = xtdata.get_instrument_list(exchange)
            if instruments:
                for inst in instruments:
                    if isinstance(inst, str) and inst not in seen_symbols:
                        m = self._market_for_symbol(inst)
                        if market is None or m == market:
                            all_securities.append(
                                InstrumentBrief(
                                    symbol=inst,
                                    market=m,
                                    sector="全部标的",
                                )
                            )
                            seen_symbols.add(inst)
        return all_securities

    def get_stock_list_in_sector(
        self,
        sector: str,
        market: Optional[str] = None,
    ) -> List[InstrumentBrief]:
        xtdata = self._get_xtdata()
        securities = xtdata.get_stock_list_in_sector(sector)
        if not securities:
            return []
        result: List[InstrumentBrief] = []
        for sec in securities:
            if isinstance(sec, str):
                m = self._market_for_symbol(sec)
                if market is None or m == market:
                    result.append(InstrumentBrief(symbol=sec, market=m, sector=sector))
        return result

    def get_sector_list(self) -> List[DataSourceSector]:
        """
        板块列表：当前为扁平列表，每项无 children；资产类别暂统一为 Equity（后续可按板块细分）。
        跳过申万/证监会多级板块键（SW1、SW2、SW3、CSRC1、CSRC2 前缀）。
        """
        xtdata = self._get_xtdata()
        names = self._sector_keys_filtered(xtdata.get_sector_list())
        return [
            DataSourceSector(name=n, alias=n, asset_class=MarketLayer.Equity, children=[])
            for n in names
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
        if matched_symbols:
            for symbol in matched_symbols:
                detail = xtdata.get_instrument_detail(symbol)
                if detail and isinstance(detail, dict):
                    n = detail.get("InstrumentName", "")
                    if n:
                        for r in results:
                            if r.symbol == symbol:
                                r.name = n
                                break
        return results[:50]


if __name__ == "__main__":
    # 命令行自检：python -m app.libs.data_source.adapter.qmt.adapter [xt_quant_path] [xt_quant_acct]
    if len(sys.argv) > 1:
        cli_cfg: Dict[str, Any] = {
            "xt_quant_path": sys.argv[1].strip(),
            "xt_quant_acct": (sys.argv[2].strip() if len(sys.argv) > 2 else None) or "39271919",
        }
    else:
        cli_cfg = {
            "xt_quant_path": r"C:\国金证券QMT交易端\userdata_mini",
            "xt_quant_acct": "39271919",
        }
    ok, msg = QMTAdapter(cli_cfg).test_connection()
    print("连通性测试:", "通过" if ok else "失败", "-", msg)
    sys.exit(0 if ok else 1)
