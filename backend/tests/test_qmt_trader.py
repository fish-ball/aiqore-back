# -*- coding: utf-8 -*-
"""app.libs.trader.qmt_trader 单元测试。"""
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.libs.trader.qmt_trader import QMTTrader


def reset_trader_type_cache() -> None:
    """重置 xttrader 类型缓存，避免用例互相影响。"""
    import app.libs.trader.qmt_trader as m

    m._xttrader_cls = None
    m._stock_account_cls = None


class TestQMTTrader(unittest.TestCase):
    def tearDown(self) -> None:
        reset_trader_type_cache()

    @patch.object(QMTTrader, "_get_xttrader")
    @patch("app.libs.trader.qmt_trader._ensure_xttrader_types")
    def test_get_account_info(self, mock_types, mock_get_xt) -> None:
        mock_types.return_value = (MagicMock, MagicMock)
        xt = MagicMock()
        asset = MagicMock()
        asset.cash = 50000.0
        asset.frozen_cash = 100.0
        asset.market_value = 40000.0
        asset.total_asset = 90000.0
        xt.query_stock_asset.return_value = asset
        mock_get_xt.return_value = xt
        t = QMTTrader({"xt_quant_path": "/tmp"})
        info = t.get_account_info("123456")
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info["account_id"], "123456")
        self.assertEqual(info["total_asset"], 90000.0)
        self.assertEqual(info["available"], 50000.0)

    @patch.object(QMTTrader, "_get_xttrader")
    @patch("app.libs.trader.qmt_trader._ensure_xttrader_types")
    def test_get_account_info_no_asset(self, mock_types, mock_get_xt) -> None:
        mock_types.return_value = (MagicMock, MagicMock)
        xt = MagicMock()
        xt.query_stock_asset.return_value = None
        mock_get_xt.return_value = xt
        t = QMTTrader({"xt_quant_path": "/tmp"})
        self.assertIsNone(t.get_account_info("123456"))

    @patch.object(QMTTrader, "_get_xttrader")
    @patch("app.libs.trader.qmt_trader._ensure_xttrader_types")
    def test_get_positions(self, mock_types, mock_get_xt) -> None:
        mock_types.return_value = (MagicMock, MagicMock)
        pos = MagicMock()
        pos.stock_code = "000001.SZ"
        pos.volume = 100
        pos.can_use_volume = 100
        pos.open_price = 10.0
        pos.market_value = 1000.0
        pos.frozen_volume = 0
        pos.on_road_volume = 0
        pos.yesterday_volume = 0
        pos.avg_price = 10.0
        pos.last_price = 10.0
        pos.profit_rate = 0.0
        pos.secu_account = ""
        pos.instrument_name = "测试"
        xt = MagicMock()
        xt.query_stock_positions.return_value = [pos]
        mock_get_xt.return_value = xt
        t = QMTTrader({"xt_quant_path": "/tmp"})
        rows = t.get_positions("123456")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "000001.SZ")


class TestGetXttraderSession(unittest.TestCase):
    """_get_xttrader 会话 id 与复用。"""

    def tearDown(self) -> None:
        reset_trader_type_cache()

    @patch("app.libs.trader.qmt_trader._ensure_xttrader_types")
    def test_session_id_explicit(self, mock_types) -> None:
        XtClass = MagicMock()
        mock_types.return_value = (XtClass, MagicMock)
        with tempfile.TemporaryDirectory() as tmp:
            t = QMTTrader({"xt_quant_path": tmp})
            inst = MagicMock()
            inst.connect.return_value = 0
            XtClass.return_value = inst
            r1 = t._get_xttrader(session_id=42)
            r2 = t._get_xttrader(session_id=999)
            self.assertIs(r1, r2)
            XtClass.assert_called_once_with(tmp, 42)

    @patch("app.libs.trader.qmt_trader._ensure_xttrader_types")
    @patch("app.libs.trader.qmt_trader.time.time", return_value=1234567890)
    def test_session_id_default_uses_time(self, _mock_time, mock_types) -> None:
        XtClass = MagicMock()
        mock_types.return_value = (XtClass, MagicMock)
        with tempfile.TemporaryDirectory() as tmp:
            t = QMTTrader({"xt_quant_path": tmp})
            inst = MagicMock()
            inst.connect.return_value = 0
            XtClass.return_value = inst
            t._get_xttrader()
            XtClass.assert_called_once_with(tmp, 1234567890)


if __name__ == "__main__":
    unittest.main()
