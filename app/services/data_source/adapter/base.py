"""
数据源适配器抽象基类：证券列表与标的详情。
本模块不依赖 app 或 FastAPI，adapter 包可独立运行/测试。
"""
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

    @abstractmethod
    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        查询指定资金账号的持仓列表。
        每项至少含 symbol（证券代码）、volume（持仓数量），
        可选 can_use_volume、market_value、avg_price、last_price、profit_rate 等。
        不支持持仓查询的数据源可返回空列表（需在子类中显式实现）。
        """
        pass

    def get_market_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        K 线原始数据。period: 1d/1w/1M 等；start_time/end_time 格式 YYYY-MM-DD HH:MM:SS。
        不支持的数据源返回 None（子类可覆盖实现）。
        """
        return None

    def get_ticks(self, symbol: str, trade_date: str) -> Optional[List[Dict[str, Any]]]:
        """
        按交易日拉取分时数据。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        不支持的数据源返回 None（子类可覆盖实现）。
        """
        return None

    def test_connection(self) -> tuple[bool, str]:
        """测试连接是否可用。子类可覆盖；默认返回不支持。"""
        return False, "该类型暂不支持连接测试"
