# -*- coding: utf-8 -*-
"""
QMT 适配器单元测试：纯函数与 QMTDataSourceAdapter 行为，xtquant 通过 mock 隔离。
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter
from app.libs.data_source.adapter.qmt.convert import rows_from_symbol_df, xt_row_to_kline
from app.libs.data_source.adapter.qmt.mappings import normalize_period_to_xt, to_xtdata_time
from app.libs.data_source.models import InstrumentBrief

# _load_xtdata 在适配器内加载 xtquant，测试中 patch 此处
_PATCH_LOAD_XT = "app.libs.data_source.adapter.qmt.adapter.QMTDataSourceAdapter._load_xtdata"


def reset_qmt_singleton() -> None:
    """重置 QMT 单例及本实例插入的 sys.path，避免用例互相污染。"""
    QMTDataSourceAdapter.reset_singleton_for_tests()


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


class TestQMTXtdataLoad(unittest.TestCase):
    """_load_xtdata 返回 None 时适配器不持有 xtdata。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_xtdata_none_when_load_returns_none(self, _mock) -> None:
        reset_qmt_singleton()
        a = QMTDataSourceAdapter({})
        self.assertIsNone(a.xtdata)


class TestQMTDataSourceAdapter(unittest.TestCase):
    """QMTDataSourceAdapter：config + _load_xtdata（测试中 patch 为 mock xtdata）。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_require_xtdata_raises_when_none(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        with self.assertRaises(RuntimeError) as ctx:
            adapter._require_xtdata()
        self.assertIn("xtquant", str(ctx.exception))

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_test_connection_fails_when_xtdata_unavailable(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        ok, msg = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("xtquant", msg)

    def test_test_connection_success(self) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["沪深A股"]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            ok, msg = adapter.test_connection()
        self.assertTrue(ok)
        self.assertEqual(msg, "连接成功")

    def test_get_stock_list_in_sector(self) -> None:
        xt = MagicMock()
        xt.get_stock_list_in_sector.return_value = ["600000.SH", "000001.SZ"]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            res = adapter.get_stock_list_in_sector("沪深A股", market="SH")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].symbol, "600000.SH")

    @patch.object(QMTDataSourceAdapter, "get_stock_list_in_sector")
    def test_get_stock_list_delegates_sector(self, mock_sector) -> None:
        mock_sector.return_value = [InstrumentBrief(symbol="x", market="SH", sector="s")]
        xt = MagicMock()
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_stock_list(sector="沪深A股")
        mock_sector.assert_called_once_with("沪深A股", None)
        self.assertEqual(len(out), 1)

    def test_get_instrument_detail(self) -> None:
        xt = MagicMock()
        xt.get_instrument_detail.return_value = {"InstrumentName": "测试"}
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertEqual(adapter.get_instrument_detail("600000.SH"), {"InstrumentName": "测试"})

    def test_get_sector_list_from_xtdata_flat(self) -> None:
        from app.libs.data_source.models import AssetClass

        xt = MagicMock()
        xt.get_sector_list.return_value = ["A", "B"]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter._get_sector_list_from_xtdata()
        self.assertEqual([x.alias for x in out], ["A", "B"])
        self.assertTrue(all(x.asset_class == AssetClass.EQUITY for x in out))

    def test_get_sector_list_from_xtdata_empty_when_xt_returns_empty(self) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = []
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertEqual(adapter._get_sector_list_from_xtdata(), [])

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

    def test_get_ticks_data_invalid_date(self) -> None:
        xt = MagicMock()
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIsNone(adapter.get_ticks_data("000001.SZ", "2024-1"))
        xt.download_history_data.assert_not_called()

    def test_get_ticks_data_returns_dataframe(self) -> None:
        xt = MagicMock()
        df = pd.DataFrame({"a": [1]})
        xt.get_market_data_ex.return_value = {"000001.SZ": df}
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_ticks_data("000001.SZ", "2024-01-15")
        self.assertTrue(isinstance(out, pd.DataFrame))

    def test_get_divid_factors_none_when_unsupported(self) -> None:
        xt = MagicMock(spec=[])
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIsNone(adapter.get_divid_factors("000001.SZ"))

    def test_get_divid_factors_returns_df(self) -> None:
        xt = MagicMock()
        df = pd.DataFrame({"x": [1]})
        xt.get_divid_factors.return_value = df
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIs(adapter.get_divid_factors("000001.SZ", start_time="2024-01-01"), df)

    def test_get_realtime_quote(self) -> None:
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
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_realtime_quote(["000001.SZ"])
        self.assertIsNotNone(out)
        assert out is not None
        q = out["000001.SZ"]
        self.assertEqual(q.name, "平安")
        self.assertEqual(q.last_price, 10.0)

    @patch.object(QMTDataSourceAdapter, "get_stock_list")
    def test_search_stocks(self, mock_list) -> None:
        xt = MagicMock(get_instrument_detail=MagicMock(return_value=None))
        mock_list.return_value = [
            InstrumentBrief(symbol="600000.SH", market="SH", sector="x"),
            InstrumentBrief(symbol="000001.SZ", market="SZ", sector="y"),
        ]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            res = adapter.search_stocks("600")
        self.assertTrue(any(r.symbol == "600000.SH" for r in res))

    def test_get_realtime_quote_exception_returns_none(self) -> None:
        xt = MagicMock()
        xt.get_full_tick.side_effect = RuntimeError("net")
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIsNone(adapter.get_realtime_quote(["000001.SZ"]))

    @patch.object(QMTDataSourceAdapter, "_preset_sector_aliases_dfs")
    def test_get_stock_list_aggregates_sectors(self, mock_aliases) -> None:
        mock_aliases.return_value = ["板块一"]
        xt = MagicMock()
        xt.get_stock_list_in_sector.return_value = ["600000.SH"]
        xt.get_instrument_list.return_value = []
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_stock_list()
        self.assertTrue(any(x.symbol == "600000.SH" for x in out))


class TestGetAdapterQMT(unittest.TestCase):
    """get_adapter('qmt', config) 与 QMTDataSourceAdapter 单例一致。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_adapter_qmt_uses_load_xtdata(self) -> None:
        reset_qmt_singleton()
        with patch(_PATCH_LOAD_XT) as mock_load:
            xt = MagicMock()
            mock_load.return_value = xt
            impl = get_adapter("qmt", {})
            self.assertIsInstance(impl, QMTDataSourceAdapter)
            self.assertIs(impl.xtdata, xt)
            mock_load.assert_called_once()
            self.assertIs(get_adapter("qmt", {}), impl)


if __name__ == "__main__":
    unittest.main()
