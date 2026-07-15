# -*- coding: utf-8 -*-
"""证券列表、板块、详情与 preset 板块树。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter
from app.libs.data_source.adapter.qmt.preset_data import PRESET_SECTOR_ROOTS
from app.libs.data_source.models import AssetClass, InstrumentBrief, InstrumentType

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTSectorListFromXtdata(unittest.TestCase):
    """从 xt 拉取板块列表（备用实现 _get_sector_list_from_xtdata）。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_sector_list_from_xtdata(self) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["沪深A股", "上证50"]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter._get_sector_list_from_xtdata()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].alias, "沪深A股")
        self.assertEqual(out[0].asset_class, AssetClass.EQUITY)
        self.assertEqual(out[0].instrument_type, InstrumentType.STOCK)
        self.assertEqual(out[0].children, [])
        xt.get_sector_list.assert_called_once()

    def test_get_sector_list_from_xtdata_skips_sw_and_csrc_prefixes(self) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = [
            "沪深A股",
            "SW1银行",
            "SW2机械设备",
            "SW3xxx",
            "CSRC1农副食品",
            "CSRC2foo",
            "上证50",
        ]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            aliases = [x.alias for x in adapter._get_sector_list_from_xtdata()]
        self.assertEqual(aliases, ["沪深A股", "上证50"])

    def test_get_sector_list_from_xtdata_flat(self) -> None:
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


class TestQMTSectorListPreset(unittest.TestCase):
    """get_sector_list 返回 preset_data 导出的板块树根列表。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_get_sector_list_uses_bundled_preset(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        out = adapter.get_sector_list()
        self.assertIs(out, PRESET_SECTOR_ROOTS)
        self.assertGreaterEqual(len(out), 1)
        self.assertEqual(out[0].alias, "上证A股")
        self.assertEqual(out[0].asset_class, AssetClass.EQUITY)
        self.assertEqual(out[0].instrument_type, InstrumentType.STOCK)


class TestQMTInstrumentListAndStocks(unittest.TestCase):
    """板块内股票与 get_instrument_list 聚合。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_stock_list_in_sector(self) -> None:
        xt = MagicMock()
        xt.get_stock_list_in_sector.return_value = ["600000.SH", "000001.SZ"]
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            res = adapter.get_stock_list_in_sector("沪深A股", market="SH")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].symbol, "600000.SH")

    @patch.object(QMTDataSourceAdapter, "get_stock_list_in_sector")
    def test_get_instrument_list_delegates_sector(self, mock_sector) -> None:
        mock_sector.return_value = [InstrumentBrief(symbol="x", market="SH", sector="s")]
        xt = MagicMock()
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_instrument_list(sector="沪深A股")
        mock_sector.assert_called_once_with("沪深A股", None)
        self.assertEqual(len(out), 1)

    @patch.object(QMTDataSourceAdapter, "_preset_sector_aliases_dfs")
    def test_get_instrument_list_aggregates_sectors(self, mock_aliases) -> None:
        mock_aliases.return_value = ["板块一"]
        xt = MagicMock()
        xt.get_stock_list_in_sector.return_value = ["600000.SH"]
        xt.get_instrument_list.return_value = []
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            out = adapter.get_instrument_list()
        self.assertTrue(any(x.symbol == "600000.SH" for x in out))


class TestQMTInstrumentDetail(unittest.TestCase):
    """get_instrument_detail。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_instrument_detail(self) -> None:
        xt = MagicMock()
        xt.get_instrument_detail.return_value = {"InstrumentName": "测试"}
        with patch(_PATCH_LOAD_XT, return_value=xt):
            adapter = QMTDataSourceAdapter({})
            got = adapter.get_instrument_detail("600000.SH")
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.name, "测试")
        self.assertEqual(got.code, "600000.SH")


if __name__ == "__main__":
    unittest.main()
