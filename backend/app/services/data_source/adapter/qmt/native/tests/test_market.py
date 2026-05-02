# -*- coding: utf-8 -*-
"""
native.market.get_market_data_ex：真实 xtdata 冒烟。

通过 ``adapt_xt_get_market_data_ex_kline`` 转为 ``KlineBatchBySymbol``（data_source 统一模型）。

XT_QUANT_PATH 优先环境变量，否则 app.config。无法加载 xtdata 时用例 skip（非失败）。

  cd backend
  python -m unittest app.services.data_source.adapter.qmt.native.tests.test_market -v
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import Any, Optional, Tuple

from app.services.data_source.adapter.qmt.core import ensure_xtdata, reset_xtdata_cache
from app.services.data_source.adapter.qmt.market_data_ex_adapt import (
    adapt_xt_get_market_data_ex_kline,
)
from app.services.data_source.adapter.qmt.native.market import get_market_data_ex

# 上证 / 深证 / 北交所示例代码
_MARKET_SYMBOLS = (
    ("600000.SH", "SH"),
    ("000001.SZ", "SZ"),
    ("830799.BJ", "BJ"),
)


def _xt_path() -> Optional[str]:
    p = os.environ.get("XT_QUANT_PATH", "").strip()
    if p:
        return p
    try:
        from app.config import settings

        return (getattr(settings, "XT_QUANT_PATH", None) or "").strip() or None
    except Exception:
        return None


def _try_xtdata() -> Tuple[Optional[Any], str]:
    path = _xt_path()
    if not path:
        return None, "无 XT_QUANT_PATH（环境变量或 app.config）"
    if not Path(path).is_dir():
        return None, f"路径无效: {path}"
    reset_xtdata_cache()
    xt = ensure_xtdata(path)
    if xt is None:
        return None, "ensure_xtdata 失败（xtquant / miniQMT）"
    return xt, ""


class TestGetMarketDataEx(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        xt, err = _try_xtdata()
        if xt is None:
            raise unittest.SkipTest(err)
        cls._xt = xt

    @classmethod
    def tearDownClass(cls) -> None:
        reset_xtdata_cache()

    def test_daily_count1_adapts_to_kline_batch(self) -> None:
        """日线 count=1：适配为 KlineBatchBySymbol，每标至少一根 KlineBar。"""
        for symbol, mkt in _MARKET_SYMBOLS:
            with self.subTest(market=mkt, symbol=symbol):
                raw = get_market_data_ex(
                    self._xt,
                    stock_list=[symbol],
                    period="1d",
                    count=1,
                )
                batch = adapt_xt_get_market_data_ex_kline(
                    raw, expected_symbols=[symbol]
                )
                self.assertIn(symbol, batch.bars_by_symbol)
                bars = batch.bars_by_symbol[symbol]
                self.assertGreaterEqual(len(bars), 1)
                self.assertGreater(bars[0].time, 0)

    def test_partial_field_list_yields_empty_bars_without_time(self) -> None:
        """仅 open/close 列且无 time 时无法构成 KlineBar，对应空列表。"""
        raw = get_market_data_ex(
            self._xt,
            field_list=["close", "open"],
            stock_list=["000001.SZ"],
            period="15m",
            start_time="20230901",
            end_time="20230905",
            count=-1,
            dividend_type="none",
            fill_data=True,
        )
        batch = adapt_xt_get_market_data_ex_kline(
            raw, expected_symbols=["000001.SZ"]
        )
        self.assertEqual(batch.bars_by_symbol.get("000001.SZ"), [])


if __name__ == "__main__":
    unittest.main()
