# -*- coding: utf-8 -*-
"""_normalize_cli_date 单元测试（无 xt 依赖）。"""

from __future__ import annotations

import unittest

from app.libs.data_source.adapter.qmt.native.get_trading_dates import _normalize_cli_date


class TestNormalizeCliDate(unittest.TestCase):
    """日期字符串归一化为 YYYYMMDD。"""

    def test_yyyymmdd_unchanged(self) -> None:
        """验证 8 位纯数字日期原样输出为 YYYYMMDD。"""
        self.assertEqual(_normalize_cli_date("20240115"), "20240115")

    def test_iso_dash(self) -> None:
        """验证 YYYY-MM-DD 能归一为 YYYYMMDD。"""
        self.assertEqual(_normalize_cli_date("2024-01-15"), "20240115")

    def test_iso_slash(self) -> None:
        """验证 YYYY/MM/DD 能归一为 YYYYMMDD。"""
        self.assertEqual(_normalize_cli_date("2024/01/15"), "20240115")

    def test_iso_dot(self) -> None:
        """验证 YYYY.MM.DD 能归一为 YYYYMMDD。"""
        self.assertEqual(_normalize_cli_date("2024.01.15"), "20240115")

    def test_empty_after_strip_raises(self) -> None:
        """验证仅空白字符串会抛出 ValueError。"""
        with self.assertRaises(ValueError):
            _normalize_cli_date("   ")

    def test_wrong_digit_length_raises(self) -> None:
        """验证非 8 位的纯数字日期会抛出 ValueError。"""
        with self.assertRaises(ValueError):
            _normalize_cli_date("2024011")


if __name__ == "__main__":
    unittest.main()
