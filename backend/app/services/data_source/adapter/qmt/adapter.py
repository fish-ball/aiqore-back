# -*- coding: utf-8 -*-
"""QMTAdapter：组合股票/期货/期权实现与 xtdata 通用能力。"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.data_source.adapter.base import SecuritiesDataSourceAdapter
from app.services.data_source.adapter.qmt.core import ensure_xtdata
from app.services.data_source.adapter.qmt.native.maintain import download_history_data
from app.services.data_source.adapter.qmt.futures_impl import QMTFuturesMixin
from app.services.data_source.adapter.qmt.options_impl import QMTOptionMixin
from app.services.data_source.adapter.qmt.stock_impl import QMTStockLikeMixin
from app.services.data_source.adapter.qmt.symbol_kind import infer_market_layer
from app.services.data_source.adapter.qmt.mappings import to_xtdata_time
from app.services.data_source.models.enums import MarketLayer
from app.services.data_source.models.kline import KlineBar
from app.services.data_source.models.quote import RealtimeQuote

logger = logging.getLogger(__name__)


class QMTAdapter(
    QMTStockLikeMixin,
    QMTFuturesMixin,
    QMTOptionMixin,
    SecuritiesDataSourceAdapter,
):
    """QMT 适配器：直接调用 xtquant.xtdata 实现行情与证券列表。"""

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
        """K 线数据，按证券类型分派到对应实现。"""
        kind = infer_market_layer(symbol)
        if kind == MarketLayer.Future:
            return self._get_klines_futures(symbol, period, count, start_time, end_time)
        if kind == MarketLayer.Option:
            return self._get_klines_option(symbol, period, count, start_time, end_time)
        return self._get_klines_stock_like(symbol, period, count, start_time, end_time)

    def get_ticks_data(self, symbol: str, trade_date: str) -> Optional[Any]:
        """
        按交易日拉取分笔数据。使用 get_market_data_ex(period='tick', dividend_type='none', fill_data=False)，
        不传 count，仅返回历史行情。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        返回 pandas DataFrame，列见 data_schema.TICK_DF_*；否则返回 None。
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


# 兼容旧版 __main__：python -m app.services.data_source.adapter.qmt
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
