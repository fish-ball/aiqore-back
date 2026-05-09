# -*- coding: utf-8 -*-
"""
数据源服务：从库取 DataSource 行，用 source_type + config 经 get_adapter 构造适配器；标的/板块同步。
业务服务应依赖 DataSourceAdapter 并由本模块注入。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.libs.data_source.adapter import get_adapter
from app.libs.data_source.adapter.base import DataSourceAdapter
from app.libs.data_source.models.enums import DataSourceType
from app.models.data_source import DataSource

logger = logging.getLogger(__name__)

__all__ = [
    "get_adapter_for_data_source",
    "get_active_data_source",
    "resolve_adapter_for_data_source_id",
    "sync_instruments",
    "sync_single_instrument",
    "sync_sectors",
]


def get_adapter_for_data_source(data_source: DataSource) -> DataSourceAdapter:
    """由 ORM 行构造适配器（不校验 is_active，调用方负责）。"""
    st = data_source.source_type
    key = st.value if isinstance(st, DataSourceType) else str(st)
    return get_adapter(key, dict(data_source.config or {}))


def get_active_data_source(db: Session, data_source_id: int) -> Optional[DataSource]:
    """按 id 查询启用中的数据源连接。"""
    return (
        db.query(DataSource)
        .filter(DataSource.id == data_source_id, DataSource.is_active.is_(True))
        .first()
    )


def resolve_adapter_for_data_source_id(
    db: Session,
    data_source_id: int,
) -> Tuple[Optional[DataSourceAdapter], Optional[str]]:
    """由数据源连接 id 解析适配器；不存在或未启用时返回 (None, 错误说明)。"""
    row = get_active_data_source(db, data_source_id)
    if row is None:
        return None, "数据源不存在或未启用"
    return get_adapter_for_data_source(row), None


def sync_instruments(
    db: Session,
    source_id: int,
    market: Optional[str] = None,
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    从指定数据源连接（data_sources.id）同步标的到数据库。
    使用抽象适配器取数，再调用 instrument_service.update_instruments_from_data 写库。
    """
    from app.services.instrument_service import instrument_service

    impl, err = resolve_adapter_for_data_source_id(db, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }

    instruments = impl.get_instrument_list(market=market, sector=sector)
    if not instruments:
        return {
            "success": False,
            "message": "未获取到证券列表",
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    logger.info("数据源连接 id=%s (%s) 获取到 %s 只证券，开始补全详情并写库", source_id, impl.name, len(instruments))
    with_details: List[Dict[str, Any]] = []
    for sec in instruments:
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


def sync_sectors(db: Session, source_id: int) -> Dict[str, Any]:
    """
    从指定数据源连接同步板块列表到数据库：构造适配器后注入 sector_service。
    """
    from app.services.sector_service import sector_service

    impl, err = resolve_adapter_for_data_source_id(db, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
        }
    return sector_service.sync_sectors_from_adapter(db, impl)


def sync_single_instrument(db: Session, symbol: str, source_id: int) -> Dict[str, Any]:
    """
    从指定数据源连接同步单个标的到数据库。
    symbol 可为带后缀的 000001.SZ；market 从后缀推断，无则默认 SH。
    """
    from app.services.instrument_service import instrument_service

    impl, err = resolve_adapter_for_data_source_id(db, source_id)
    if err is not None:
        return {
            "success": False,
            "message": err,
            "total": 0,
            "created": 0,
            "updated": 0,
            "errors": 1,
        }
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
