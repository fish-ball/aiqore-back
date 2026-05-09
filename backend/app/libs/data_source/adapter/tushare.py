# -*- coding: utf-8 -*-
"""tushare 数据源适配器。未实现的方法继承基类行为（NotImplementedError）。不依赖 app/FastAPI。"""
from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from .base import DataSourceAdapter


class TushareDataSourceAdapterConfig(TypedDict, total=False):
    """Tushare 行情配置 schema（占位，后续扩展 token 等）。"""

    token: str


class TushareDataSourceAdapter(DataSourceAdapter):
    """tushare 占位：后续按需实现各接口方法。"""

    @property
    def name(self) -> str:
        return "tushare"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = dict(config or {})
