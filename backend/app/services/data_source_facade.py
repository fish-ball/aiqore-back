# -*- coding: utf-8 -*-
"""
数据源对外装配入口：组合默认 QMT 与标的同步。
细粒度导入可使用 data_source_qmt_defaults、data_source_instruments、data_source_resolve。
"""
from __future__ import annotations

from app.services.data_source_instruments import sync_instruments, sync_single_instrument
from app.services.data_source_qmt_defaults import get_default_qmt_adapter

__all__ = [
    "get_default_qmt_adapter",
    "sync_instruments",
    "sync_single_instrument",
]
