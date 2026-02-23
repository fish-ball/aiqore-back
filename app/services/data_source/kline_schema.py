# -*- coding: utf-8 -*-
"""
K 线数据格式约定：与 ticks 区分，供 adapter 与 cache 统一使用。
参考迅投文档：https://dict.thinktrader.net/dictionary/stock.html?id=p6K7h8
Adapter 子类在 get_klines_data 内部完成上游格式到本格式的转换并返回，不在抽象层外再做格式整理。
"""
from typing import List

# K 线行字段（parquet 与内存一致）：time 为 UNIX 毫秒时间戳（整数），其余为数值
KLINE_ROW_FIELDS: List[str] = [
    "time",        # UNIX 毫秒时间戳，整数
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "settle",      # 今结算（股票多为 0）
    "openInterest",  # 持仓量（股票多为 0）
    "preClose",    # 前收盘价
    "suspendFlag", # 停牌 1 停牌，0 不停牌
]
