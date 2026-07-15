# -*- coding: utf-8 -*-
"""实时行情 get_realtime_quote。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTRealtimeQuote(unittest.TestCase):
    """get_full_tick 与详情名拼接。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

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

    def test_get_realtime_quote_exception_returns_none(self) -> None:
        xt = MagicMock()
        xt.get_full_tick.side_effect = RuntimeError("net")
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            self.assertIsNone(adapter.get_realtime_quote(["000001.SZ"]))


if __name__ == "__main__":
    unittest.main()
