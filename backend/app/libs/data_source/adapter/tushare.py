# -*- coding: utf-8 -*-
"""tushare 数据源适配器（未实现，返回空）。不依赖 app/FastAPI。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from .base import DataSourceAdapter


class TushareDataSourceAdapterConfig(TypedDict, total=False):
    """Tushare 行情配置 schema（占位，后续扩展 token 等）。"""

    token: str


class TushareDataSourceAdapter(DataSourceAdapter):
    """tushare 占位：后续实现"""

    @property
    def name(self) -> str:
        return "tushare"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = dict(config or {})

    def get_stock_list(self, market: Optional[str] = None, sector: Optional[str] = None) -> List[Any]:
        return []

    def get_instrument_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        return None
