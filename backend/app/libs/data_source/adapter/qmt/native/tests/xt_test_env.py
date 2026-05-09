# -*- coding: utf-8 -*-
"""
native 真实 xtdata 冒烟用例共用工具。

需本机已启动 miniQMT，且当前 Python 可 import xtquant。
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

from app.libs.data_source.adapter.qmt.adapter import QMTDataSourceAdapter

# 上证 / 深证 / 北交所示例代码（多市场覆盖）
SAMPLE_MARKET_SYMBOLS = (
    ("600000.SH", "SH"),
    ("000001.SZ", "SZ"),
    ("830799.BJ", "BJ"),
)


def try_load_xtdata() -> Tuple[Optional[Any], str]:
    """
    尝试加载 xtdata 实例。
    成功返回 (xt, "")；失败返回 (None, 人类可读原因)，供 SkipTest 使用。
    """
    QMTDataSourceAdapter.reset_singleton_for_tests()
    adapter = QMTDataSourceAdapter({})
    xt = adapter.xtdata
    if xt is None:
        return None, "无法加载 xtquant.xtdata（请启动 miniQMT 并确保已安装 xtquant）"
    return xt, ""
