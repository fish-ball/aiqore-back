"""
证券交易端抽象：账户与持仓查询，与行情数据源 adapter 分离。
本模块不依赖 FastAPI，可单独测试。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SecuritiesTrader(ABC):
    """证券交易端抽象基类。"""

    @abstractmethod
    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """查询资金账号资产概要。"""
        pass

    @abstractmethod
    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """查询资金账号持仓列表。"""
        pass
