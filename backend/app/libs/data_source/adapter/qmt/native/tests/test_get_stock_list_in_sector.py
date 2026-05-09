# -*- coding: utf-8 -*-
"""get_stock_list_in_sector 单元测试；依赖本机 xtquant/miniQMT。"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_stock_list_in_sector import get_stock_list_in_sector

# 本机 QMT 实测：各板块中应存在的代表性代码（用于校验板块成分接口）
_SECTOR_EXPECT_SYMBOL = (
    # 权益 / ETF / 指数
    ("上证A股", "600519.SH"),
    ("深证A股", "000001.SZ"),
    ("创业板", "300750.SZ"),
    ("科创板", "688981.SH"),
    ("沪市ETF", "510300.SH"),
    ("深市ETF", "159915.SZ"),
    ("沪市指数", "000300.SH"),
    ("深市指数", "399001.SZ"),
    # 期货 / 期权（交易所板块：同一板块可各抽期货、期权一条）
    ("上期所", "rb2605.SF"),
    ("上期所", "ag2612P11700.SF"),
    ("大商所", "jd2606.DF"),
    ("大商所", "bz2610-P-4800.DF"),
    ("郑商所", "PK612.ZF"),
    ("中金所", "IC2612.IF"),
    ("中金所", "IO2605-P-5000.IF"),
    ("能源中心", "nr2612.INE"),
    ("能源中心", "sc2607P470.INE"),
    # 沪深 ETF 期权（独立板块）
    ("上证期权", "10011096.SHO"),
    ("深证期权", "90007110.SZO"),
)


class TestGetStockListInSector(unittest.TestCase):
    """抽样板块：列表非空且包含已知标的。"""

    def test_sample_sectors_contain_known_symbols(self) -> None:
        """验证权益/ETF/指数及期货、期权相关板块成分为非空 str 列表，且包含约定的代表性代码。"""
        for sector, symbol in _SECTOR_EXPECT_SYMBOL:
            with self.subTest(sector=sector, symbol=symbol):
                lst = get_stock_list_in_sector(sector)
                self.assertIsInstance(lst, list)
                self.assertTrue(all(isinstance(x, str) for x in lst))
                self.assertGreater(len(lst), 0)
                self.assertIn(symbol, lst)


if __name__ == "__main__":
    unittest.main()
