"""
证券交易端：与数据源 adapter 分离，负责账户资产、持仓等交易侧查询。
"""
from typing import Any, Dict, Optional, Type

from app.config import settings
from app.models.data_source import DataSource

from .base import SecuritiesTrader
from .qmt_trader import QMTTrader

# 与 DataSource.source_type 一致
SOURCE_TYPE_QMT = "qmt"

_TRADER_REGISTRY: Dict[str, Type[SecuritiesTrader]] = {
    SOURCE_TYPE_QMT: QMTTrader,
}

_default_qmt_trader: Optional[QMTTrader] = None


def get_trader(source_type: str, config: Optional[Dict[str, Any]] = None) -> SecuritiesTrader:
    """根据 source_type 返回交易端实例。"""
    cls = _TRADER_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"不支持的交易端 source_type: {source_type}，可选: {list(_TRADER_REGISTRY.keys())}")
    return cls(config or {})


def _connection_to_trader_config(conn: DataSource) -> Dict[str, Any]:
    """ORM 连接 JSON config 副本；交易需 xt_quant_path，缺省时用 settings.XT_QUANT_PATH。"""
    cfg = dict(conn.config or {})
    if not str(cfg.get("xt_quant_path") or "").strip():
        cfg = {**cfg, "xt_quant_path": settings.XT_QUANT_PATH}
    return cfg


def get_trader_for_connection(conn: DataSource) -> SecuritiesTrader:
    """
    根据数据源连接返回交易端实例。
    当前仅 QMT 支持账户/持仓查询。
    """
    if conn.source_type != SOURCE_TYPE_QMT:
        raise ValueError(f"交易接口当前仅支持 QMT，连接 source_type={conn.source_type}")
    return get_trader(SOURCE_TYPE_QMT, _connection_to_trader_config(conn))


def get_default_qmt_trader() -> QMTTrader:
    """进程内单例：使用 settings 的默认 QMT 交易端。"""
    global _default_qmt_trader
    if _default_qmt_trader is None:
        _default_qmt_trader = QMTTrader({
            "xt_quant_path": settings.XT_QUANT_PATH,
            "xt_quant_acct": settings.XT_QUANT_ACCT,
        })
    return _default_qmt_trader


__all__ = [
    "SecuritiesTrader",
    "QMTTrader",
    "SOURCE_TYPE_QMT",
    "get_trader",
    "get_trader_for_connection",
    "get_default_qmt_trader",
]
