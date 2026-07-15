# -*- coding: utf-8 -*-
"""除权因子 get_divid_factors。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTDividFactors(unittest.TestCase):
    """get_divid_factors 是否支持与返回 DataFrame。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

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


if __name__ == "__main__":
    unittest.main()
