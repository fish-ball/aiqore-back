# -*- coding: utf-8 -*-
"""QMT 适配器 get_sector_list：通过 mock xtdata 验证拉取板块列表。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.adapter.qmt import QMTAdapter


class TestQMTAdapterGetSectorList(unittest.TestCase):
    """模拟 xtdata.get_sector_list，断言 QMTAdapter 返回板块名称列表。"""

    @patch.object(QMTAdapter, "_get_xtdata")
    def test_get_sector_list_from_xtdata(self, mock_gx) -> None:
        xt = MagicMock()
        xt.get_sector_list.return_value = ["沪深A股", "上证50"]
        mock_gx.return_value = xt
        adapter = QMTAdapter({"xt_quant_path": "/tmp"})
        self.assertEqual(adapter.get_sector_list(), ["沪深A股", "上证50"])
        xt.get_sector_list.assert_called_once()


if __name__ == "__main__":
    unittest.main()
