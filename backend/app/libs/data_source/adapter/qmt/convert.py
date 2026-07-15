# -*- coding: utf-8 -*-
"""xtquant 结构转统一模型：K 线、标的详情字典等。"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Type

import pandas as pd

from app.libs.data_source.adapter.qmt import native
from app.libs.data_source.models.enums import AssetClass, InstrumentType, OptionContractKind
from app.libs.data_source.models.instrument import (
    DataSourceInstrument,
    DataSourceInstrumentETF,
    DataSourceInstrumentFund,
    DataSourceInstrumentFuture,
    DataSourceInstrumentIndex,
    DataSourceInstrumentOption,
    DataSourceInstrumentStock,
)
from app.libs.data_source.models.kline import KlineBar

logger = logging.getLogger(__name__)


def _str_field(raw: dict[str, Any], key: str) -> str:
    v = raw.get(key)
    if v is None:
        return ""
    return str(v).strip()


def _parse_qmt_yyyymmdd(val: Any) -> Optional[date]:
    """解析迅投 YYYYMMDD 或 0/99999999 等到 date；无效返回 None。"""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s in ("0", "99999999", "99991231"):
        return None
    if len(s) >= 8 and s[:8].isdigit():
        y, m, d = int(s[:4]), int(s[4:6]), int(s[6:8])
        if m <= 0 or d <= 0:
            return None
        try:
            return date(y, m, d)
        except ValueError:
            return None
    return None


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _to_bool(val: Any) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return None


# 迅投 ExchangeID 中可视为商品/金融期货期权挂牌场所的取值（与 app.constants 解耦，仅用于子类粗分）
_QMT_FUTURES_VENUE_IDS: frozenset[str] = frozenset(
    {
        "SF",
        "SHFE",
        "INE",
        "DF",
        "DCE",
        "ZF",
        "CZCE",
        "GF",
        "GFEX",
        "CFX",
        "CFFEX",
        "CFE",
        "IF",
    }
)


def _qmt_suffix_for_code(raw: dict[str, Any], symbol: str) -> str:
    """用于拼接 code 的交易所后缀：优先 symbol 点号后一段，否则 ExchangeID（大写）。"""
    if "." in symbol:
        suf = symbol.rsplit(".", 1)[-1].strip().upper()
        if suf:
            return suf
    return _str_field(raw, "ExchangeID").upper()


def _build_code(instrument_id: str, suffix: str, symbol: str) -> str:
    if instrument_id and suffix:
        return f"{instrument_id}.{suffix}"
    return symbol or instrument_id


def _qmt_option_contract_kind(val: Any) -> Optional[OptionContractKind]:
    if val is None:
        return None
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    if n == 0:
        return OptionContractKind.CALL
    if n == 1:
        return OptionContractKind.PUT
    return None


def _is_qmt_option_raw(raw: dict[str, Any]) -> bool:
    ot = raw.get("OptionType")
    if isinstance(ot, int):
        return ot != -1
    return False


def _is_future_exchange_raw(exchange_id_raw: str) -> bool:
    if not exchange_id_raw:
        return False
    u = exchange_id_raw.strip().upper()
    return u in _QMT_FUTURES_VENUE_IDS


def _safe_get_instrument_type(symbol: str, xtdata: Any) -> Optional[str]:
    try:
        return native.get_instrument_type(symbol, xtdata=xtdata)
    except ValueError:
        logger.debug("get_instrument_type 解析失败: %s", symbol, exc_info=True)
        return None


def _resolve_instrument_subclass(
    raw: dict[str, Any],
    symbol: str,
    xtdata: Any,
) -> Type[DataSourceInstrument]:
    if _is_qmt_option_raw(raw):
        return DataSourceInstrumentOption
    kind = _safe_get_instrument_type(symbol, xtdata) if xtdata is not None else None
    if kind == "stock":
        return DataSourceInstrumentStock
    if kind == "fund":
        return DataSourceInstrumentFund
    if kind == "etf":
        return DataSourceInstrumentETF
    if kind == "index":
        return DataSourceInstrumentIndex
    ex_raw = _str_field(raw, "ExchangeID")
    if kind is None and _is_future_exchange_raw(ex_raw):
        return DataSourceInstrumentFuture
    return DataSourceInstrumentStock


def _infer_instrument_and_asset_class(
    cls: Type[DataSourceInstrument],
    qmt_kind: Optional[str],
) -> tuple[str, str]:
    if cls is DataSourceInstrumentOption:
        return InstrumentType.OPTION.value, AssetClass.EQUITY.value
    if cls is DataSourceInstrumentFuture:
        return InstrumentType.FUTURE.value, AssetClass.COMMODITY.value
    if cls is DataSourceInstrumentFund:
        return InstrumentType.FUND.value, AssetClass.EQUITY.value
    if cls is DataSourceInstrumentETF:
        return InstrumentType.ETF.value, AssetClass.EQUITY.value
    if cls is DataSourceInstrumentIndex:
        return InstrumentType.INDEX.value, AssetClass.EQUITY.value
    if qmt_kind == "fund":
        return InstrumentType.FUND.value, AssetClass.EQUITY.value
    if qmt_kind == "etf":
        return InstrumentType.ETF.value, AssetClass.EQUITY.value
    if qmt_kind == "index":
        return InstrumentType.INDEX.value, AssetClass.EQUITY.value
    return InstrumentType.STOCK.value, AssetClass.EQUITY.value


def _underlying_code_from_opt(raw: dict[str, Any]) -> str:
    c = _str_field(raw, "OptUndlCode")
    m = _str_field(raw, "OptUndlMarket")
    if not c:
        return ""
    if m:
        return f"{c}.{m}"
    return c


def qmt_detail_dict_to_instrument(
    raw: dict[str, Any],
    symbol: str,
    *,
    xtdata: Any | None = None,
) -> DataSourceInstrument:
    """将 native/xtdata get_instrument_detail 返回的字典转为对应的 DataSourceInstrument 子类实例。"""
    iid = _str_field(raw, "InstrumentID")
    suffix = _qmt_suffix_for_code(raw, symbol)
    code = _build_code(iid, suffix, symbol)
    qmt_kind = _safe_get_instrument_type(symbol, xtdata) if xtdata is not None else None
    cls = _resolve_instrument_subclass(raw, symbol, xtdata)
    inst_type, asset_cls = _infer_instrument_and_asset_class(cls, qmt_kind)

    base_kw: dict[str, Any] = {
        "code": code,
        "name": _str_field(raw, "InstrumentName"),
        "instrument_type": inst_type,
        "asset_class": asset_cls,
        "open_date": _parse_qmt_yyyymmdd(raw.get("OpenDate")),
        "expire_date": _parse_qmt_yyyymmdd(raw.get("ExpireDate") if raw.get("ExpireDate") is not None else raw.get("ExpiryDate")),
        "trading_date": _parse_qmt_yyyymmdd(raw.get("TradingDay")),
        "pre_close": _to_float(raw.get("PreClose")),
        "last_volume": _to_int(raw.get("LastVolume")),
        "settlement_price": _to_float(raw.get("SettlementPrice")),
        "up_stop_price": _to_float(raw.get("UpStopPrice")),
        "down_stop_price": _to_float(raw.get("DownStopPrice")),
        "price_tick": _to_float(raw.get("PriceTick")),
        "multiplier": _to_float(raw.get("VolumeMultiple")),
        "is_active": _to_bool(raw.get("IsTrading")),
        "last_price": _to_float(raw.get("LastPrice")),
    }

    if cls is DataSourceInstrumentStock:
        return DataSourceInstrumentStock(
            **base_kw,
            float_share=_to_float(raw.get("FloatVolume")),
            total_share=_to_float(raw.get("TotalVolume")),
        )
    if cls is DataSourceInstrumentFuture:
        return DataSourceInstrumentFuture(
            **base_kw,
            product_code=_str_field(raw, "ProductID"),
            product_name=_str_field(raw, "ProductName"),
            long_margin_ratio=_to_float(raw.get("LongMarginRatio")),
            short_margin_ratio=_to_float(raw.get("ShortMarginRatio")),
            is_continuous=_to_bool(raw.get("IsContinuous")),
            delivery_year=_to_int(raw.get("DeliveryYear")),
            delivery_month=_to_int(raw.get("DeliveryMonth")),
            max_limit_order_volume=_to_int(raw.get("MaxLimitOrderVolume")),
            min_limit_order_volume=_to_int(raw.get("MinLimitOrderVolume")),
            max_market_order_volume=_to_int(raw.get("MaxMarketOrderVolume")),
            min_market_order_volume=_to_int(raw.get("MinMarketOrderVolume")),
            product_open_quota=_to_int(raw.get("ProductOpenInterestQuota")),
            contract_open_quota=_to_int(raw.get("ContractOpenInterestQuota")),
        )
    if cls is DataSourceInstrumentOption:
        return DataSourceInstrumentOption(
            **base_kw,
            option_type=_qmt_option_contract_kind(raw.get("OptionType")),
            product_code=_str_field(raw, "ProductID"),
            product_name=_str_field(raw, "ProductName"),
            underlying_code=_underlying_code_from_opt(raw),
            max_limit_order_volume=_to_int(raw.get("MaxLimitOrderVolume")),
            min_limit_order_volume=_to_int(raw.get("MinLimitOrderVolume")),
            max_market_order_volume=_to_int(raw.get("MaxMarketOrderVolume")),
            min_market_order_volume=_to_int(raw.get("MinMarketOrderVolume")),
            exercise_price=_to_float(raw.get("OptExercisePrice")),
            end_delivery_date=_parse_qmt_yyyymmdd(raw.get("EndDelivDate")),
            product_open_quota=_to_int(raw.get("ProductOpenInterestQuota")),
            contract_open_quota=_to_int(raw.get("ContractOpenInterestQuota")),
        )
    if cls is DataSourceInstrumentFund:
        return DataSourceInstrumentFund(**base_kw)
    if cls is DataSourceInstrumentETF:
        return DataSourceInstrumentETF(**base_kw)
    if cls is DataSourceInstrumentIndex:
        return DataSourceInstrumentIndex(**base_kw)
    return DataSourceInstrument(**base_kw)


def xt_row_to_kline(row: Any) -> KlineBar:
    """xtquant 单行（DataFrame row）转为标准 K 线模型。"""
    t = row.get("time")
    try:
        time_ms = int(float(t)) if t is not None else 0
    except (TypeError, ValueError):
        time_ms = 0

    def _f(key: str, default: float = 0) -> float:
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _i(key: str, default: int = 0) -> int:
        v = row.get(key)
        if v is None:
            return default
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    vol = row.get("volume", row.get("vol"))
    vol = int(float(vol)) if vol is not None else 0
    return KlineBar(
        time=time_ms,
        open=_f("open"),
        high=_f("high"),
        low=_f("low"),
        close=_f("close"),
        volume=vol,
        amount=_f("amount"),
        settle=_f("settle"),
        openInterest=_i("openInterest"),
        preClose=_f("preClose"),
        suspendFlag=_i("suspendFlag"),
    )


def rows_from_symbol_df(df: Any) -> List[KlineBar]:
    """从 xtquant 单标的 DataFrame 转为标准 K 线列表。结算价列 ``settelementPrice`` 映射为 ``settle``。"""
    if df is not None and hasattr(df, "columns"):
        cols = getattr(df, "columns", None)
        if cols is not None and "settelementPrice" in cols and "settle" not in cols:
            df = df.rename(columns={"settelementPrice": "settle"})
    return [xt_row_to_kline(row) for _, row in df.iterrows()]


def adapt_xt_get_market_data_ex_kline(
    raw: Any,
    *,
    expected_symbols: Sequence[str],
) -> Dict[str, List[KlineBar]]:
    """
    将 ``get_market_data_ex`` 在 K 线周期下的 dict[合约, DataFrame] 转为 dict[合约, KlineBar 列表]。

    - DataFrame 为空：空列表。
    - 无 time 列且表非空：无法构成 KlineBar，空列表。
    """
    if not isinstance(raw, dict):
        raise TypeError(
            f"get_market_data_ex（K 线）预期顶层为 dict，实为 {type(raw).__name__}"
        )
    missing = [s for s in expected_symbols if s not in raw]
    if missing:
        raise ValueError(f"缺少合约键: {missing}，当前键 {list(raw.keys())}")
    out: Dict[str, List[KlineBar]] = {}
    for sym in expected_symbols:
        v = raw[sym]
        if not isinstance(v, pd.DataFrame):
            raise TypeError(
                f"合约 {sym!r} 预期 pd.DataFrame，实为 {type(v).__name__}"
            )
        if v.empty:
            out[sym] = []
            continue
        if "time" not in v.columns:
            out[sym] = []
            continue
        out[sym] = rows_from_symbol_df(v)
    return out
