# -*- coding: utf-8 -*-
"""get_adapter 工厂与 QMT 单例。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

from app.libs.data_source.adapter.qmt.tests.fixtures import (
    _PATCH_LOAD_XT,
    reset_qmt_singleton,
)


class TestGetAdapterQMT(unittest.TestCase):
    """get_adapter('qmt', config) 与 QMTDataSourceAdapter 单例一致。"""

    def tearDown(self) -> None:
        reset_qmt_singleton()

    def test_get_adapter_qmt_uses_load_xtdata(self) -> None:
        reset_qmt_singleton()
        with patch(_PATCH_LOAD_XT) as mock_load:
            xt = MagicMock()
            mock_load.return_value = xt
            impl = get_adapter("qmt", {})
            self.assertIsInstance(impl, QMTDataSourceAdapter)
            self.assertIs(impl.xtdata, xt)
            mock_load.assert_called_once()
            self.assertIs(get_adapter("qmt", {}), impl)


if __name__ == "__main__":
    unittest.main()
