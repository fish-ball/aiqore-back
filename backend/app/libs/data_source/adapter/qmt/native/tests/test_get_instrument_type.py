# -*- coding: utf-8 -*-
"""get_instrument_type 单元测试；依赖本机 xtquant/miniQMT。

返回值以本机 xtdata.get_instrument_type 为准；权益类多为小写字符串标签，期货/期权在当前环境下常为 None（若升级后变化需同步改断言）。
"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_instrument_type import get_instrument_type


class TestGetInstrumentType(unittest.TestCase):
    """按品种断言 get_instrument_type 的返回值。"""

    def test_stock_returns_stock(self) -> None:
        """A 股股票返回 \"stock\"。

        数据实例：600519.SH、000001.SZ -> 'stock'
        """
        for sym in ("600519.SH", "000001.SZ"):
            with self.subTest(symbol=sym):
                self.assertEqual(get_instrument_type(sym), "stock")

    def test_index_returns_index(self) -> None:
        """指数返回 \"index\"。

        数据实例：000300.SH -> 'index'
        """
        self.assertEqual(get_instrument_type("000300.SH"), "index")

    def test_fund_returns_fund(self) -> None:
        """场外/场内基金类返回 \"fund\"（与 ETF 区分）。

        数据实例：161725.SZ（LOF）-> 'fund'
        """
        self.assertEqual(get_instrument_type("161725.SZ"), "fund")

    def test_etf_returns_etf(self) -> None:
        """ETF 返回 \"etf\"（与 LOF 等 fund 区分）。

        数据实例：510300.SH、588000.SH -> 'etf'
        """
        for sym in ("510300.SH", "588000.SH"):
            with self.subTest(symbol=sym):
                self.assertEqual(get_instrument_type(sym), "etf")

    def test_future_returns_none_in_current_qmt(self) -> None:
        """商品/股指期货合约：当前 miniQMT 对 get_instrument_type 返回 None。

        数据实例：rb2605.SF、PK612.ZF、IC2612.IF -> None（若日后返回 str 需改本用例）
        """
        for sym in ("rb2605.SF", "PK612.ZF", "IC2612.IF"):
            with self.subTest(symbol=sym):
                self.assertIsNone(get_instrument_type(sym))

    def test_commodity_option_returns_none_in_current_qmt(self) -> None:
        """商品期货期权：当前环境返回 None。

        数据实例：ag2612P11700.SF -> None
        """
        self.assertIsNone(get_instrument_type("ag2612P11700.SF"))

    def test_cffex_index_option_returns_none_in_current_qmt(self) -> None:
        """中金所股指期权：当前环境返回 None。

        数据实例：IO2605-P-5000.IF -> None
        """
        self.assertIsNone(get_instrument_type("IO2605-P-5000.IF"))

    def test_etf_option_returns_none_in_current_qmt(self) -> None:
        """上交所 ETF 期权：当前环境返回 None。

        数据实例：10011096.SHO -> None
        """
        self.assertIsNone(get_instrument_type("10011096.SHO"))

    def test_invalid_symbol_returns_none(self) -> None:
        """无效代码返回 None 且不抛异常。

        数据实例：__bad__.SH -> None
        """
        self.assertIsNone(get_instrument_type("__bad__.SH"))

    def test_sample_symbols_return_str_or_none(self) -> None:
        """抽样：类型推断结果为 str 或 None，不抛异常（与细分用例互补）。"""
        for sym in (
            "600519.SH",
            "000001.SZ",
            "000300.SH",
            "161725.SZ",
            "510300.SH",
            "rb2605.SF",
            "IO2605-P-5000.IF",
            "__bad__.SH",
        ):
            with self.subTest(symbol=sym):
                t = get_instrument_type(sym)
                self.assertTrue(t is None or isinstance(t, str))


if __name__ == "__main__":
    unittest.main()
