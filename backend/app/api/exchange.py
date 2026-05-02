# -*- coding: utf-8 -*-
"""交易所目录 API（静态定义，只读）。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.constants.exchanges import (
    exchange_def_to_api_dict,
    iter_exchange_defs,
)

router = APIRouter(prefix="/api/exchange", tags=["交易所"])
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_exchanges(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    is_active: Optional[int] = Query(None, description="1 仅有效，0 仅无效，不传则返回全部"),
    keyword: Optional[str] = Query(None, description="代码/名称/简称模糊搜索"),
    code: Optional[str] = Query(None, description="规范交易所代码精确匹配，如 SSE；与其它筛选同时生效"),
):
    """分页返回内置交易所目录。"""
    try:
        rows = iter_exchange_defs(active_only=False, keyword=keyword)
        if code is not None and code.strip():
            cu = code.strip().upper()
            rows = [e for e in rows if e.code.upper() == cu]
        if is_active == 1:
            rows = [e for e in rows if e.is_active]
        elif is_active == 0:
            rows = [e for e in rows if not e.is_active]
        items = [exchange_def_to_api_dict(e) for e in rows]
        total = len(items)
        offset = (page - 1) * page_size
        return {"results": items[offset : offset + page_size], "count": total}
    except Exception as e:
        logger.exception("交易所列表失败")
        raise HTTPException(status_code=500, detail=str(e)) from e
