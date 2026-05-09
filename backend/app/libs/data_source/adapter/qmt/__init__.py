# -*- coding: utf-8 -*-
"""
QMT/miniQMT 子包：xtquant 封装、按证券类型拆分实现、统一模型输出。
迅投侧时间/周期/后缀等转换见 mappings.py；DataFrame/行转换见 convert.py；历史下载与行情在适配器内对 xtdata 直接调用 download_history_data、get_market_data 等。
"""
from __future__ import annotations

from app.libs.data_source.adapter.qmt.adapter import QMTDataSourceAdapter

__all__ = [
    "QMTDataSourceAdapter",
]
