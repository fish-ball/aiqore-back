# -*- coding: utf-8 -*-
"""数据源连接 ORM 行 -> 适配器实例（供 API 连接测试等使用）。"""
from __future__ import annotations

from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.connection_row import DataSourceLike
from app.libs.data_source.adapter.qmt.config import connection_row_to_config


def get_adapter_for_connection(conn: DataSourceLike):
    """根据连接记录的 source_type 路由到对应适配器。"""
    if conn.source_type == "qmt":
        return get_adapter("qmt", connection_row_to_config(conn))
    return get_adapter(conn.source_type, {})
