# -*- coding: utf-8 -*-
"""分笔 get_ticks_data。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTTicks(unittest.TestCase):
    """get_ticks_data 日期校验与 DataFrame 返回。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

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


if __name__ == "__main__":
    unittest.main()
