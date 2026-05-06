# -*- coding: utf-8 -*-
"""
数据源服务：证券数据源适配器工厂、连接 config 解析、标的/板块同步。
默认单例适配器的具体注册实现由 settings 与本模块内 get_adapter 调用约定；业务服务应依赖 DataSourceAdapter 并由本模块注入。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.data_source import DataSource
from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.adapter.qmt.config import select_qmt_adapter_config

logger = logging.getLogger(__name__)

__all__ = [
    "default_qmt_config_from_settings",
    "resolve_adapter_config",
    "get_default_securities_adapter",
    "get_default_qmt_adapter",
    "sync_instruments",
    "sync_single_instrument",
    "sync_sectors",
]


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
            db.query(DataSource)
            .filter(
                DataSource.source_type == "qmt",
                DataSource.is_active.is_(True),
            )
            .order_by(DataSource.is_quote_source.desc(), DataSource.id)
            .all()
        )
        return select_qmt_adapter_config(source_id, rows, default_qmt_config_from_settings())
    if key in ("joinquant", "tushare"):
        if source_id is not None:
            conn = (
                db.query(DataSource)
                .filter(
                    DataSource.id == source_id,
                    DataSource.source_type == key,
                    DataSource.is_active.is_(True),
                )
                .first()
            )
            if not conn:
                return None, f"未找到 id={source_id} 的启用 {key} 连接"
        return {}, None
    return None, f"不支持的 adapter: {adapter}"


_default_securities_adapter: Optional[DataSourceAdapter] = None


def get_default_securities_adapter() -> DataSourceAdapter:
    """
    返回进程内单例的默认证券数据源适配器（具体注册实现由 settings / 连接表在 get_adapter 层决定）。
    """
    global _default_securities_adapter
    if _default_securities_adapter is None:
        _default_securities_adapter = get_adapter("qmt", {
            "xt_quant_path": settings.XT_QUANT_PATH,
            "xt_quant_acct": settings.XT_QUANT_ACCT,
        })
    return _default_securities_adapter


def get_default_qmt_adapter() -> DataSourceAdapter:
    """兼容旧名，等价于 get_default_securities_adapter()。"""
    return get_default_securities_adapter()


def sync_instruments(
    db: Session,
    adapter: str = "qmt",
    source_id: Optional[int] = None,
    market: Optional[str] = None,
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    从指定数据源同步标的到数据库。
    使用抽象适配器取数，再调用 instrument_service.update_instruments_from_data 写库。
    """
    from app.services.instrument_service import instrument_service

    key = (adapter or "qmt").strip().lower()
    config, err = resolve_adapter_config(db, key, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }

    impl = get_adapter(key, config)
    securities = impl.get_stock_list(market=market, sector=sector)
    if not securities:
        return {
            "success": False,
            "message": "未获取到证券列表",
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    logger.info("数据源 %s 获取到 %s 只证券，开始补全详情并写库", key, len(securities))
    with_details: List[Dict[str, Any]] = []
    for sec in securities:
        row = sec.model_dump() if hasattr(sec, "model_dump") else sec
        symbol = row.get("symbol")
        if not symbol:
            continue
        detail = impl.get_instrument_detail(symbol)
        with_details.append({
            "symbol": symbol,
            "market": row.get("market", "SH" if symbol.endswith(".SH") else "SZ"),
            "sector": row.get("sector", ""),
            "detail": detail,
        })
    return instrument_service.update_instruments_from_data(db, with_details)


def sync_sectors(
    db: Session,
    adapter: str = "qmt",
    source_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    从指定数据源同步板块列表到数据库：在此解析连接并构造适配器，再注入 sector_service。
    解析规则与 sync_instruments 一致。
    """
    from app.services.sector_service import sector_service

    key = (adapter or "qmt").strip().lower()
    config, err = resolve_adapter_config(db, key, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    impl = get_adapter(key, config or {})
    return sector_service.sync_sectors_from_adapter(db, impl)


def sync_single_instrument(
    db: Session,
    symbol: str,
    adapter: str = "qmt",
    source_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    从指定数据源同步单个标的到数据库。
    symbol 可为带后缀的 000001.SZ；market 从后缀推断，无则默认 SH。
    """
    from app.services.instrument_service import instrument_service

    key = (adapter or "qmt").strip().lower()
    resolved, err = resolve_adapter_config(db, key, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 1,
        }
    impl = get_adapter(key, resolved)
    detail = impl.get_instrument_detail(symbol)
    if symbol.endswith(".SH") or symbol.endswith(".SZ"):
        market = "SH" if symbol.endswith(".SH") else "SZ"
    else:
        market = "SH"
    with_details = [
        {
            "symbol": symbol,
            "market": market,
            "sector": "",
            "detail": detail,
        }
    ]
    return instrument_service.update_instruments_from_data(db, with_details)
