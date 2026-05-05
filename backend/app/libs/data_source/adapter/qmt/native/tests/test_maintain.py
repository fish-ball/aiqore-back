# -*- coding: utf-8 -*-
"""
maintain.download_history_data：真实 xtdata 冒烟。

遍历常见 period（与 mappings 中 K 线周期一致，并含 tick）及多市场示例代码（SH/SZ/BJ）。
XT_QUANT_PATH 使用环境变量。无法加载 xtdata 时用例 skip（非失败）。

  cd backend
  python -m unittest app.libs.data_source.adapter.qmt.native.tests.test_maintain -v
"""
from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.core import reset_xtdata_cache
from app.libs.data_source.adapter.qmt.mappings import BAR_PERIOD_TO_XT
from app.libs.data_source.adapter.qmt.native.maintain import download_history_data
from app.libs.data_source.adapter.qmt.native.tests.xt_test_env import (
    SAMPLE_MARKET_SYMBOLS,
    try_load_xtdata,
)

# 日线类周期：8 位起始日即可；分钟与 tick 需交易时段
_DAILY_PERIODS = ("1d", "1w", "1mon")
_INTRADAY_XT_PERIODS = tuple(sorted(set(BAR_PERIOD_TO_XT.values())))
_INTRADAY_RANGE = ("20240115093000", "20240115150000")
_DAILY_RANGE = ("20240101", "")


class TestDownloadHistoryData(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        xt, err = try_load_xtdata()
        if xt is None:
            raise unittest.SkipTest(err)
        cls._xt = xt

    @classmethod
    def tearDownClass(cls) -> None:
        reset_xtdata_cache()

    def test_download_history_data_periods_and_markets(self) -> None:
        """不同 period 与不同市场后缀组合调用 download_history_data（真实下载）。"""
        st_day, et_day = _DAILY_RANGE
        st_intra, et_intra = _INTRADAY_RANGE
        for symbol, mkt in SAMPLE_MARKET_SYMBOLS:
            for period in _DAILY_PERIODS:
                with self.subTest(market=mkt, symbol=symbol, period=period, kind="daily"):
                    download_history_data(
                        self._xt, symbol, period, start_time=st_day, end_time=et_day
                    )
            for period in _INTRADAY_XT_PERIODS:
                with self.subTest(market=mkt, symbol=symbol, period=period, kind="intraday"):
                    download_history_data(
                        self._xt,
                        symbol,
                        period,
                        start_time=st_intra,
                        end_time=et_intra,
                    )
            with self.subTest(market=mkt, symbol=symbol, period="tick", kind="intraday"):
                download_history_data(
                    self._xt,
                    symbol,
                    "tick",
                    start_time=st_intra,
                    end_time=et_intra,
                )


if __name__ == "__main__":
    unittest.main()
