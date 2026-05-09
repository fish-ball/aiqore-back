# -*- coding: utf-8 -*-
"""get_sector_list 单元测试；依赖本机 xtquant/miniQMT。"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_sector_list import get_sector_list

# 与业务侧常用根板块名称对齐（写死，避免测试依赖 preset_data）
_EXPECTED_ROOT_SECTOR_NAMES = (
    "上证A股",
    "深证A股",
    "创业板",
    "科创板",
    "沪市ETF",
    "深市ETF",
    "沪市指数",
    "深市指数",
)


class TestGetSectorList(unittest.TestCase):
    """板块列表：若干根板块名须出现在 xt 全量列表中。"""

    def test_expected_sector_names_exist_in_xt_list(self) -> None:
        """验证 xt 返回的板块名为 str 列表，且上述写死的板块名均出现在列表中。"""
        out = get_sector_list()
        self.assertIsInstance(out, list)
        self.assertTrue(all(isinstance(x, str) for x in out))
        names = set(out)
        for alias in _EXPECTED_ROOT_SECTOR_NAMES:
            with self.subTest(alias=alias):
                self.assertIn(
                    alias,
                    names,
                    msg=f"板块名未出现在 xtdata.get_sector_list 结果中: {alias}",
                )


if __name__ == "__main__":
    unittest.main()
