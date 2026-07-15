# -*- coding: utf-8 -*-
"""QMT 适配器单测共享：patch 目标与单例重置。"""
from __future__ import annotations

from app.libs.data_source.adapter.qmt import QMTDataSourceAdapter

# _load_xtdata 在适配器内加载 xtquant，测试中 patch 此处
_PATCH_LOAD_XT = "app.libs.data_source.adapter.qmt.adapter.QMTDataSourceAdapter._load_xtdata"


def reset_qmt_singleton() -> None:
    """重置 QMT 单例及本实例插入的 sys.path，避免用例互相污染。"""
    QMTDataSourceAdapter.reset_singleton_for_tests()
