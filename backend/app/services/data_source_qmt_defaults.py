# -*- coding: utf-8 -*-
"""默认 QMT 适配器单例：仅依赖 settings 与 data_source.adapter，避免与 instrument_service 循环引用。"""
from __future__ import annotations

from app.config import settings
from app.libs.data_source.adapter import get_adapter

_default_qmt_adapter = None


def get_default_qmt_adapter():
    """返回默认 QMT 适配器（使用 settings 配置），供 market/trade/sector/instrument 等使用。"""
    global _default_qmt_adapter
    if _default_qmt_adapter is None:
        _default_qmt_adapter = get_adapter("qmt", {
            "xt_quant_path": settings.XT_QUANT_PATH,
            "xt_quant_acct": settings.XT_QUANT_ACCT,
        })
    return _default_qmt_adapter


__all__ = ["get_default_qmt_adapter"]
