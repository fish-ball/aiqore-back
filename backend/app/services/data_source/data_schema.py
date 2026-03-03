# -*- coding: utf-8 -*-
"""
数据格式约定：K 线与 tick 分笔，供 adapter 与 cache 统一使用。
K 线参考迅投文档：https://dict.thinktrader.net/dictionary/stock.html?id=p6K7h8
Adapter 子类在 get_klines_data / get_ticks_data 内部完成上游格式到本格式的转换并返回。
"""
from typing import Dict, List

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

# 分笔 DataFrame 列名（与 get_market_data_ex period='tick' 返回一致）
TICK_DF_COLUMNS: List[str] = [
    "time",              # int64, UNIX 毫秒时间戳
    "lastPrice",         # float64
    "open",
    "high",
    "low",
    "lastClose",
    "amount",
    "volume",            # int64
    "pvolume",           # int64
    "tickvol",           # int64
    "stockStatus",       # int32
    "openInt",           # int32
    "lastSettlementPrice",
    "askPrice",          # object，如 [10.99, 0.0, ...]
    "bidPrice",          # object
    "askVol",            # object
    "bidVol",            # object
    "settlementPrice",
    "transactionNum",   # int64
    "pe",
]

# 分笔列类型说明（用于文档与校验，key 为列名，value 为 dtype 描述）
TICK_DF_DTYPES: Dict[str, str] = {
    "time": "int64",
    "lastPrice": "float64",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "lastClose": "float64",
    "amount": "float64",
    "volume": "int64",
    "pvolume": "int64",
    "tickvol": "int64",
    "stockStatus": "int32",
    "openInt": "int32",
    "lastSettlementPrice": "float64",
    "askPrice": "object",
    "bidPrice": "object",
    "askVol": "object",
    "bidVol": "object",
    "settlementPrice": "float64",
    "transactionNum": "int64",
    "pe": "float64",
}
