# -*- coding: utf-8 -*-
"""QMT 板块：preset_data 成品与 xtdata 备用路径 _get_sector_list_from_xtdata。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter
from app.libs.data_source.adapter.qmt.preset_data import PRESET_SECTOR_ROOTS
from app.libs.data_source.models import AssetClass, InstrumentType

_PATCH_LOAD_XT = "app.libs.data_source.adapter.qmt.adapter.QMTDataSourceAdapter._load_xtdata"


class TestQMTAdapterGetSectorListFromXt(unittest.TestCase):
    """从 xt 拉取并剔除前缀（备用实现）。"""

    def tearDown(self) -> None:
        QMTDataSourceAdapter.reset_singleton_for_tests()

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


class TestQMTAdapterPresetData(unittest.TestCase):
    """get_sector_list 直接返回 preset_data 导出的板块树根列表。"""

    def tearDown(self) -> None:
        QMTDataSourceAdapter.reset_singleton_for_tests()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_get_sector_list_uses_bundled_preset(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        out = adapter.get_sector_list()
        self.assertIs(out, PRESET_SECTOR_ROOTS)
        self.assertGreaterEqual(len(out), 1)
        self.assertEqual(out[0].alias, "上证A股")
        self.assertEqual(out[0].asset_class, AssetClass.EQUITY)
        self.assertEqual(out[0].instrument_type, InstrumentType.STOCK)


if __name__ == "__main__":
    unittest.main()
