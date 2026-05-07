# -*- coding: utf-8 -*-
"""QMT 适配器 get_sector_list：通过 mock xtdata 验证拉取板块列表。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.models import MarketLayer
from app.libs.data_source.adapter.qmt import QMTAdapter


class TestQMTAdapterGetSectorList(unittest.TestCase):
    """模拟 xtdata.get_sector_list，断言 QMTAdapter 返回 DataSourceSector 扁平列表。"""

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_sector_list_from_xtdata(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["沪深A股", "上证50"]
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        out = adapter.get_sector_list()
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].alias, "沪深A股")
        self.assertEqual(out[0].asset_class, MarketLayer.Equity)
        self.assertEqual(out[0].children, [])
        xt.get_sector_list.assert_called_once()

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_sector_list_skips_sw_and_csrc_prefixes(self, mock_gx) -> None:
        """SW1/2/3、CSRC1/2 开头的板块键不进入返回列表。"""
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
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        aliases = [x.alias for x in adapter.get_sector_list()]
        self.assertEqual(aliases, ["沪深A股", "上证50"])


if __name__ == "__main__":
    unittest.main()
