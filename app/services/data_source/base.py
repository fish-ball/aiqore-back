"""数据源适配器抽象基类：证券列表与标的详情"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class SecuritiesDataSourceAdapter(ABC):
    """证券数据源适配器抽象基类"""

    @abstractmethod
    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取证券列表。每项至少含 symbol、market，可选 sector。
        sector 指定时返回该板块证券；否则返回全量/按 market 过滤。
        """
        pass

    @abstractmethod
    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取标的详细信息（如 QMT get_instrument_detail 返回结构）。"""
        pass
