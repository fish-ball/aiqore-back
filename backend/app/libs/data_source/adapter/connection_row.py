# -*- coding: utf-8 -*-
"""
数据源连接行协议：与 ORM DataSourceConnection 字段对齐。
data_source 包仅依赖本 Protocol，不引用 app.models。
"""
from __future__ import annotations

from typing import Any, Protocol


class DataSourceConnectionLike(Protocol):
    """供适配器 config 映射及按 id 筛选；实现类可为 SQLAlchemy 模型。"""

    id: Any
    source_type: str
    host: Any
    port: Any
    user: Any
    password: Any
    xt_quant_path: Any
    xt_quant_acct: Any
