"""聚宽数据源适配器（未实现，返回空）"""
from typing import List, Dict, Any, Optional

from app.services.data_source.base import SecuritiesDataSourceAdapter


class JoinQuantAdapter(SecuritiesDataSourceAdapter):
    """聚宽占位：后续实现"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}

    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        return None

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """聚宽占位：不支持持仓查询，返回空列表。"""
        return []
