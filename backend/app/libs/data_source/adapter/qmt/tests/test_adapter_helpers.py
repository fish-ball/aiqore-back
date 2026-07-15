# -*- coding: utf-8 -*-
"""纯函数：mappings 与 convert。"""
from __future__ import annotations

import unittest

import pandas as pd

from app.libs.data_source.adapter.qmt.convert import rows_from_symbol_df, xt_row_to_kline
from app.libs.data_source.adapter.qmt.mappings import normalize_period_to_xt, to_xtdata_time


class TestPureHelpers(unittest.TestCase):
    """to_xtdata_time / normalize_period_to_xt 与 convert 纯函数。"""

    def test_to_xtdata_time_none_and_empty(self) -> None:
        self.assertIsNone(to_xtdata_time(None))
        self.assertEqual(to_xtdata_time(""), "")

    def test_to_xtdata_time_digits(self) -> None:
        self.assertEqual(to_xtdata_time("2024-01-15"), "20240115")
        self.assertEqual(to_xtdata_time("2024-01-15 09:30:00"), "20240115093000")

    def test_normalize_period_to_xt(self) -> None:
        self.assertEqual(normalize_period_to_xt("1M"), "1mon")
        self.assertEqual(normalize_period_to_xt("1d"), "1d")

    def test_xt_row_to_kline(self) -> None:
        row = {
            "time": 1700000000000,
            "open": 1.0,
            "high": 2.0,
            "low": 0.5,
            "close": 1.5,
            "volume": 100,
            "amount": 1000.0,
            "settle": 0.0,
            "openInterest": 0,
            "preClose": 1.0,
            "suspendFlag": 0,
        }
        out = xt_row_to_kline(row)
        self.assertEqual(out.time, 1700000000000)
        self.assertEqual(out.volume, 100)
        self.assertEqual(out.close, 1.5)

    def test_rows_from_symbol_df(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "time": 1,
                    "open": 1.0,
                    "high": 2.0,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 10,
                    "amount": 100.0,
                    "settle": 0.0,
                    "openInterest": 0,
                    "preClose": 1.0,
                    "suspendFlag": 0,
                }
            ]
        )
        rows = rows_from_symbol_df(df)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].close, 1.5)


if __name__ == "__main__":
    unittest.main()
