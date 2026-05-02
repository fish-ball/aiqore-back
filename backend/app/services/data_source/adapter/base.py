"""
数据源适配器抽象基类：证券列表与标的详情。
本模块不依赖 app 或 FastAPI，adapter 包可独立运行/测试。
统一 K 线模型见 app.services.data_source.models.KlineBar。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.services.data_source.models import KlineBar


class SecuritiesDataSourceAdapter(ABC):
    """证券数据源适配器抽象基类"""

    @abstractmethod
    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Any]:
        """
        获取证券列表。每项为 InstrumentBrief 或至少含 symbol、market、可选 sector 的 dict。
        sector 指定时返回该板块证券；否则返回全量/按 market 过滤。
        """
        pass

    @abstractmethod
    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取标的详细信息（如 QMT get_instrument_detail 返回结构）。"""
        pass

    def get_klines_data(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[List[KlineBar]]:
        """
        K 线数据（与 ticks 区分）。period: 1d/1w/1M 等；start_time/end_time 格式 YYYY-MM-DD HH:MM:SS。
        返回 KlineBar 列表；不支持的数据源返回 None。
        """
        return None

    def get_ticks_data(self, symbol: str, trade_date: str) -> Optional[Any]:
        """
        按交易日拉取分笔数据。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        返回值为 pandas DataFrame，列与类型见 data_schema.TICK_DF_*；不支持的数据源返回 None。
        """
        return None

    def test_connection(self) -> tuple[bool, str]:
        """测试连接是否可用。子类可覆盖；默认返回不支持。"""
        return False, "该类型暂不支持连接测试"
