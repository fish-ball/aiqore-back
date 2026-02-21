"""QMT 数据源适配器：按连接配置构造 QMTService，实现抽象接口"""
from typing import List, Dict, Any, Optional

from app.services.data_source.base import SecuritiesDataSourceAdapter
from app.services.qmt_service import QMTService


class QMTAdapter(SecuritiesDataSourceAdapter):
    """QMT 适配器，使用连接配置（来自 data_source_connections 或 dict）"""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._qmt: Optional[QMTService] = None

    def _get_qmt(self) -> QMTService:
        if self._qmt is None:
            self._qmt = QMTService(config=self._config)
            self._qmt.connect()
        return self._qmt

    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        if sector:
            return self._get_qmt().get_stock_list_in_sector(sector, market)
        return self._get_qmt().get_stock_list(market)

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self._get_qmt().get_instrument_detail(symbol)
