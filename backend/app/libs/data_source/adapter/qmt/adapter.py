# -*- coding: utf-8 -*-
"""QMTDataSourceAdapter：进程内单例，绑定 xtdata，提供证券列表、K 线、分笔、实时行情等。"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

import pandas as pd

from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.adapter.qmt import native
from app.libs.data_source.adapter.qmt.convert import qmt_detail_dict_to_instrument
from app.libs.data_source.adapter.qmt.kline_fetch import fetch_klines
from app.libs.data_source.adapter.qmt.mappings import to_xtdata_time
from app.libs.data_source.adapter.qmt.preset_data import PRESET_SECTOR_ROOTS
from app.libs.data_source.models import AssetClass, DataSourceSector, InstrumentType
from app.libs.data_source.models.instrument import DataSourceInstrument, InstrumentBrief
from app.libs.data_source.models.kline import KlineBar
from app.libs.data_source.models.quote import RealtimeQuote

logger = logging.getLogger(__name__)


class QMTDataSourceAdapter(DataSourceAdapter):
    """
    QMT 行情适配器（进程内单例）。
    使用 xtquant.xtdata；需本机已启动 miniQMT 且 Python 可导入 xtquant。config 仅作占位或与交易侧字段并存。
    """

    _singleton_instance: ClassVar[Optional["QMTDataSourceAdapter"]] = None

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
    def _preset_sector_aliases_dfs(nodes: List[DataSourceSector]) -> List[str]:
        """深度优先收集 alias，与 preset 树结构一致，供 get_instrument_list 扫描 QMT 板块键。"""
        out: List[str] = []
        for n in nodes:
            if n.alias:
                out.append(n.alias)
            out.extend(QMTDataSourceAdapter._preset_sector_aliases_dfs(n.children))
        return out

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

    def __new__(cls, config: Optional[Dict[str, Any]] = None) -> QMTDataSourceAdapter:
        if cls._singleton_instance is None:
            cls._singleton_instance = super().__new__(cls)
        return cls._singleton_instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = dict(config or {})
        if getattr(self, "xtdata", None) is None:
            self.xtdata = self._load_xtdata()

    def _unload_xtdata_env(self) -> None:
        """单测隔离：清空本实例持有的 xtdata 引用（不卸载已导入的 xtquant 模块）。"""
        self.xtdata = None

    def _load_xtdata(self) -> Optional[Any]:
        """导入 xtquant.xtdata；需本机环境已安装 xtquant 且 miniQMT 已启动方可正常取数。"""
        try:
            from xtquant import xtdata as _xt

            return _xt
        except ImportError as e:
            logger.warning("xtquant 未安装或不可用: %s", e)
            return None

    @classmethod
    def reset_singleton_for_tests(cls) -> None:
        """单测隔离：清空单例引用与 xtdata 句柄。"""
        inst = cls._singleton_instance
        if inst is not None:
            inst._unload_xtdata_env()
        cls._singleton_instance = None

    def _require_xtdata(self) -> Any:
        """业务调用前确保 xtdata 可用。"""
        if self.xtdata is None:
            raise RuntimeError("xtquant 未安装或不可用，请启动 miniQMT 并确保当前 Python 环境可 import xtquant")
        return self.xtdata

    def test_connection(self) -> tuple[bool, str]:
        if self.xtdata is None:
            return False, "xtquant 未安装或不可用，请启动 miniQMT 并确保可导入 xtquant"
        try:
            self.xtdata.get_sector_list()
            return True, "连接成功"
        except Exception as e:
            logger.exception("QMT 连接测试异常")
            return False, str(e)

    def get_instrument_detail(
        self,
        symbol: str,
        *,
        iscomplete: bool = False,
    ) -> Optional[DataSourceInstrument]:
        """经 qmt.native.get_instrument_detail 拉取详情，不直接调用 xtdata。"""
        xt = self._require_xtdata()
        raw = native.get_instrument_detail(symbol, iscomplete=iscomplete, xtdata=xt)
        if raw is None:
            return None
        return qmt_detail_dict_to_instrument(raw, symbol, xtdata=xt)

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
            self._require_xtdata(), symbol, period, count, start_time, end_time
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
        xtdata = self._require_xtdata()
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
        xtdata = self._require_xtdata()
        st = to_xtdata_time(start_time) if start_time else ""
        et = to_xtdata_time(end_time) if end_time else ""
        try:
            return xtdata.get_divid_factors(symbol, start_time=st or "", end_time=et or "")
        except Exception as e:
            logger.error("获取除权数据失败 %s: %s", symbol, e)
            return None

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, RealtimeQuote]]:
        xtdata = self._require_xtdata()
        try:
            quotes = xtdata.get_full_tick(symbols)
            names: Dict[str, str] = {}
            for symbol in symbols:
                raw_detail = native.get_instrument_detail(
                    symbol, iscomplete=False, xtdata=xtdata
                )
                if isinstance(raw_detail, dict):
                    v = raw_detail.get("InstrumentName")
                    if v is not None:
                        nm = str(v).strip()
                        if nm:
                            names[symbol] = nm
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

    def get_instrument_list(
        self,
        market: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[InstrumentBrief]:
        if sector:
            return self.get_stock_list_in_sector(sector, market)
        xtdata = self._require_xtdata()
        all_securities: List[InstrumentBrief] = []
        seen_symbols: set[str] = set()
        for sec_name in QMTDataSourceAdapter._preset_sector_aliases_dfs(PRESET_SECTOR_ROOTS):
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
        xtdata = self._require_xtdata()
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
        """板块树：直接使用 preset_data 模块导出的成品列表。"""
        return PRESET_SECTOR_ROOTS

    def _get_sector_list_from_xtdata(self) -> List[DataSourceSector]:
        """
        从 xtdata.get_sector_list 拉取并剔除申万/证监会多级键（SW1、SW2、SW3、CSRC1、CSRC2 前缀）。
        保留备用于导出预设或与 JSON 对照，默认业务路径不走此接口。
        """
        xtdata = self._require_xtdata()
        names = self._sector_keys_filtered(xtdata.get_sector_list())
        return [
            DataSourceSector(
                name=n,
                alias=n,
                asset_class=AssetClass.EQUITY,
                instrument_type=InstrumentType.STOCK,
                children=[],
            )
            for n in names
        ]


if __name__ == "__main__":
    # 命令行自检：python -m app.libs.data_source.adapter.qmt.adapter（需已启动 miniQMT）
    from app.libs.data_source.adapter import get_adapter

    ok, msg = get_adapter("qmt", {}).test_connection()
    print("连通性测试:", "通过" if ok else "失败", "-", msg)
    sys.exit(0 if ok else 1)
