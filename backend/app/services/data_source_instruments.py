# -*- coding: utf-8 -*-
"""
标的列表/详情同步到数据库（同步执行，供 API 与 Celery 共用）。
依赖 instrument_service 与 DB 解析，不属于 data_source 原子包。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.libs.data_source.adapter import get_adapter
from app.services.data_source_resolve import resolve_adapter_config
from app.services.instrument_service import instrument_service

logger = logging.getLogger(__name__)


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
    with_details = []
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
