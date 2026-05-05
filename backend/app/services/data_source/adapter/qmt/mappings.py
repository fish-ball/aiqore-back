# -*- coding: utf-8 -*-
"""
迅投 xtquant / xtdata 专用映射与字符串转换（原 xt_mapping + 周期/后缀表统一于此）。

- 时间：上层 YYYY-MM-DD[ HH:MM:SS] -> xt start_time/end_time 用的连续数字串
- 周期：上层 period -> xt get_market_data / download_history_data 的 period 参数
- 后缀：期货等合约后缀集合，供 symbol_kind 使用
"""
from __future__ import annotations

from typing import Dict, Optional

from app.constants.exchanges import EXCHANGES
from app.services.data_source.models.enums import BarPeriod

_FUTURES_EXCHANGE_CODES = frozenset({"SHFE", "INE", "DCE", "CZCE", "GFEX", "CFFEX"})
# 中金所除主后缀 CFX 外，接口常见 .cfe / .cffex
_EXTRA_FUTURES_SUFFIX_LOWER = frozenset({"cfe", "cffex"})


def to_xtdata_time(s: Optional[str]) -> Optional[str]:
    """
    将 YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD 转为 xtdata 所需格式 YYYYMMDD 或 YYYYMMDDhhmmss。
    xtdata 文档：start_time/end_time 为 8 位日期或 YYYYMMDDhhmmss，不接受带横杠和空格的格式。
    """
    if not s or not isinstance(s, str):
        return s
    s = s.strip()
    if not s:
        return s
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) >= 14:
        return digits[:14]
    if len(digits) >= 8:
        return digits[:8]
    return s

# 上层 period 字符串 -> xtdata.get_market_data / download_history_data 的 period 参数
# 文档常见：1d、1w、1mon；分钟线为 1m、5m 等
BAR_PERIOD_TO_XT: Dict[str, str] = {
    BarPeriod.M1.value: "1m",
    BarPeriod.M3.value: "3m",
    BarPeriod.M5.value: "5m",
    BarPeriod.M15.value: "15m",
    BarPeriod.M30.value: "30m",
    BarPeriod.H1.value: "1h",
    BarPeriod.D1.value: "1d",
    BarPeriod.W1.value: "1w",
    BarPeriod.M1_MONTH.value: "1mon",
}

# 期货等合约代码后缀（小写），用于 infer_market_layer；与 exchanges.suffix 一致
FUTURES_EXCHANGE_SUFFIXES = (
    frozenset(ex.suffix.lower() for ex in EXCHANGES if ex.code.upper() in _FUTURES_EXCHANGE_CODES)
    | _EXTRA_FUTURES_SUFFIX_LOWER
)


def normalize_period_to_xt(period: str) -> str:
    """将上层 period（如 1M）转为 xtdata 周期字符串（如 1mon）。"""
    p = (period or "").strip()
    if not p:
        return BarPeriod.D1.value
    if p in BAR_PERIOD_TO_XT:
        return BAR_PERIOD_TO_XT[p]
    if p == "1M":
        return "1mon"
    return p


# 与历史 xt_mapping.to_xtdata_period 同义，便于单点导入
to_xtdata_period = normalize_period_to_xt
