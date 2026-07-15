"""
数据源适配器抽象基类：证券列表与标的详情。
本模块不依赖 app 或 FastAPI，adapter 包可独立运行/测试。
统一 K 线模型见 app.libs.data_source.models.KlineBar。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.libs.data_source.models import DataSourceInstrument, DataSourceSector, KlineBar


class DataSourceAdapter(ABC):
    """数据源适配器抽象基类（证券 / 行情 / 板块等）。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """与 DataSourceType、get_adapter 注册键一致，例如 qmt。"""
        raise NotImplementedError("子类必须实现 name 属性")

    def get_instrument_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Any]:
        """
        获取证券列表。每项为 InstrumentBrief 或至少含 symbol、market、可选 sector 的 dict。
        sector 指定时返回该板块证券；否则返回全量/按 market 过滤。
        """
        raise NotImplementedError("子类必须实现 get_instrument_list")

    def get_instrument_detail(
        self,
        symbol: str,
        *,
        iscomplete: bool = False,
    ) -> Optional[DataSourceInstrument]:
        """获取标的详细信息，返回统一 DataSourceInstrument；无数据时返回 None。"""
        raise NotImplementedError("子类必须实现 get_instrument_detail")

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
        raise NotImplementedError("子类必须实现 get_klines_data")

    def get_ticks_data(self, symbol: str, trade_date: str) -> Optional[Any]:
        """
        按交易日拉取分笔数据。trade_date 为 YYYYMMDD 或 YYYY-MM-DD。
        返回值为 pandas DataFrame，列与迅投 get_market_data_ex period=tick 一致；不支持的数据源返回 None。
        """
        raise NotImplementedError("子类必须实现 get_ticks_data")

    def get_sector_list(self) -> List[DataSourceSector]:
        """获取数据源板块树（根节点列表）；不支持时返回空列表。"""
        raise NotImplementedError("子类必须实现 get_sector_list")

    def get_realtime_quote(self, symbols: List[str]) -> Optional[Dict[str, Any]]:
        """批量实时行情；返回 symbol -> 行情对象或字典。"""
        raise NotImplementedError("子类必须实现 get_realtime_quote")

    def test_connection(self) -> tuple[bool, str]:
        """测试连接是否可用。"""
        raise NotImplementedError("子类必须实现 test_connection")
