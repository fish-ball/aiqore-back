# -*- coding: utf-8 -*-
"""get_instrument_detail：按证券类型用真实行情校验映射（依赖本机 xtquant / miniQMT）。"""
from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter
from app.libs.data_source.adapter.qmt.tests.fixtures import reset_qmt_singleton
from app.libs.data_source.models.instrument import (
    DataSourceInstrumentETF,
    DataSourceInstrumentFund,
    DataSourceInstrumentFuture,
    DataSourceInstrumentIndex,
    DataSourceInstrumentOption,
    DataSourceInstrumentStock,
)


class TestQMTGetInstrumentDetailByKind(unittest.TestCase):
    """按类型拉取标的详情：依赖本机 xtquant / miniQMT。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def _adapter_or_skip(self) -> QMTDataSourceAdapter:
        adapter = QMTDataSourceAdapter()
        if adapter.xtdata is None:
            self.skipTest("需要本机可 import xtquant 且 miniQMT 可用")
        return adapter

    def _detail_or_skip(
        self,
        adapter: QMTDataSourceAdapter,
        symbol: str,
        reason: str,
        *,
        iscomplete: bool = False,
    ):
        got = adapter.get_instrument_detail(symbol, iscomplete=iscomplete)
        if got is None:
            self.skipTest(f"{reason}（symbol={symbol}）")
        return got

    def test_stock_a_share(self) -> None:
        """上证 A 股 -> DataSourceInstrumentStock。"""
        adapter = self._adapter_or_skip()
        got = self._detail_or_skip(adapter, "600000.SH", "未返回股票详情")
        self.assertIsInstance(got, DataSourceInstrumentStock)
        self.assertEqual(got.code, "600000.SH")
        self.assertTrue(got.name)
        self.assertIn(".", got.code)

    def test_etf(self) -> None:
        """沪深 ETF -> DataSourceInstrumentETF。"""
        adapter = self._adapter_or_skip()
        got = self._detail_or_skip(adapter, "510300.SH", "未返回 ETF 详情")
        self.assertIsInstance(got, DataSourceInstrumentETF)
        self.assertEqual(got.code, "510300.SH")
        self.assertTrue(got.name)
        self.assertIn(".", got.code)

    def test_lof_fund(self) -> None:
        """场内基金 LOF -> DataSourceInstrumentFund。"""
        adapter = self._adapter_or_skip()
        got = self._detail_or_skip(adapter, "161725.SZ", "未返回基金详情")
        self.assertIsInstance(got, DataSourceInstrumentFund)
        self.assertEqual(got.code, "161725.SZ")
        self.assertTrue(got.name)
        self.assertIn(".", got.code)

    def test_broad_index(self) -> None:
        """常用指数 -> DataSourceInstrumentIndex。"""
        adapter = self._adapter_or_skip()
        got = self._detail_or_skip(adapter, "000300.SH", "未返回指数详情")
        self.assertIsInstance(got, DataSourceInstrumentIndex)
        self.assertEqual(got.code, "000300.SH")
        self.assertTrue(got.name)
        self.assertIn(".", got.code)

    def test_future_contract(self) -> None:
        """商品期货合约 -> DataSourceInstrumentFuture（合约过期时需改代码）。"""
        adapter = self._adapter_or_skip()
        # 上期所螺纹主力附近月份，过期后请换成当前可交易合约
        got = self._detail_or_skip(adapter, "rb2605.SF", "未返回期货详情")
        self.assertIsInstance(got, DataSourceInstrumentFuture)
        self.assertTrue(got.code)
        self.assertTrue(got.name)
        self.assertIn(".", got.code)

    def test_option_contract(self) -> None:
        """股指期权 -> DataSourceInstrumentOption（需完整字段以含 OptionType；合约过期时请改代码）。"""
        adapter = self._adapter_or_skip()
        # iscomplete=True：非完整行情缺 OptionType 时会被判为期货
        got = self._detail_or_skip(
            adapter,
            "IO2606-C-4500.IF",
            "未返回期权详情",
            iscomplete=True,
        )
        self.assertIsInstance(got, DataSourceInstrumentOption)
        self.assertTrue(got.code)
        self.assertTrue(got.name)
        self.assertIn(".", got.code)


if __name__ == "__main__":
    unittest.main()
