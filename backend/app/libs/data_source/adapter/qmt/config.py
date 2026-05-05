# -*- coding: utf-8 -*-
"""QMT 连接 config：纯映射与选择逻辑（无 ORM、无 settings）。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple

from app.libs.data_source.adapter.connection_row import DataSourceConnectionLike


def connection_row_to_config(conn: DataSourceConnectionLike) -> Dict[str, Any]:
    """将连接行转为 QMTAdapter 所需 config（含 xt_quant_path / xt_quant_acct）。"""
    return {
        "host": conn.host,
        "port": conn.port,
        "user": conn.user,
        "password": conn.password,
        "xt_quant_path": conn.xt_quant_path,
        "xt_quant_acct": conn.xt_quant_acct,
    }


def select_qmt_adapter_config(
    source_id: Optional[int],
    ordered_active_qmt_rows: Sequence[DataSourceConnectionLike],
    fallback_config: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    在已筛选、已排序的 QMT 启用连接列表中选取 config。
    ordered_active_qmt_rows：与 ORM 查询 order_by(is_quote_source.desc(), id) 一致。
    返回 (config_dict, error_message)；成功时 error_message 为 None。
    """
    if source_id is not None:
        for row in ordered_active_qmt_rows:
            if row.id == source_id:
                return connection_row_to_config(row), None
        return None, f"未找到 id={source_id} 的启用 QMT 连接"
    if ordered_active_qmt_rows:
        return connection_row_to_config(ordered_active_qmt_rows[0]), None
    return fallback_config, None
