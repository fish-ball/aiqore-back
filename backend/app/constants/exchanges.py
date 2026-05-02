# -*- coding: utf-8 -*-
"""
交易所完整静态目录（代码内维护，非数据库表）。

证券主表 `exchange_code`（大写）与本模块中各条目的 `code` 对齐。
数据源若返回其它写法（如 XSHG），通过 `aliases` 归一到规范 `code`。

`suffix`：证券代码中点号后的规范片段（不含点），统一大写（如 SH、SF、CFX），
与迅投等环境中 `symbol` 写法一致（解析时大小写不敏感）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple


@dataclass(frozen=True)
class ExchangeDef:
    """单条交易所定义（不可变）。"""

    code: str
    name: str
    short_name: str
    # 证券代码点号后的规范后缀标识（不含点），如 600000.SH -> SH，rb2405.SF -> SF
    suffix: str
    sort_order: int = 0
    country_region: str = "CN"
    description: Optional[str] = None
    is_active: bool = True
    # 接口或历史数据中可能出现的其它交易所写法（统一存大写）
    aliases: FrozenSet[str] = frozenset()


# 顺序即默认展示顺序；code 为系统内唯一键，与 securities.exchange_code 一致
EXCHANGES: Tuple[ExchangeDef, ...] = (
    ExchangeDef(
        code="SSE",
        name="上海证券交易所",
        short_name="上交所",
        suffix="SH",
        sort_order=10,
        description="现货、期权等（常见 ExchangeID：SSE，别名 XSHG）",
        aliases=frozenset({"XSHG"}),
    ),
    ExchangeDef(
        code="SZSE",
        name="深圳证券交易所",
        short_name="深交所",
        suffix="SZ",
        sort_order=20,
        description="现货、期权等（常见 ExchangeID：SZSE，别名 XSHE）",
        aliases=frozenset({"XSHE"}),
    ),
    ExchangeDef(
        code="BSE",
        name="北京证券交易所",
        short_name="北交所",
        suffix="BJ",
        sort_order=30,
        description="现货（常见 ExchangeID：BSE）",
    ),
    ExchangeDef(
        code="NEEQ",
        name="全国中小企业股份转让系统",
        short_name="新三板",
        suffix="NQ",
        sort_order=35,
        description="股转 / 新三板相关标的（常见 ExchangeID：NEEQ）",
        aliases=frozenset({"NQ"}),
    ),
    ExchangeDef(
        code="SHFE",
        name="上海期货交易所",
        short_name="上期所",
        suffix="SF",
        sort_order=40,
        description="期货；合约后缀常见 .SF（如 rb2405.SF）",
    ),
    ExchangeDef(
        code="INE",
        name="上海国际能源交易中心",
        short_name="上期能源",
        suffix="INE",
        sort_order=45,
        description="期货；合约后缀常见 .INE",
    ),
    ExchangeDef(
        code="DCE",
        name="大连商品交易所",
        short_name="大商所",
        suffix="DF",
        sort_order=50,
        description="期货；合约后缀常见 .DF",
    ),
    ExchangeDef(
        code="CZCE",
        name="郑州商品交易所",
        short_name="郑商所",
        suffix="ZF",
        sort_order=60,
        description="期货；合约后缀常见 .ZF",
    ),
    ExchangeDef(
        code="GFEX",
        name="广州期货交易所",
        short_name="广期所",
        suffix="GF",
        sort_order=65,
        description="期货；合约后缀常见 .GF",
    ),
    ExchangeDef(
        code="CFFEX",
        name="中国金融期货交易所",
        short_name="中金所",
        suffix="CFX",
        sort_order=70,
        description="金融期货、期权；主后缀 .CFX，亦常见 .CFE / .CFFEX",
        aliases=frozenset({"CFE"}),
    ),
    ExchangeDef(
        code="HKEX",
        name="香港交易所",
        short_name="港交所",
        suffix="HK",
        sort_order=80,
        country_region="HK",
        description="港股等（常见 ExchangeID：HKEX）",
    ),
)


_BY_CODE: Dict[str, ExchangeDef] = {e.code.upper(): e for e in EXCHANGES}


def _build_alias_to_code() -> Dict[str, str]:
    m: Dict[str, str] = {}
    for ex in EXCHANGES:
        c = ex.code.upper()
        m[c] = c
        for a in ex.aliases:
            m[a.upper()] = c
    return m


_ALIAS_TO_CODE: Dict[str, str] = _build_alias_to_code()


def _build_suffix_to_exchange_code() -> Dict[str, str]:
    """点号后后缀（小写）-> 规范交易所 code；含中金所等价后缀。"""
    m: Dict[str, str] = {}
    for ex in EXCHANGES:
        key = str(ex.suffix).strip().lower()
        if key:
            m[key] = ex.code.upper()
    m["cfe"] = "CFFEX"
    m["cffex"] = "CFFEX"
    return m


# 供 resolve symbol / infer 期货等与 mappings 对齐
SUFFIX_TO_EXCHANGE_CODE: Dict[str, str] = _build_suffix_to_exchange_code()


_SPOT_BOARD_SUFFIXES = frozenset({"SH", "SZ", "BJ"})
# 证券主表 market（SH/SZ/BJ）-> 规范交易所 code
MARKET_TO_EXCHANGE_CODE: Dict[str, str] = {
    ex.suffix.upper(): ex.code.upper()
    for ex in EXCHANGES
    if ex.suffix.upper() in _SPOT_BOARD_SUFFIXES
}


def normalize_exchange_code(raw: Optional[str]) -> Optional[str]:
    """
    将接口返回的 ExchangeID 或别名转为规范 code（大写）。
    未知则返回 None。
    """
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    if s in _BY_CODE:
        return s
    return _ALIAS_TO_CODE.get(s)


def get_exchange_def(code: Optional[str]) -> Optional[ExchangeDef]:
    """按规范 code（大小写不敏感）取定义。"""
    if not code:
        return None
    return _BY_CODE.get(str(code).strip().upper())


def iter_exchange_defs(
    *,
    active_only: bool = True,
    keyword: Optional[str] = None,
) -> List[ExchangeDef]:
    """可选关键字过滤（匹配 code / name / short_name / suffix），默认仅有效条目。"""
    rows = list(EXCHANGES)
    if active_only:
        rows = [e for e in rows if e.is_active]
    if keyword and keyword.strip():
        kw = keyword.strip().lower()
        rows = [
            e
            for e in rows
            if kw in e.code.lower()
            or kw in e.name.lower()
            or kw in (e.short_name or "").lower()
            or kw == e.suffix.lower()
        ]
    return sorted(rows, key=lambda x: (x.sort_order, x.code))


def exchange_def_to_api_dict(ex: ExchangeDef) -> Dict[str, object]:
    """供 REST 与前端列表使用的字典形态（无数据库 id）。"""
    return {
        "code": ex.code,
        "name": ex.name,
        "short_name": ex.short_name,
        "suffix": ex.suffix,
        "country_region": ex.country_region,
        "sort_order": ex.sort_order,
        "description": ex.description,
        "is_active": 1 if ex.is_active else 0,
    }


def exchange_brief_dict(code: Optional[str]) -> Optional[Dict[str, object]]:
    """证券接口嵌套的交易所摘要。"""
    ex = get_exchange_def(code)
    if ex is None:
        return None
    return {
        "code": ex.code,
        "name": ex.name,
        "short_name": ex.short_name,
        "suffix": ex.suffix,
    }
