# -*- coding: utf-8 -*-
"""get_trading_dates 单元测试；依赖本机 xtquant/miniQMT。"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_trading_dates import get_trading_dates


class TestGetTradingDates(unittest.TestCase):
    """交易日（底层常见为时间戳 int 或 YYYYMMDD 字符串，此处只断言列表元素类型）。"""

    def _assert_trading_date_items(self, out: object) -> None:
        """辅助：校验列表元素为可接受的交易日表示（int 或足够长的数字字符串）。"""
        self.assertIsInstance(out, list)
        for item in out:
            self.assertIsInstance(item, (str, int))
            if isinstance(item, str):
                self.assertTrue(item.isdigit(), msg=f"非数字日期串: {item!r}")
                self.assertGreaterEqual(len(item), 8, msg=f"日期/时间戳字符串过短: {item!r}")
            else:
                self.assertGreater(item, 0)

    def test_sh_compact_range(self) -> None:
        """验证沪市、YYYYMMDD 起止、count=-1 时返回列表且元素形态合法。"""
        out = get_trading_dates(
            market="SH",
            start_time="20240101",
            end_time="20240131",
            count=-1,
        )
        self._assert_trading_date_items(out)

    def test_sz_iso_start_end(self) -> None:
        """验证深市、ISO 风格起止日期经封装后仍能返回合法交易日列表。"""
        out = get_trading_dates(
            market="SZ",
            start_time="2024-01-01",
            end_time="2024-01-31",
            count=-1,
        )
        self._assert_trading_date_items(out)

    def test_default_market_and_optional_range(self) -> None:
        """验证默认市场且起止为空串时返回列表；非空时元素形态合法。"""
        # 底层 xt 要求起止为 str，缺省用空串（与模块说明一致）
        out = get_trading_dates(start_time="", end_time="")
        self.assertIsInstance(out, list)
        if out:
            self._assert_trading_date_items(out)

    def test_positive_count_caps_length(self) -> None:
        """验证 count 为正时返回条数不超过 count，且元素形态合法。"""
        out = get_trading_dates(
            market="SH",
            start_time="20240101",
            end_time="20241231",
            count=5,
        )
        self.assertIsInstance(out, list)
        self.assertLessEqual(len(out), 5)
        if out:
            self._assert_trading_date_items(out)


if __name__ == "__main__":
    unittest.main()
