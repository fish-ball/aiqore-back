# -*- coding: utf-8 -*-
"""
native 真实 xtdata 冒烟用例共用工具。

XT_QUANT_PATH 使用环境变量；再经 ensure_xtdata 加载。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Tuple

from app.libs.data_source.adapter.qmt.core import ensure_xtdata, reset_xtdata_cache

# 上证 / 深证 / 北交所示例代码（多市场覆盖）
SAMPLE_MARKET_SYMBOLS = (
    ("600000.SH", "SH"),
    ("000001.SZ", "SZ"),
    ("830799.BJ", "BJ"),
)


def get_xt_quant_path() -> Optional[str]:
    """测试用 miniQMT 路径：环境变量 XT_QUANT_PATH。"""
    p = os.environ.get("XT_QUANT_PATH", "").strip()
    return p or None


def try_load_xtdata() -> Tuple[Optional[Any], str]:
    """
    尝试加载 xtdata 实例。
    成功返回 (xt, "")；失败返回 (None, 人类可读原因)，供 SkipTest 使用。
    """
    path = get_xt_quant_path()
    if not path:
        return None, "无 XT_QUANT_PATH（请设置环境变量）"
    if not Path(path).is_dir():
        return None, f"路径无效: {path}"
    reset_xtdata_cache()
    xt = ensure_xtdata(path)
    if xt is None:
        return None, "ensure_xtdata 失败（xtquant / miniQMT）"
    return xt, ""
