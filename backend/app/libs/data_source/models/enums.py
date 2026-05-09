# -*- coding: utf-8 -*-
"""数据源通用枚举：资产大类、标的类型、K 线周期等。"""

from __future__ import annotations

from enum import Enum

__all__ = ["AssetClass", "InstrumentType", "BarPeriod", "DataSourceType"]


class DataSourceType(str, Enum):
    """
    数据源类型：ORM DataSource.source_type、板块表 Sector.source、get_adapter 注册键、各适配器 name 一致。
    """

    QMT = "qmt"
    JOINQUANT = "joinquant"
    TUSHARE = "tushare"


class AssetClass(str, Enum):
    EQUITY = "EQUITY"  # 权益：以公司所有权为核心风险
    DEBT = "DEBT"  # 债权：以利率和信用为核心风险
    HYBRID = "HYBRID"  # 混合：债权和权益的组合
    COMMODITY = "COMMODITY"  # 商品：以实物供需为核心风险
    CURRENCY = "CURRENCY"  # 货币：汇率与加密货币
    CRYPTO = "CRYPTO"  # 加密货币：以区块链技术为核心风险


class InstrumentType(str, Enum):
    # --- EQUITY 类 ---
    STOCK = "STOCK"  # 普通股
    PREFERRED_STOCK = "PREF_STOCK"  # 优先股
    FUND = "FUND"  # 基金
    ETF = "ETF"  # 交易所基金
    INDEX = "INDEX"  # 指数（与 instruments.instrument_type 一致）

    # --- DEBT / HYBRID 类 ---
    BOND = "BOND"  # 纯债（国债/金融债）
    CONV_BOND = "CONV_BOND"  # 可转债
    REPO = "REPO"  # 回购（如 GC001）

    # --- DERIVATIVE 类 ---
    FUTURE = "FUTURE"  # 期货 Futures
    OPTION = "OPTION"  # 期权 Options
    PERP = "PERP"  # 永续合约 Perpetual Futures
    WARRANT = "WARRANT"  # 权证 Warrants


class BarPeriod(str, Enum):
    """
    统一 K 线周期（上层 / API / 缓存约定）。
    各数据源适配器自行映射为下游所需字符串。
    """

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"
    M1_MONTH = "1M"
