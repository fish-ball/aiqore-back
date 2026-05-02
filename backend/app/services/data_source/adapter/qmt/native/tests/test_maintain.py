# -*- coding: utf-8 -*-
"""
maintain.download_history_data：真实 xtdata 冒烟。

遍历常见 period（与 mappings 中 K 线周期一致，并含 tick）及多市场示例代码（SH/SZ/BJ）。
XT_QUANT_PATH 优先环境变量，否则 app.config。无法加载 xtdata 时用例 skip（非失败）。

  cd backend
  python -m unittest app.services.data_source.adapter.qmt.native.tests.test_maintain -v
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import Any, Optional, Tuple

from app.services.data_source.adapter.qmt.core import ensure_xtdata, reset_xtdata_cache
from app.services.data_source.adapter.qmt.mappings import BAR_PERIOD_TO_XT
from app.services.data_source.adapter.qmt.native.maintain import download_history_data

# 迅投后缀：上证 / 深证 / 北交所（示例代码，用于下载接口多市场覆盖）
_MARKET_SYMBOLS = (
    ("600000.SH", "SH"),
    ("000001.SZ", "SZ"),
    ("830799.BJ", "BJ"),
)

# 日线类周期：8 位起始日即可；分钟与 tick 需交易时段
_DAILY_PERIODS = ("1d", "1w", "1mon")
_INTRADAY_XT_PERIODS = tuple(sorted(set(BAR_PERIOD_TO_XT.values())))
_INTRADAY_RANGE = ("20240115093000", "20240115150000")
_DAILY_RANGE = ("20240101", "")


def _xt_path() -> Optional[str]:
    p = os.environ.get("XT_QUANT_PATH", "").strip()
    if p:
        return p
    try:
        from app.config import settings

        return (getattr(settings, "XT_QUANT_PATH", None) or "").strip() or None
    except Exception:
        return None


def _try_xtdata() -> Tuple[Optional[Any], str]:
    path = _xt_path()
    if not path:
        return None, "无 XT_QUANT_PATH（环境变量或 app.config）"
    if not Path(path).is_dir():
        return None, f"路径无效: {path}"
    reset_xtdata_cache()
    xt = ensure_xtdata(path)
    if xt is None:
        return None, "ensure_xtdata 失败（xtquant / miniQMT）"
    return xt, ""


class TestDownloadHistoryData(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        xt, err = _try_xtdata()
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
        for symbol, mkt in _MARKET_SYMBOLS:
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
