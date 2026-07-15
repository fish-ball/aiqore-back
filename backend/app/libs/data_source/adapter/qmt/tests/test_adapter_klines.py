# -*- coding: utf-8 -*-
"""K 线 get_klines_data。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTKlines(unittest.TestCase):
    """get_klines_data 多种 xt 返回形态。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_klines_data_symbol_df(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "time": 1000,
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 1,
                    "amount": 0.0,
                    "settle": 0.0,
                    "openInterest": 0,
                    "preClose": 0.0,
                    "suspendFlag": 0,
                }
            ]
        )
        xt = MagicMock()
        xt.get_market_data.return_value = {"000001.SZ": df}
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            rows = adapter.get_klines_data("000001.SZ", period="1d", count=10)
        self.assertIsNotNone(rows)
        assert rows is not None
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].close, 1.0)

    def test_get_klines_data_exception_returns_none(self) -> None:
        xt = MagicMock()
        xt.get_market_data.side_effect = RuntimeError("boom")
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIsNone(adapter.get_klines_data("000001.SZ"))

    def test_get_klines_data_multi_field_dict(self) -> None:
        idx = pd.Index(["000001.SZ"])
        time_df = pd.DataFrame({"t0": [1700000000000]}, index=idx)
        open_df = pd.DataFrame({"t0": [10.0]}, index=idx)
        close_df = pd.DataFrame({"t0": [11.0]}, index=idx)
        vol_df = pd.DataFrame({"t0": [100]}, index=idx)
        amt_df = pd.DataFrame({"t0": [1000.0]}, index=idx)
        data = {
            "time": time_df,
            "open": open_df,
            "high": open_df,
            "low": open_df,
            "close": close_df,
            "volume": vol_df,
            "amount": amt_df,
            "settle": close_df * 0,
            "openInterest": vol_df * 0,
            "preClose": close_df,
            "suspendFlag": vol_df * 0,
        }
        xt = MagicMock()
        xt.get_market_data.return_value = data
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            rows = adapter.get_klines_data("000001.SZ")
        self.assertIsNotNone(rows)
        assert rows is not None
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].close, 11.0)


if __name__ == "__main__":
    unittest.main()
