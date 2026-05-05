# -*- coding: utf-8 -*-
"""板块同步：data_source_service 解析连接；sector_service 仅接收适配器实例。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.data_source_service import sync_sectors
from app.services.sector_service import sector_service


class TestSectorSyncResolve(unittest.TestCase):
    """resolve_adapter_config 失败时不构造适配器、不写库。"""

    @patch("app.libs.data_source.adapter.get_adapter")
    @patch("app.services.data_source_service.resolve_adapter_config")
    def test_sync_sectors_returns_error_when_config_unresolved(
        self, mock_resolve, mock_get_adapter
    ) -> None:
        mock_resolve.return_value = (None, "未找到 id=1 的启用 QMT 连接")
        db = MagicMock()
        result = sync_sectors(db, adapter="qmt", source_id=1)
        self.assertFalse(result["success"])
        self.assertIn("未找到", result["message"])
        mock_get_adapter.assert_not_called()

    @patch("app.libs.data_source.adapter.get_adapter")
    @patch("app.services.data_source_service.resolve_adapter_config")
    def test_sync_sectors_no_sectors_no_commit(self, mock_resolve, mock_get_adapter) -> None:
        mock_resolve.return_value = ({}, None)
        impl = MagicMock()
        impl.get_sector_list.return_value = []
        mock_get_adapter.return_value = impl
        db = MagicMock()
        result = sync_sectors(db, adapter="joinquant")
        self.assertFalse(result["success"])
        db.commit.assert_not_called()


class TestSectorServiceAdapterInjection(unittest.TestCase):
    """板块服务只依赖适配器接口。"""

    def test_sync_sectors_from_adapter_rejects_empty_source_key(self) -> None:
        db = MagicMock()
        impl = MagicMock()
        impl.get_sector_list.return_value = ["沪深A股"]
        r = sector_service.sync_sectors_from_adapter(db, impl, source_key="  ")
        self.assertFalse(r["success"])
        self.assertIn("source_key", r["message"])


class TestDataSourceServiceSyncSectors(unittest.TestCase):
    """sync_sectors 解析后调用 sector_service.sync_sectors_from_adapter。"""

    @patch.object(sector_service, "sync_sectors_from_adapter")
    def test_data_source_sync_sectors_delegates(self, mock_from_adapter) -> None:
        mock_from_adapter.return_value = {
            "success": True,
            "message": "ok",
            "total": 1,
            "created": 0,
            "updated": 1,
            "errors": 0,
        }
        db = MagicMock()
        impl = MagicMock()
        with patch("app.services.data_source_service.resolve_adapter_config", return_value=({}, None)):
            with patch("app.services.data_source_service.get_adapter", return_value=impl):
                out = sync_sectors(db, adapter="qmt", source_id=2)
        mock_from_adapter.assert_called_once()
        call_kw = mock_from_adapter.call_args
        self.assertIs(call_kw[0][0], db)
        self.assertIs(call_kw[0][1], impl)
        self.assertEqual(call_kw[1], {"source_key": "qmt"})
        self.assertTrue(out["success"])


if __name__ == "__main__":
    unittest.main()
