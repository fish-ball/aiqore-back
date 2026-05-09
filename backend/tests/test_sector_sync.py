# -*- coding: utf-8 -*-
"""板块同步：data_source_service 解析连接；sector_service 仅接收适配器实例。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.libs.data_source.models import AssetClass, DataSourceSector, InstrumentType
from app.services.data_source_service import sync_sectors
from app.services.sector_service import sector_service


class TestSectorSyncResolve(unittest.TestCase):
    """resolve_adapter_for_data_source_id 失败时不构造适配器、不写库。"""

    @patch("app.services.data_source_service.resolve_adapter_for_data_source_id")
    def test_sync_sectors_returns_error_when_config_unresolved(
        self, mock_resolve
    ) -> None:
        mock_resolve.return_value = (None, "数据源不存在或未启用")
        db = MagicMock()
        result = sync_sectors(db, source_id=1)
        self.assertFalse(result["success"])
        self.assertIn("数据源", result["message"])

    @patch("app.services.data_source_service.resolve_adapter_for_data_source_id")
    def test_sync_sectors_no_sectors_no_commit(self, mock_resolve) -> None:
        impl = MagicMock()
        impl.name = "joinquant"
        impl.get_sector_list.return_value = []
        mock_resolve.return_value = (impl, None)
        db = MagicMock()
        result = sync_sectors(db, source_id=1)
        self.assertFalse(result["success"])
        db.commit.assert_not_called()


class TestSectorServiceAdapterInjection(unittest.TestCase):
    """板块服务只依赖适配器接口。"""

    def test_sync_sectors_from_adapter_rejects_unknown_adapter_name(self) -> None:
        db = MagicMock()
        impl = MagicMock()
        impl.name = "unknown_vendor"
        impl.get_sector_list.return_value = [
            DataSourceSector(
                name="x",
                alias="x",
                asset_class=AssetClass.EQUITY,
                instrument_type=InstrumentType.STOCK,
                children=[],
            )
        ]
        r = sector_service.sync_sectors_from_adapter(db, impl)
        self.assertFalse(r["success"])
        self.assertIn("DataSourceType", r["message"])


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
        impl.name = "qmt"
        with patch(
            "app.services.data_source_service.resolve_adapter_for_data_source_id",
            return_value=(impl, None),
        ):
            out = sync_sectors(db, source_id=2)
        mock_from_adapter.assert_called_once()
        call_args = mock_from_adapter.call_args
        self.assertIs(call_args[0][0], db)
        self.assertIs(call_args[0][1], impl)
        self.assertEqual(call_args[1], {})
        self.assertTrue(out["success"])


if __name__ == "__main__":
    unittest.main()
