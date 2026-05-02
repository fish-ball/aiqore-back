# -*- coding: utf-8 -*-
"""
QMT/miniQMT 子包：xtquant 封装、按证券类型拆分实现、统一模型输出。
迅投侧时间/周期/后缀等转换与映射均见 mappings.py；领域通用枚举与模型见 app.services.data_source.models。
底层 xt 函数式封装见 native 子包（将逐步迁移）。
测试兼容：保留与旧模块一致的私有函数别名（_to_xtdata_time 等）。
"""
from __future__ import annotations

from app.services.data_source.adapter.qmt.adapter import QMTAdapter
from app.services.data_source.adapter.qmt.core import DEFAULT_SECTORS, ensure_xtdata, reset_xtdata_cache
from app.services.data_source.adapter.qmt.convert import (
    rows_from_symbol_df as _rows_from_symbol_df,
    tick_list_to_rows as _tick_list_to_rows,
    tick_ndarray_to_rows as _tick_ndarray_to_rows,
    tick_row_to_standard as _tick_row_to_standard,
    tick_scalar as _tick_scalar,
    xt_row_to_kline as _xt_row_to_kline,
)
from app.services.data_source.adapter.qmt.mappings import to_xtdata_period as _to_xtdata_period
from app.services.data_source.adapter.qmt.mappings import to_xtdata_time as _to_xtdata_time

# 旧单文件模块中的名称
_ensure_xtdata = ensure_xtdata

__all__ = [
    "QMTAdapter",
    "DEFAULT_SECTORS",
    "ensure_xtdata",
    "reset_xtdata_cache",
    "_ensure_xtdata",
    "_to_xtdata_time",
    "_to_xtdata_period",
    "_xt_row_to_kline",
    "_rows_from_symbol_df",
    "_tick_scalar",
    "_tick_row_to_standard",
    "_tick_list_to_rows",
    "_tick_ndarray_to_rows",
]
