# -*- coding: utf-8 -*-
"""
数据源适配器 config 解析（依赖 app.models / app.config）。
供 API、Celery、标的同步等上层调用；data_source 原子包内不引用本模块。
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.data_source_connection import DataSourceConnection
from app.libs.data_source.adapter.qmt.config import select_qmt_adapter_config


def default_qmt_config_from_settings() -> Dict[str, Any]:
    """无启用 QMT 连接记录时，从全局 settings 构造 QMT 配置。"""
    return {
        "host": settings.QMT_HOST,
        "port": settings.QMT_PORT,
        "user": settings.QMT_USER,
        "password": settings.QMT_PASSWORD,
        "xt_quant_path": settings.XT_QUANT_PATH,
        "xt_quant_acct": settings.XT_QUANT_ACCT,
    }


def resolve_adapter_config(
    db: Session,
    adapter: str,
    source_id: Optional[int],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    根据 adapter（与 get_adapter 注册键一致）解析 config。
    返回 (config_dict, error_message)；成功时 error_message 为 None。
    """
    key = (adapter or "").strip().lower()
    if key == "qmt":
        rows = (
            db.query(DataSourceConnection)
            .filter(
                DataSourceConnection.source_type == "qmt",
                DataSourceConnection.is_active.is_(True),
            )
            .order_by(DataSourceConnection.is_quote_source.desc(), DataSourceConnection.id)
            .all()
        )
        return select_qmt_adapter_config(source_id, rows, default_qmt_config_from_settings())
    if key in ("joinquant", "tushare"):
        if source_id is not None:
            conn = (
                db.query(DataSourceConnection)
                .filter(
                    DataSourceConnection.id == source_id,
                    DataSourceConnection.source_type == key,
                    DataSourceConnection.is_active.is_(True),
                )
                .first()
            )
            if not conn:
                return None, f"未找到 id={source_id} 的启用 {key} 连接"
        return {}, None
    return None, f"不支持的 adapter: {adapter}"
