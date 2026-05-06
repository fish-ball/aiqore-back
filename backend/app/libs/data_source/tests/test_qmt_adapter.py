# -*- coding: utf-8 -*-
"""
QMT 适配器单元测试：纯函数与 QMTAdapter 行为，xtquant 通过 mock 隔离。
"""
from __future__ import annotations

import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.libs.data_source.adapter.qmt import QMTAdapter
from app.libs.data_source.adapter.qmt.convert import rows_from_symbol_df, xt_row_to_kline
from app.libs.data_source.adapter.qmt.core import ensure_xtdata, reset_xtdata_cache
from app.libs.data_source.adapter.qmt.mappings import normalize_period_to_xt, to_xtdata_time
from app.libs.data_source.models import InstrumentBrief


def reset_qmt_globals() -> None:
    """重置 xtdata 进程级缓存，避免用例互相污染。"""
    reset_xtdata_cache()


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


class TestEnsureXtdata(unittest.TestCase):
    """ensure_xtdata：无有效路径时不加载。"""

    def tearDown(self) -> None:
        reset_qmt_globals()

    def test_ensure_xtdata_no_path_returns_none(self) -> None:
        reset_qmt_globals()
        self.assertIsNone(ensure_xtdata(None))
        self.assertIsNone(ensure_xtdata(""))


class TestQMTAdapter(unittest.TestCase):
    """QMTAdapter 方法，默认 patch 掉外部依赖。"""

    def tearDown(self) -> None:
        reset_qmt_globals()

    def test_get_xtdata_raises_when_no_xtquant(self) -> None:
        reset_qmt_globals()
        adapter = QMTAdapter({"xt_quant_path": None})
        with patch("app.libs.data_source.adapter.qmt.adapter.ensure_xtdata", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                adapter._get_xtdata()
            self.assertIn("xtquant", str(ctx.exception))

    def test_test_connection_bad_path(self) -> None:
        adapter = QMTAdapter({"xt_quant_path": "/nonexistent/path/xxx"})
        ok, msg = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("路径", msg)

    def test_test_connection_acct_folder_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = QMTAdapter({"xt_quant_path": tmp, "xt_quant_acct": "99999999"})
            ok, msg = adapter.test_connection()
            self.assertFalse(ok)
            self.assertIn("不存在", msg)

    @patch("app.libs.data_source.adapter.qmt.adapter.ensure_xtdata")
    def test_test_connection_success(self, mock_ensure) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["沪深A股"]
        mock_ensure.return_value = xt
        with tempfile.TemporaryDirectory() as tmp:
            adapter = QMTAdapter({"xt_quant_path": tmp})
            ok, msg = adapter.test_connection()
        self.assertTrue(ok)
        self.assertEqual(msg, "连接成功")

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_stock_list_in_sector(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_stock_list_in_sector.return_value = ["600000.SH", "000001.SZ"]
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        res = adapter.get_stock_list_in_sector("沪深A股", market="SH")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].symbol, "600000.SH")

    @patch.object(QMTAdapter, "get_stock_list_in_sector")
    def test_get_stock_list_delegates_sector(self, mock_sector) -> None:
        mock_sector.return_value = [InstrumentBrief(symbol="x", market="SH", sector="s")]
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_stock_list(sector="沪深A股")
        mock_sector.assert_called_once_with("沪深A股", None)
        self.assertEqual(len(out), 1)

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_instrument_detail(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_instrument_detail.return_value = {"InstrumentName": "测试"}
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertEqual(adapter.get_instrument_detail("600000.SH"), {"InstrumentName": "测试"})

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_sector_list_from_xt(self, mock_gx) -> None:
        from app.libs.data_source.models import MarketLayer

        xt = MagicMock()
        xt.get_sector_list.return_value = ["A", "B"]
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_sector_list()
        self.assertEqual([x.alias for x in out], ["A", "B"])
        self.assertTrue(all(x.asset_class == MarketLayer.Equity for x in out))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_sector_list_fallback_default(self, mock_gx) -> None:
        xt = MagicMock(spec=[])  # 无 get_sector_list
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_sector_list()
        aliases = [x.alias for x in out]
        self.assertIn("沪深A股", aliases)

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_klines_data_symbol_df(self, mock_gx) -> None:
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
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        rows = adapter.get_klines_data("000001.SZ", period="1d", count=10)
        self.assertIsNotNone(rows)
        assert rows is not None
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].close, 1.0)

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_klines_data_exception_returns_none(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_market_data.side_effect = RuntimeError("boom")
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertIsNone(adapter.get_klines_data("000001.SZ"))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_klines_data_multi_field_dict(self, mock_gx) -> None:
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
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        rows = adapter.get_klines_data("000001.SZ")
        self.assertIsNotNone(rows)
        assert rows is not None
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].close, 11.0)

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_ticks_data_invalid_date(self, mock_gx) -> None:
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertIsNone(adapter.get_ticks_data("000001.SZ", "2024-1"))
        mock_gx.assert_not_called()

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_ticks_data_returns_dataframe(self, mock_gx) -> None:
        xt = MagicMock()
        df = pd.DataFrame({"a": [1]})
        xt.get_market_data_ex.return_value = {"000001.SZ": df}
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_ticks_data("000001.SZ", "2024-01-15")
        self.assertTrue(isinstance(out, pd.DataFrame))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_divid_factors_none_when_unsupported(self, mock_gx) -> None:
        xt = MagicMock(spec=[])
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertIsNone(adapter.get_divid_factors("000001.SZ"))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_divid_factors_returns_df(self, mock_gx) -> None:
        xt = MagicMock()
        df = pd.DataFrame({"x": [1]})
        xt.get_divid_factors.return_value = df
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertIs(adapter.get_divid_factors("000001.SZ", start_time="2024-01-01"), df)

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_realtime_quote(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_full_tick.return_value = {
            "000001.SZ": {
                "lastPrice": 10.0,
                "open": 9.0,
                "high": 11.0,
                "low": 8.0,
                "lastClose": 9.5,
                "volume": 1000,
                "amount": 10000.0,
            }
        }
        xt.get_instrument_detail.return_value = {"InstrumentName": "平安"}
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_realtime_quote(["000001.SZ"])
        self.assertIsNotNone(out)
        assert out is not None
        q = out["000001.SZ"]
        self.assertEqual(q.name, "平安")
        self.assertEqual(q.last_price, 10.0)

    @patch.object(QMTAdapter, "get_stock_list")
    @patch.object(QMTAdapter, "_get_xtdata")
    def test_search_stocks(self, mock_gx, mock_list) -> None:
        mock_gx.return_value = MagicMock(get_instrument_detail=MagicMock(return_value=None))
        mock_list.return_value = [
            InstrumentBrief(symbol="600000.SH", market="SH", sector="x"),
            InstrumentBrief(symbol="000001.SZ", market="SZ", sector="y"),
        ]
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        res = adapter.search_stocks("600")
        self.assertTrue(any(r.symbol == "600000.SH" for r in res))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_realtime_quote_exception_returns_none(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_full_tick.side_effect = RuntimeError("net")
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertIsNone(adapter.get_realtime_quote(["000001.SZ"]))

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_stock_list_aggregates_sectors(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["板块一"]
        xt.get_stock_list_in_sector.return_value = ["600000.SH"]
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_stock_list()
        self.assertTrue(any(x.symbol == "600000.SH" for x in out))


if __name__ == "__main__":
    unittest.main()
