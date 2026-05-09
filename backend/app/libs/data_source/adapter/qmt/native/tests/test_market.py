# -*- coding: utf-8 -*-
"""
xtdata.get_market_data_ex 冒烟：经 ``adapt_xt_get_market_data_ex_kline`` 转为 KlineBar。

需本机已启动 miniQMT。无法加载 xtdata 时用例 skip（非失败）。

  cd backend
  python -m unittest app.libs.data_source.adapter.qmt.native.tests.test_market -v
"""
from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.adapter import QMTDataSourceAdapter
from app.libs.data_source.adapter.qmt.convert import adapt_xt_get_market_data_ex_kline
from app.libs.data_source.adapter.qmt.native.tests.xt_test_env import (
    SAMPLE_MARKET_SYMBOLS,
    try_load_xtdata,
)


class TestGetMarketDataEx(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        xt, err = try_load_xtdata()
        if xt is None:
            raise unittest.SkipTest(err)
        cls._xt = xt

    @classmethod
    def tearDownClass(cls) -> None:
        QMTDataSourceAdapter.reset_singleton_for_tests()

    def test_daily_count1_adapts_to_kline_batch(self) -> None:
        """日线 count=1：适配为按合约分组的 KlineBar 列表，每标至少一根。"""
        for symbol, mkt in SAMPLE_MARKET_SYMBOLS:
            with self.subTest(market=mkt, symbol=symbol):
                raw = self._xt.get_market_data_ex(
                    field_list=[],
                    stock_list=[symbol],
                    period="1d",
                    start_time="",
                    end_time="",
                    count=1,
                    dividend_type="none",
                    fill_data=True,
                )
                batch = adapt_xt_get_market_data_ex_kline(
                    raw, expected_symbols=[symbol]
                )
                self.assertIn(symbol, batch)
                bars = batch[symbol]
                self.assertGreaterEqual(len(bars), 1)
                self.assertGreater(bars[0].time, 0)

    def test_partial_field_list_yields_empty_bars_without_time(self) -> None:
        """仅 open/close 列且无 time 时无法构成 KlineBar，对应空列表。"""
        raw = self._xt.get_market_data_ex(
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
        self.assertEqual(batch.get("000001.SZ"), [])


if __name__ == "__main__":
    unittest.main()
