# -*- coding: utf-8 -*-
"""xtdata 加载与连接探测。"""

from __future__ import annotations

import unittest
from app.libs.data_source.models import DataSourceSector
from unittest.mock import patch

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestQMTXtdataLoad(unittest.TestCase):
    """_load_xtdata 返回 None 时适配器不持有 xtdata。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_xtdata_none_when_load_returns_none(self, _mock) -> None:
        reset_qmt_singleton()
        a = QMTDataSourceAdapter({})
        self.assertIsNone(a.xtdata)


class TestQMTConnection(unittest.TestCase):
    """_require_xtdata 与 test_connection。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_require_xtdata_raises_when_none(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        with self.assertRaises(RuntimeError) as ctx:
            adapter._require_xtdata()
        self.assertIn("xtquant", str(ctx.exception))

    @patch(_PATCH_LOAD_XT, return_value=None)
    def test_test_connection_fails_when_xtdata_unavailable(self, _mock) -> None:
        adapter = QMTDataSourceAdapter({})
        ok, msg = adapter.test_connection()
        self.assertFalse(ok)
        self.assertIn("xtquant", msg)

    def test_test_connection_success(self) -> None:
        adapter = QMTDataSourceAdapter({})
        result = adapter.get_sector_list()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], DataSourceSector)
        print([x.name for x in result])
        self.assertTrue(any(x.name == "上证A股" for x in result))


if __name__ == "__main__":
    unittest.main()
